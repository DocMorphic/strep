"""Independent decoded-surface contact-area diagnostic, separate from fitting."""
import argparse
from pathlib import Path
import numpy as np
import trimesh
from threadpoolctl import threadpool_limits
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from bounded_partner_surface import penetration


def triangle_witness(points):
    """A realized triangle-area lower bound; not a maximum-area certificate."""
    if len(points)<3:return dict(area_m2=0.,indices=[])
    distance=np.linalg.norm(points[:,None]-points[None,:],axis=2)
    a,b=np.unravel_index(distance.argmax(),distance.shape)
    area=np.linalg.norm(np.cross(points[b]-points[a],points-points[a]),axis=1)/2
    c=int(area.argmax())
    return dict(area_m2=float(area[c]),indices=[int(a),int(b),c])


def measure(points,patches,faces,tolerance):
    results=[];normals=[]
    for i in [0,1]:
        triangles=points[i][faces[patches[i]['face_ids']]]
        normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]).sum(0)
        if np.linalg.norm(normal)<1e-12:raise ValueError('Degenerate region normal')
        normals.append(normal/np.linalg.norm(normal))
    for source,target in [(0,1),(1,0)]:
        ids=np.array(patches[source]['vertices']);mesh=trimesh.Trimesh(points[target],faces[patches[target]['face_ids']],process=False)
        distances=[];closest=[]
        for start in range(0,len(ids),32):
            p,d,_=trimesh.proximity.closest_point(mesh,points[source][ids[start:start+32]])
            closest.extend(p);distances.extend(d)
        distances=np.array(distances);closest=np.array(closest);active=np.flatnonzero(distances<=tolerance)
        source_witness=triangle_witness(points[source][ids[active]]);target_witness=triangle_witness(closest[active])
        results.append(dict(source=source,target=target,region_vertices=len(ids),within_tolerance_count=len(active),
            within_tolerance_vertices=ids[active].tolist(),minimum_distance_m=float(distances.min()),
            source_area_witness=source_witness,target_area_witness=target_witness,
            source_witness_positions_m=points[source][ids[active]][source_witness['indices']].tolist(),
            target_witness_positions_m=closest[active][target_witness['indices']].tolist()))
    return dict(directions=results,opposing_normal_degrees=float(np.degrees(np.arccos(np.clip(-normals[0]@normals[1],-1,1)))))


def run(export,study):
    export=Path(export).resolve();study=Path(study).resolve();recipe=read(study/'request.json');patches=read(study/'palm-region.json')
    if (export/'region-verification.json').exists():raise ValueError('Preserve earlier verification')
    if read(export/'pipeline.json')['status']!='complete':raise ValueError('Export not complete')
    manifest=read(export/'manifest.json');screen=recipe['screen'];result={}
    for variant in ['input','candidate']:
        scene=read(export/(variant+'-scene.json'))['scene'];points=[];files={}
        for name in ['A','B']:
            entry=scene['actors'][name];path=export/entry['preview_glb']
            if sha256(path)!=manifest['assets'][entry['preview_glb']]['sha256']:raise ValueError('Export payload changed')
            rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
            world=sampler.sample(float(np.float32(75/30)));r=Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix()
            points.append(rig.vertices(world)@r.T+np.array(entry['transform']['translation_m']));files[name]=sha256(path)
            if name=='A':
                # Read triangle indices directly from the exported GLB, not fitter caches.
                from rig_asset import array
                primitive=rig.document['meshes'][0]['primitives'][0];faces=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
        with threadpool_limits(limits=1):
            region=measure(points,[patches['A'],patches['B']],faces,screen['max_contact_distance_m'])
            collision=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
        region_pass=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=screen['min_triangle_area_m2'] for d in region['directions'])
        # The existing independent penetration report defines its own field names.
        result[variant]=dict(glb_sha256=files,region=region,collision=collision,region_area_screen_passed=region_pass,
            orientation_screen_passed=region['opposing_normal_degrees']<=screen['opposing_normal_max_degrees'],
            penetration_screen_passed=max(c['max_depth_m'] for c in collision)<=screen['max_event_penetration_m'])
        result[variant]['event_screens_passed']=all(result[variant][k] for k in ['region_area_screen_passed','orientation_screen_passed','penetration_screen_passed'])
        save(export/'region-verification.json',dict(at=now(),frame=75,variants=result,request_sha256=sha256(study/'request.json'),region_sha256=sha256(study/'palm-region.json'),
            verifier_sha256=sha256(__file__),screen=screen,quality_approved=False,
            scope='Independent all-patch nearest-surface distances, realized area witness and full-body vertex-in-mesh audit at one decoded event frame. Region intent supersedes center-point equality for this experiment only. Not a continuous collision, triangle-intersection, anatomical or action-quality certificate.'))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('export',type=Path);p.add_argument('study',type=Path);a=p.parse_args();run(a.export,a.study)
