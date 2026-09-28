"""Independent force, sensitivity, source preservation and exported-track checks."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from object_dynamics import diagnose,uniform_box_inertia
from study_object_dynamics import OUT


def verify():
    protocol=read(OUT/'protocol.json');summary=read(OUT/'summary.json');rows=[]
    assert summary['protocol_sha256']==sha256(OUT/'protocol.json')
    for case,row in zip(protocol['cases'],summary['cases']):
        assert case['id']==row['id']
        folder=OUT/case['inputs'];track=read(folder/'object-track.json')
        for name,digest in case['files'].items():assert sha256(folder/name)==sha256(ROOT/case['source']/name)==digest
        p=np.asarray(track['positions_m']);q=np.asarray(track['rotations_xyzw']);fps=track['fps']
        acceleration=np.diff(p,n=2,axis=0)*fps**2
        base=None
        for scenario in row['scenarios']:
            path=OUT/scenario['path'];assert sha256(path)==scenario['sha256']
            report=read(path);mass=scenario['mass_kg'];force=np.asarray(report['required_non_gravity_force_world_N'])
            np.testing.assert_allclose(force,mass*(acceleration-protocol['gravity_m_s2']),atol=1e-10,rtol=0)
            torque=np.asarray(report['required_torque_about_com_world_Nm'])
            if base is None:base=(force/mass,torque/mass)
            np.testing.assert_allclose(force/mass,base[0],atol=1e-12,rtol=0)
            np.testing.assert_allclose(torque/mass,base[1],atol=1e-12,rtol=0)
            assert report['physical_approval'] is None
            assert report['excluded_boundary_frames']==[59,60,120,121]
        source=ROOT/case['source']/'portable/scene.glb';digest=sha256(source)
        doc,binary=read_glb(source);node=next(i for i,n in enumerate(doc['nodes']) if n.get('name')=='Interaction_box')
        sampler=AnimationSampler(doc,binary,0)
        world=np.stack([sampler.sample(float(np.float32(f/fps)))[node] for f in range(len(p))])
        decoded_p=world[:,:3,3];decoded_q=Rotation.from_matrix(world[:,:3,:3]).as_quat()
        np.testing.assert_allclose(decoded_p,p,atol=1e-6,rtol=0)
        original_r=Rotation.from_quat(q).as_matrix()
        np.testing.assert_allclose(world[:,:3,:3],original_r,atol=1e-6,rtol=0)
        phases=[{key:phase[key] for key in ['id','start_frame','end_frame_exclusive','support_assumption']} for phase in report['phases']]
        decoded=diagnose(decoded_p,decoded_q,fps=fps,mass_kg=1.,
            inertia_body_kg_m2=uniform_box_inertia(1.,track['size_m']),gravity_m_s2=protocol['gravity_m_s2'],phases=phases)
        save(OUT/'results'/case['id']/'decoded-1kg.json',decoded)
        # Differentiation amplifies float32 export error. Record, do not silently
        # equate the decoded diagnostic with the original float64 track.
        force_error=np.max(np.abs(np.asarray(decoded['required_non_gravity_force_world_N'])-base[0]))
        torque_error=np.max(np.abs(np.asarray(decoded['required_torque_about_com_world_Nm'])-base[1]))
        assert sha256(source)==digest
        rows.append(dict(id=case['id'],source_glb_sha256=digest,frames_checked=len(p),
            max_decoded_position_error_m=float(np.max(np.abs(decoded_p-p))),
            max_decoded_rotation_element_error=float(np.max(np.abs(world[:,:3,:3]-original_r))),
            max_decoded_force_component_difference_N_at_1kg=float(force_error),
            max_decoded_torque_component_difference_Nm_at_1kg=float(torque_error),
            input_hashes_unchanged=True,mass_sensitivity_linear=True))
    save(OUT/'verification.json',dict(at=now(),cases=rows,passed=True,
        scope='Independent translation second differences, mass scaling, original inputs and existing decoded GLB tracks. Not a new engine import or physical approval.'))
    print(rows)


if __name__=='__main__':verify()
