"""Differentiable distributed-contact penalties with frozen witness choices.

Witness selection is a local optimization heuristic, never an infeasibility
certificate. Independent scene measurement searches the full authored patch.
"""
import itertools
import numpy as np
import torch
from object_geometry import Geometry
from scene_region_contact import contact_witness


def signed_distance(points, position, rotation, geometry):
    local = (points-position) @ rotation
    if geometry.shape == 'sphere':
        return torch.linalg.vector_norm(local, dim=-1)-geometry.dimensions[0]
    half = points.new_tensor(geometry.dimensions)/2
    q = local.abs()-half
    return torch.linalg.vector_norm(torch.relu(q), dim=-1)+torch.minimum(q.amax(-1), q.new_tensor(0.))


def violations(points, faces, triple, anchor, target, desired_normal, geometry, position, rotation, limits, anchor_tolerance):
    """Dimensionless signed violations (<= 0 is feasible) for one frame."""
    gaps = signed_distance(points, position, rotation, geometry)
    near = points[triple]
    tri = points[faces]
    normal = torch.linalg.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]).sum(0)
    normal = normal/torch.linalg.vector_norm(normal).clamp_min(1e-12)
    spacing = torch.stack([torch.linalg.vector_norm(near[a]-near[b]) for a,b in [(0,1),(1,2),(2,0)]])
    area = torch.linalg.vector_norm(torch.linalg.cross(near[1]-near[0],near[2]-near[0]))/2
    chord = 2*np.sin(np.deg2rad(limits['normal_degrees'])/2)
    return torch.cat([
        (limits['clearance_m']-gaps)/.001,
        (gaps[triple]-limits['contact_gap_m'])/.001,
        (torch.linalg.vector_norm(near-target,dim=-1)-limits['local_radius_m'])/.001,
        (limits['spacing_m']-spacing)/.001,
        ((limits['area_m2']-area)/limits['area_m2']).reshape(1),
        ((torch.linalg.vector_norm(near.mean(0)-target)-limits['centroid_error_m'])/.001).reshape(1),
        ((torch.linalg.vector_norm(normal-desired_normal)-chord)/chord).reshape(1),
        ((torch.linalg.vector_norm(points[anchor]-target)-anchor_tolerance)/.001).reshape(1)])


def choose_triangle(points, ids, target, gaps, limits):
    witness = contact_witness(points, ids, target, gaps, limits)
    if witness is not None:
        return witness['vertices'], 'existing feasible distributed witness'
    # Avoid cubic whole-patch work at every frame of an initially bad clip.
    # This restricted start can miss useful correspondences; final feasibility
    # always uses the independent full-patch search, not this heuristic pool.
    ranking = np.linalg.norm(points-target,axis=1)+np.abs(gaps-limits['clearance_m'])
    pool = np.argsort(ranking,kind='stable')[:24]
    triples = np.asarray(list(itertools.combinations(pool,3)))
    tri = points[triples]
    spacing = np.minimum.reduce([np.linalg.norm(tri[:,a]-tri[:,b],axis=1) for a,b in [(0,1),(1,2),(2,0)]])
    area = np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    score = np.maximum(limits['spacing_m']-spacing,0)/.001
    score += np.maximum(limits['area_m2']-area,0)/limits['area_m2']
    score += np.maximum(np.linalg.norm(tri.mean(1)-target,axis=1)-limits['centroid_error_m'],0)/.001
    score += np.maximum(gaps[triples]-limits['contact_gap_m'],0).sum(1)/.001
    score += np.maximum(limits['clearance_m']-gaps[triples],0).sum(1)/.001
    return ids[triples[int(score.argmin())]].tolist(), 'best scored triple in 24 nearest candidate vertices'


class RegionObjective:
    def __init__(self, package, source, skin, reduction='worst'):
        from floor_contact import Surface
        if reduction not in ['worst','balanced']:raise ValueError('Unknown region penalty reduction')
        self.reduction=reduction
        self.records=[]; self.selected=set(); self.selections=[]
        surface=Surface(skin)
        for record in package['regions']:
            ids=np.asarray(record['vertex_ids']);remap={v:i for i,v in enumerate(ids)}
            faces=np.array([[remap[v] for v in face] for face in skin['faces'][record['binding']['face_ids']]])
            hand=record['binding']['hand'];a,b=record['start_frame'],record['end_frame']
            segments=package['anchor_subproblem']['regions'][hand]['segments']
            segment=next(s for s in segments if s['start_frame']==a and s['end_frame']==b)
            geometry=Geometry.parse(record['geometry']);limits=record['binding']['limits']
            for frame in range(a,b+1):
                points=surface.vertices(source['global_rot_mats'][frame],source['posed_joints'][frame],ids)
                position=np.asarray(record['object_positions_m'][frame]);rotation=np.asarray(record['object_rotations'][frame])
                target=np.asarray(segment['positions_m'][frame-a]);gaps=geometry.distance_gradient(points,position,rotation)[0]
                chosen,method=choose_triangle(points,ids,target,gaps,limits)
                self.records.append(dict(frame=frame,hand=hand,ids=ids,faces=faces,
                    triple=np.array([remap[v] for v in chosen]),anchor=remap[segment['vertex_id']],target=target,
                    desired_normal=np.asarray(record['desired_normals'][frame]),geometry=geometry,position=position,
                    rotation=rotation,limits=limits,anchor_tolerance=record['anchor_tolerance_m']))
                self.selections.append(dict(contact_id=record['contact_id'],frame=frame,vertices=chosen,method=method))
            self.selected.update(ids.tolist())
        if not self.records:raise ValueError('Region fitting needs active authored regions')

    def bind(self,mapping):
        self.mapping=mapping

    def point_tolerances(self,contacts,frames,default):
        result=np.full((frames,len(contacts)),default)
        order=list(contacts)
        for r in self.records:result[r['frame'],order.index(r['hand'])]=r['anchor_tolerance']
        return result

    def residuals(self,vertices):
        values=[]
        for r in self.records:
            points=vertices[r['frame'],[self.mapping[v] for v in r['ids']]]
            def tensor(x):return torch.as_tensor(x,dtype=points.dtype,device=points.device)
            values.append(violations(points,r['faces'],r['triple'],r['anchor'],tensor(r['target']),
                tensor(r['desired_normal']),r['geometry'],tensor(r['position']),tensor(r['rotation']),r['limits'],r['anchor_tolerance']))
        return values

    def loss(self,vertices):
        # Normalize per authored contact-frame, so large patches do not drown
        # out small ones. Max violation retains the worst patch sample.
        values=self.residuals(vertices)
        if self.reduction=='worst':
            losses=[torch.relu(v).square().amax() for v in values]
        else:
            losses=[]
            for record,v in zip(self.records,values):
                n=len(record['ids']);squared=torch.relu(v).square()
                # Every constraint family contributes without replicating the
                # weight of clearance merely because the patch has more vertices.
                groups=[squared[:n].mean(),squared[n:n+3].mean(),squared[n+3:n+6].mean(),squared[n+6:n+9].mean()]
                groups.extend(squared[n+9:])
                losses.append(torch.stack(groups).sum())
        return torch.stack(losses).mean()*100.

    def record(self):
        return dict(selections=self.selections,weight=100.,reduction=self.reduction,schema='strep-region-fitting-objective-v1',
            scope='Frozen witness triples; normalized worst-violation penalties. Hard edit bounds inherited from the clip solver, contact feasibility not guaranteed.')
