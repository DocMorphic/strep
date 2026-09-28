"""Compare identical released motion with/without the authored platform collider."""
import itertools
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from scene_constraints import sample_object
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def corner_gap(p,r,size,p2,r2,size2):
    # Independent SAT implementation: project all eight world corners and
    # compare both escape directions, including nested intervals.
    signs=np.array(list(itertools.product([-1.,1.],repeat=3)))
    a=(signs*np.asarray(size)/2)@r.T+p;b=(signs*np.asarray(size2)/2)@r2.T+p2
    axes=[*r.T,*r2.T]+[np.cross(x,y) for x in r.T for y in r2.T]
    gaps=[]
    for axis in axes:
        length=np.linalg.norm(axis)
        if length<1e-9:continue
        axis=axis/length;x=a@axis;y=b@axis
        gaps.append(max(y.min()-x.max(),x.min()-y.max()))
    return float(max(gaps))


def main():
    report=ROOT/'reports/static-collider-v1';protocol=read(report/'protocol.json')
    assert sha256(report/'source.json')==protocol['fixture_sha256']
    jobs=read(report/'jobs.json')['jobs'];rows=[];source=read(report/'source.json')['scene'];platform=source['objects']['platform']
    cp,cr=sample_object(platform,source['frame_count']);size=source['objects']['box']['size_m'];release=121
    p,r=sample_object(source['objects']['box'],source['frame_count'])
    prefix_depth=max(0.,max(-corner_gap(pos,rot,size,cp[f],cr[f],platform['size_m']) for f,(pos,rot) in enumerate(zip(p[:release+1],r[:release+1]))))
    for job in jobs:
        folder=ROOT/'reports'/job['collection'];request=read(folder/'request.json');obs=read(folder/'simulation/engine-output.json')['observations']
        assert request['authored']['revision']==jobs_revision(report,jobs)
        rot=Rotation.from_quat([o['rotation_xyzw'] for o in obs]).as_matrix()
        depth=max(0.,max(-corner_gap(o['position_m'],rr,size,cp[release],cr[release],platform['size_m']) for o,rr in zip(obs,rot)))
        audit=read(folder/'release-audit.json');mode=request['authored']['collision_mode']
        if mode=='static_scene':
            assert abs(depth-audit['scene_collisions']['colliders'][0]['max_penetration_m'])<1e-10
            assert 'object:platform' in audit['scene_collisions']['final_contact_colliders'] and audit['first_floor_contact_source_frame'] is None
        else:assert all('object:platform' not in o['contact_colliders'] for o in obs)
        doc,binary=read_glb(folder/'objects.glb');sampler=AnimationSampler(doc,binary,0)
        indices={node['extras']['strep_object_id']:i for i,node in enumerate(doc['nodes'])}
        decoded_depth=0.
        for frame in np.arange(release,179.5,.5):
            matrices=sampler.sample(float(np.float32(frame/30)));a=matrices[indices['box']];b=matrices[indices['platform']]
            decoded_depth=max(decoded_depth,-corner_gap(a[:3,3],a[:3,:3],size,b[:3,3],b[:3,:3],platform['size_m']))
        rows.append(dict(job=job['id'],mode=mode,physics_samples=len(obs),independent_platform_depth_max_m=depth,decoded_frame_half_frame_platform_depth_max_m=float(decoded_depth),release_audit=audit,package_sha256=sha256(folder/'scene-animation.zip')))
    assert {r['mode'] for r in rows}=={'static_scene','floor_only'}
    a=next(r for r in rows if r['mode']=='floor_only');b=next(r for r in rows if r['mode']=='static_scene')
    save(report/'comparison.json',dict(at=now(),cases=rows,authored_prefix_platform_depth_max_m=prefix_depth,
        scope='Same existing actor/box request, explicit platform geometry; only static collision mode changes. Independent eight-corner SAT, physics and decoded half frames. Prefix intersections remain authored defects; this is a release-component study, not a successful complete pickup.',
        after_release_depth_improved=b['independent_platform_depth_max_m']<a['independent_platform_depth_max_m'],human_approved=False))
    print(dict(prefix_depth_m=prefix_depth,baseline_depth_m=a['independent_platform_depth_max_m'],candidate_depth_m=b['independent_platform_depth_max_m']))


def jobs_revision(report,jobs):
    return read(ROOT/'reports'/jobs[0]['collection']/'request.json')['authored']['revision']


if __name__=='__main__':main()
