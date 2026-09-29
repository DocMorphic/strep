"""Differentiable contact penalties with witnesses fixed within each solve stage.

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


def family_reduction(values, vertices):
    """Average each multi-row family, then sum the eight constraint families."""
    if values.ndim != 1 or len(values) != vertices + 13 or vertices < 3:
        raise ValueError('Regional residual layout mismatch')
    groups = [values[:vertices].mean(), values[vertices:vertices+3].mean(),
              values[vertices+3:vertices+6].mean(), values[vertices+6:vertices+9].mean()]
    groups.extend(values[vertices+9:])
    return torch.stack(groups).sum()


class RegionInequalities:
    """Separate normalized inequality multipliers, fixed within each LBFGS stage."""
    def __init__(self, counts):
        if not counts or any(type(n) != int or n < 3 for n in counts):
            raise ValueError('Nonempty regional vertex counts required')
        self.counts = counts
        self.penalty = 200.  # Zero multipliers exactly match the original balanced loss.
        self.multipliers = None
        self.last = None

    def loss(self, values):
        if len(values) != len(self.counts):
            raise ValueError('Regional contact/frame count changed')
        for g, n in zip(values, self.counts):
            family_reduction(g, n)  # Reject broadcastable but incorrect layouts.
        if self.multipliers is None:
            self.multipliers = [torch.zeros_like(g) for g in values]
        losses = []
        for g, m, n in zip(values, self.multipliers, self.counts):
            merit = (torch.relu(m + self.penalty*g).square() - m.square()) / (2*self.penalty)
            losses.append(family_reduction(merit, n))
        self.last = [g.detach().clone() for g in values]
        return torch.stack(losses).mean()

    def advance(self, growth):
        if self.last is None:
            raise ValueError('Evaluate accepted parameters before advancing regional multipliers')
        if type(growth) not in [int, float] or not np.isfinite(growth) or growth <= 1:
            raise ValueError('Finite penalty growth greater than one required')
        self.multipliers = [torch.relu(m + self.penalty*g).detach() for m, g in zip(self.multipliers, self.last)]
        self.penalty *= growth

    def diagnostics(self):
        return dict(penalty=self.penalty,
                    maximum_normalized_violation=max(float(torch.relu(g).max()) for g in self.last)
                    if self.last is not None else None)

    def reset_witness(self,index):
        # Gap/radius/spacing/area/centroid rows now refer to different vertices.
        # Whole-patch clearance, normal and authored anchor identities persist.
        if not 0 <= index < len(self.counts):raise ValueError('Unknown regional constraint record')
        if self.multipliers is not None:
            n=self.counts[index]
            self.multipliers[index][n:n+11]=0


def solver_region_limits(limits,gap_margin):
    if type(gap_margin) not in [int,float] or not np.isfinite(gap_margin) or gap_margin<0:
        raise ValueError('Contact gap margin must be finite and nonnegative')
    result=dict(limits)
    result['contact_gap_m']-=gap_margin
    if result['contact_gap_m']<result['clearance_m'] or (gap_margin>0 and result['contact_gap_m']==result['clearance_m']):
        raise ValueError('Contact gap margin exhausts the clearance window')
    return result


class RegionObjective:
    def __init__(self, package, source, skin, reduction='worst', constraint_mode='penalty',witness_mode='frozen',gap_margin_m=0.):
        from floor_contact import Surface
        if reduction not in ['worst','balanced']:raise ValueError('Unknown region penalty reduction')
        if constraint_mode not in ['penalty','augmented']:raise ValueError('Unknown region constraint mode')
        if constraint_mode=='augmented' and reduction!='balanced':raise ValueError('Regional inequalities require balanced reduction')
        self.constraint_mode=constraint_mode
        if witness_mode not in ['frozen','stage_refresh']:raise ValueError('Unknown witness mode')
        self.witness_mode=witness_mode
        self.gap_margin_m=gap_margin_m
        self.witness_history=[];self.witness_stage=0;self.last_points=None
        self.reduction=reduction
        self.records=[]; self.selected=set(); self.selections=[]
        surface=Surface(skin)
        for record in package['regions']:
            ids=np.asarray(record['vertex_ids']);remap={v:i for i,v in enumerate(ids)}
            faces=np.array([[remap[v] for v in face] for face in skin['faces'][record['binding']['face_ids']]])
            hand=record['binding']['hand'];a,b=record['start_frame'],record['end_frame']
            segments=package['anchor_subproblem']['regions'][hand]['segments']
            segment=next(s for s in segments if s['start_frame']==a and s['end_frame']==b)
            geometry=Geometry.parse(record['geometry']);limits=solver_region_limits(record['binding']['limits'],gap_margin_m)
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
        self.inequalities=RegionInequalities([len(r['ids']) for r in self.records]) if constraint_mode=='augmented' else None

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
        if self.witness_mode=='stage_refresh':
            self.last_points=[vertices[r['frame'],[self.mapping[v] for v in r['ids']]].detach().clone() for r in self.records]
        if self.inequalities is not None:
            return self.inequalities.loss(values)
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

    def advance_stage(self,growth):
        if self.inequalities is not None:self.inequalities.advance(growth)
        if self.witness_mode=='stage_refresh':
            if self.last_points is None:raise ValueError('Accepted pose required for witness refresh')
            self.witness_stage+=1
            self.refresh_witnesses(self.last_points)

    def initialize_witnesses(self,vertices):
        if self.witness_mode=='stage_refresh':
            points=[vertices[r['frame'],[self.mapping[v] for v in r['ids']]].detach() for r in self.records]
            self.refresh_witnesses(points)

    def refresh_witnesses(self,points_by_record):
        if len(points_by_record)!=len(self.records):raise ValueError('Witness pose layout mismatch')
        changes=[]
        for index,(r,points) in enumerate(zip(self.records,points_by_record)):
            array=points.cpu().numpy()
            gaps=r['geometry'].distance_gradient(array,r['position'],r['rotation'])[0]
            chosen,method=choose_triangle(array,r['ids'],r['target'],gaps,r['limits'])
            old=r['ids'][r['triple']].tolist()
            if set(chosen)==set(old):continue
            mapping={v:i for i,v in enumerate(r['ids'])}
            proposed=np.array([mapping[v] for v in chosen])
            def score(triple):
                def tensor(x):return torch.as_tensor(x,dtype=points.dtype,device=points.device)
                g=violations(points,r['faces'],triple,r['anchor'],tensor(r['target']),tensor(r['desired_normal']),
                             r['geometry'],tensor(r['position']),tensor(r['rotation']),r['limits'],r['anchor_tolerance'])
                q=torch.relu(g).square();n=len(r['ids'])
                if self.reduction=='worst':return float(q.max())
                # Only changed families, avoiding cancellation against large
                # unchanged clearance or orientation penalties.
                return float(q[n:n+3].mean()+q[n+3:n+6].mean()+q[n+6:n+9].mean()+q[n+9]+q[n+10])
            before,after=score(r['triple']),score(proposed)
            if after>=before-1e-12:continue
            r['triple']=proposed
            if self.inequalities is not None:self.inequalities.reset_witness(index)
            changes.append(dict(record=index,contact_id=self.selections[index]['contact_id'],frame=r['frame'],
                                old_vertices=old,new_vertices=chosen,old_score=before,new_score=after,method=method))
        self.witness_history.append(dict(stage=self.witness_stage,changes=changes))

    def stage_diagnostics(self):
        return self.inequalities.diagnostics() if self.inequalities is not None else dict(mode='fixed_penalty')

    def record(self):
        return dict(selections=self.selections,weight=100.,reduction=self.reduction,constraint_mode=self.constraint_mode,
            witness_mode=self.witness_mode,witness_history=self.witness_history,
            solver_contact_gap_margin_m=self.gap_margin_m,
            final_witnesses=[r['ids'][r['triple']].tolist() for r in self.records],
            augmented_state=self.stage_diagnostics(),schema='strep-region-fitting-objective-v1',
            scope='Witnesses fixed within each stage; optional strictly improving reselection at accepted stage boundaries. Authored patches/limits unchanged; feasibility not guaranteed.')
