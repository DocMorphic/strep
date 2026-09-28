"""Independent exported-skin screens and actual engine-bone/proxy clock check."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from scene_constraints import pose

OUT=ROOT/'reports/actor-proxy-release-v1'


def main():
    source=read(ROOT/read(OUT/'protocol.json')['source']/'source.json')['scene']
    folders={label:ROOT/'reports/scene-release-jobs'/name for label,name in [('baseline','actor-proxy-v1-baseline'),('candidate','actor-proxy-v3-candidate')]}
    actor=source['actors']['A'];path=ROOT/read(OUT/'protocol.json')['source']/actor['preview_glb']
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0);placement_p,placement_r=pose(actor['transform'])
    samplers={}
    for label,folder in folders.items():
        doc,binary=read_glb(folder/'objects.glb');samplers[label]=AnimationSampler(doc,binary,0)
        assert len(doc['nodes'])==1
    rows={label:dict(max_skin_vertex_depth_m=0.,frames_over_1cm=0,after_release_max_depth_m=0.,authored_prefix_max_depth_m=0.) for label in folders}
    for f in np.arange(0,179.5,.5):
        vertices=rig.vertices(sampler.sample(float(f)/30))@placement_r.T+placement_p
        for label,s in samplers.items():
            m=s.sample(float(np.float32(f/30)))[0];local=(vertices-m[:3,3])@m[:3,:3]
            depth=float(max(0.,(np.array([.1,.1,.1])-np.abs(local)).min(axis=1).max()))
            row=rows[label];row['max_skin_vertex_depth_m']=max(row['max_skin_vertex_depth_m'],depth)
            row['frames_over_1cm']+=int(depth>.01)
            key='after_release_max_depth_m' if f>121 else 'authored_prefix_max_depth_m';row[key]=max(row[key],depth)
    # This uses actual Godot animation playback, not the compiler's Python FK.
    engine=read(ROOT/'reports/godot-actor-proxy-candidate-v1/engine-output.json')['scenes'][0]
    names=engine['actors']['A']['bone_names'];obs=read(folders['candidate']/'simulation/engine-output.json')['observations']
    parts=read(folders['candidate']/'source/actor-proxies.json')['actors'][0]['parts_geometry']
    pe=re=0.
    for frame in range(121,180):
        states={s['id']:s for s in obs[(frame-121)*8]['moving_colliders']}
        for part in parts:
            matrix=np.array(engine['frames'][frame]['A'][names.index(part['name'])]);r=matrix[:3].T;p=matrix[3]
            state=states['actor:A:'+part['name']]
            pe=max(pe,float(np.max(np.abs(p+r@part['center_local_m']-state['position_m']))))
            re=max(re,float(np.max(np.abs(r-Rotation.from_quat(state['rotation_xyzw']).as_matrix()))))
    assert max(pe,re)<1e-6
    save(OUT/'verification.json',dict(at=now(),decoded_skin=rows,whole_and_half_frame_samples=359,
        actual_engine_bone_proxy_clock=dict(frames=59,parts=21,position_error_m=pe,rotation_element_error=re,passed=True),
        files={k:sha256(v/'scene-animation.zip') for k,v in folders.items()},
        scope='All decoded skin vertices against box at whole/half frames; not edge-only intersections or continuous time. Actual engine bone transforms plus local proxy offsets match recorded physics poses at every shared integer frame.',quality_approved=False))
    print(rows);print('engine/proxy errors',pe,re)


if __name__=='__main__':main()
