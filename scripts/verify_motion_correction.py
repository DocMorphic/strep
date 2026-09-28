"""Independent FK, boundary, skin and motion-change diagnostics for native correction."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256
from verify_boundary_guides import positions
from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
from gltf_tools import read_glb,sample_animation,accessor
from build_soma_preview import ASSET
from rig_clip_import import AnimationSampler


def angle(a,b):
    return np.degrees(Rotation.from_matrix((a.swapaxes(-1,-2)@b).reshape(-1,3,3)).magnitude()).reshape(a.shape[:-2])


def anchor_errors(local77,root,guide,anchors):
    """Compare on the constrained 30-bone hierarchy, never a slice of 77-bone FK."""
    small=SOMASkeleton30();full=SOMASkeleton77()
    subset=[full.bone_order_names.index(n) for n in small.bone_order_names]
    expected,er=positions(guide['local_rot_mats'][:,subset].astype(float),guide['root_positions'].astype(float),small)
    p,r=positions(local77[:,subset].astype(float),root.astype(float),small)
    return float(np.linalg.norm(p[anchors]-expected[anchors],axis=-1).max()),float(angle(r[anchors],er[anchors]).max())


def verify(out):
    out=Path(out);s30=SOMASkeleton30();s77=SOMASkeleton77()
    subset=[s77.bone_order_names.index(n) for n in s30.bone_order_names]
    skin=dict(np.load(ASSET,allow_pickle=False));points=np.c_[skin['bind_vertices'],np.ones(len(skin['bind_vertices']))]
    weights=skin['lbs_weights'];indices=skin['lbs_indices'];inverse=np.linalg.inv(skin['bind_rig_transform'])
    footregions={}
    for side in ('Left','Right'):
        bones=[i for i,n in enumerate(s77.bone_order_names) if n.startswith(side) and ('Foot' in n or 'Toe' in n)]
        mask=(weights*np.isin(indices,bones)).sum(axis=1)>=.65
        assert mask.any();footregions[side]=mask
    results=[];manifest=[]
    for item in read(out/'comparison.json')['cases']:
        case=item['case'];mode=item['mode'];folder=out/case/mode
        data=dict(np.load(folder/'motion.npz',allow_pickle=False));raw=dict(np.load(out/case/'raw/motion.npz',allow_pickle=False));guide=dict(np.load(out/case/'source-guide.npz',allow_pickle=False))
        assert sha256(folder/'motion.npz')==item['output_sha256']
        assert sha256(folder/'soma.glb')==item['glb_sha256']
        assert sha256(out/case/'raw/motion.npz')==item['source_sha256']
        np.testing.assert_array_equal(data['foot_contacts'],raw['foot_contacts'])
        n=item['frames'];anchors=item['anchors']
        p,r=positions(data['local_rot_mats'].astype(float),data['root_positions'].astype(float),s77)
        np.testing.assert_allclose(p,data['posed_joints'],atol=1e-5,rtol=0)
        np.testing.assert_allclose(r,data['global_rot_mats'],atol=1e-5,rtol=0)
        error,rot_error=anchor_errors(data['local_rot_mats'],data['root_positions'],guide,anchors)
        doc,binary=read_glb(folder/'soma.glb');attrs=doc['meshes'][0]['primitives'][0]['attributes'];sampler=AnimationSampler(doc,binary,0)
        np.testing.assert_array_equal(np.concatenate([accessor(doc,binary,attrs[f'WEIGHTS_{i}']) for i in (0,1)],axis=1),weights)
        np.testing.assert_array_equal(np.concatenate([accessor(doc,binary,attrs[f'JOINTS_{i}']) for i in (0,1)],axis=1),indices)
        centroids={side:[] for side in footregions};floor=[];half_floor=[];export_error=0.
        for f in np.arange(0,n-.5,.5):
            world=sampler.sample(float(np.float32(f/30)))[1:78]
            transform=world@inverse
            vertices=np.sum(np.einsum('vwij,vj->vwi',transform[indices,:3,:],points)*weights[:,:,None],axis=1)
            depth=max(0.,float(-vertices[:,1].min()))
            if f==int(f):
                f=int(f);export_error=max(export_error,float(np.abs(world[:,:3,3]-p[f]).max()),float(np.abs(world[:,:3,:3]-r[f]).max()))
                floor.append(depth)
                for side,mask in footregions.items():centroids[side].append(vertices[mask][:,[0,2]].mean(axis=0))
            else:half_floor.append(depth)
        assert export_error<1e-5
        assert abs(max(floor)-item['native_mesh_floor_m'])<1e-5
        feet={}
        for side,channel in [('Left',0),('Right',3)]:
            contact=data['foot_contacts'][:,channel:channel+2].max(axis=1)>=.5
            flags=contact[:-1]&contact[1:]
            speed=np.linalg.norm(np.diff(centroids[side],axis=0),axis=-1)*30
            feet[side]=dict(predicted_support_steps=int(flags.sum()),predicted_support_horizontal_speed_p95_m_s=float(np.percentile(speed[flags],95)) if flags.any() else None)
        local=data['local_rot_mats'].astype(float);step=angle(local[:-1],local[1:]);root=data['root_positions'].astype(float)
        rootv=np.diff(root,axis=0)*30
        metrics=dict(anchor_max_position_error_m=error,anchor_max_global_rotation_error_degrees=rot_error,pose_screen_passed=error<=.03,floor_depth_max_m=max(floor),half_frame_floor_depth_max_m=max(half_floor),local_rotation_step_max_degrees=float(step.max()),boundary_eight_frame_step_max_degrees=float(np.r_[step[:8].ravel(),step[-8:].ravel()].max()),max_local_rotation_change_degrees=float(angle(raw['local_rot_mats'].astype(float),local).max()),max_root_change_m=float(np.linalg.norm(root-raw['root_positions'],axis=-1).max()),max_root_speed_m_s=float(np.linalg.norm(rootv,axis=-1).max()),max_root_acceleration_m_s2=float(np.linalg.norm(np.diff(rootv,axis=0)*30,axis=-1).max()),preview_error=export_error,feet=feet)
        # Passing the position target is a fact separate from movement quality.
        metrics['exact_anchor_screen_passed']=error<1e-4 and rot_error<.01
        row=dict(case=case,mode=mode,metrics=metrics);results.append(row)
        manifest.append(dict(id=case+'-'+mode,path=case+'/'+mode+'/soma.glb',sha256=item['glb_sha256'],frames=n,fps=30))
        print(case,mode,metrics,flush=True)
    save(out/'verification.json',dict(cases=results,scope='Independent NumPy hierarchy FK and SciPy geodesics; every GLB frame, all eight skin weights, all vertices at integer and half frames. Predicted contact labels retained, not confirmed. No semantic/dynamics/animator acceptance.'))
    save(out/'manifest.json',dict(cases=manifest))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);verify(p.parse_args().output)
