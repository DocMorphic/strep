"""Known reachable contact fixtures distinguish convergence from target feasibility."""
import importlib
import time
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from floor_contact import reconstruct,Surface
from palm_contacts import calibrate
from inspect_motion import skeleton_metadata
from build_soma_preview import ASSET
from evaluate_contact_spec import evaluate


def run():
    output=ROOT/'reports/contact-convergence-v1';output.mkdir(exist_ok=False)
    source=ROOT/'reports/scene-fitting-v2/assets/high-five-seed-11/A/previous-motion.npz'
    skin=dict(np.load(ASSET));names,parents,_=skeleton_metadata(77);m=dict(np.load(source))
    # A repeated real pose with a small rigid arm change is a constructive
    # reachability witness, not an example of realistic motion.
    base={k:np.repeat(v[60:61],30,axis=0) for k,v in m.items()}
    base['root_positions'][:,1]+=.1;base['posed_joints'][:,:,1]+=.1
    local=base['local_rot_mats'].astype(float).copy()
    angles=10*np.sin(np.linspace(0,np.pi,30))**2
    local[:,names.index('RightArm')]=local[:,names.index('RightArm')]@Rotation.from_euler('y',angles,degrees=True).as_matrix()
    witness=reconstruct(base,local,parents);palm=calibrate(skin)['RightHand']['surface_vertex'];surface=Surface(skin)
    track=[surface.vertices(r,p,[palm])[0].tolist() for r,p in zip(witness['global_rot_mats'],witness['posed_joints'])]
    np.savez(output/'base.npz',**base);np.savez(output/'witness.npz',**witness)
    summary=dict(created_at=now(),source_sha256=sha256(source),trials=[],scope='Constructively reachable engineering fixtures, not generated action or naturalness acceptance.')
    for mode in ['full_track','single_frame']:
        a,b=(0,29) if mode=='full_track' else (15,15)
        spec=dict(schema_version=2,fps=30,frame_count=30,regions={'RightHand':dict(mode='explicit',segments=[dict(start_frame=a,end_frame=b,space='track',positions_m=track[a:b+1],vertex_id=palm)])})
        assert evaluate(base,witness,skin,spec)['all_explicit_targets_within_tolerance']
        save(output/(mode+'-spec.json'),spec)
        for version in [3,4]:
            solver=importlib.import_module('support_contact_v'+str(version));start=time.perf_counter()
            result,recipe=solver.refine(base,base,skin,raw=base,contact_spec=spec)
            measured=evaluate(base,result,skin,spec);folder=output/(mode+'-v'+str(version))
            save(folder/'recipe.json',recipe);save(folder/'evaluation.json',measured);np.savez(folder/'motion.npz',**result)
            summary['trials'].append(dict(mode=mode,solver_version=version,seconds=time.perf_counter()-start,max_error_m=measured['intervals'][0]['max_error_m'],
                objective=recipe['objective'],evaluations=recipe['evaluations'],solver_sha256=sha256(ROOT/'scripts'/('support_contact_v'+str(version)+'.py'))))
            save(output/'summary.json',summary);print(summary['trials'][-1],flush=True)
    save(output/'pipeline.json',dict(status='complete'))


if __name__=='__main__':run()
