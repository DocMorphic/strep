"""Independent corner-SAT and exported shared-clock check for the moving study."""
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from strep import ROOT,read,save,sha256,now
from verify_static_release import corner_gap
from scene_constraints import sample_object
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def main():
    out=ROOT/'reports/moving-collider-v1';protocol=read(out/'protocol.json')
    assert sha256(out/'source.json')==protocol['fixture_sha256']
    source=read(out/'source.json')['scene'];jobs=read(out/'jobs.json')['jobs'];assert len(jobs)==1
    folder=ROOT/'reports'/jobs[0]['collection'];request=read(folder/'request.json');release=request['authored']['release_frame']
    actual=read(folder/'simulation/engine-output.json');obs=actual['observations'];fps=actual['physics_fps']
    assert actual['backend']=='Jolt Physics' and actual['direct_state_class']=='JoltPhysicsDirectBodyState3D'
    assert read(folder/'pipeline.json')['status']=='complete'
    p,r=sample_object(source['objects']['platform'],source['frame_count'])
    times=release+np.arange(len(obs))*30/fps
    cp=np.array([np.interp(times,np.arange(len(p)),p[:,axis]) for axis in range(3)]).T
    cr=Slerp(np.arange(len(p)),Rotation.from_matrix(r))(times).as_matrix()
    box=source['objects']['crate'];platform=source['objects']['platform']
    br=Rotation.from_quat([o['rotation_xyzw'] for o in obs]).as_matrix()
    depth=max(0.,max(-corner_gap(o['position_m'],rot,box['size_m'],pos,rotation,platform['size_m']) for o,rot,pos,rotation in zip(obs,br,cp,cr)))
    audit=read(folder/'release-audit.json');assert abs(depth-audit['scene_collisions']['colliders'][0]['max_penetration_m'])<1e-10
    assert 'object:platform' in obs[-1]['contact_colliders']
    doc,binary=read_glb(folder/'objects.glb');sampler=AnimationSampler(doc,binary,0)
    indices={node['extras']['strep_object_id']:i for i,node in enumerate(doc['nodes'])}
    decoded_depth=0.;prefix_depth=0.;count=0
    for frame in np.arange(0,source['frame_count']-.5,.5):
        matrices=sampler.sample(float(np.float32(frame/30)));a=matrices[indices['crate']];b=matrices[indices['platform']]
        penetration=max(0.,-corner_gap(a[:3,3],a[:3,:3],box['size_m'],b[:3,3],b[:3,:3],platform['size_m']))
        if frame<=release:prefix_depth=max(prefix_depth,penetration)
        else:decoded_depth=max(decoded_depth,penetration)
        count+=1
    save(out/'comparison.json',dict(at=now(),job=folder.name,physics_samples=len(obs),independent_physics_depth_m=depth,
        decoded_whole_and_half_frame_samples=count,decoded_depth_m=decoded_depth,authored_prefix_depth_m=prefix_depth,
        release_audit=audit,package_sha256=sha256(folder/'scene-animation.zip'),
        geometry_screens_passed=max(depth,decoded_depth,prefix_depth)<=.01,
        scope='Authored release/kinematic platform component, not a generated human interaction or held-out action success. Eight-corner SAT independent of production center/radius SAT. No actor collisions or human ratings.',human_approved=False))
    print(dict(depth_m=depth,decoded_depth_m=decoded_depth,prefix_depth_m=prefix_depth))


if __name__=='__main__':main()
