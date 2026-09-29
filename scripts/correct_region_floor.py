"""Lift only the pre-approach root, retaining the complete interaction exactly."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from region_floor_envelope import solve_lift


def run(approach_report,dense_audit,output):
    approach_report,dense_audit,output=[Path(p).resolve() for p in (approach_report,dense_audit,output)]
    patch_protocol,patch=read(approach_report/'protocol.json'),read(approach_report/'result.json')
    verification=read(dense_audit/'verification.json');dense=read(dense_audit/'candidate.json')
    if patch['status']!='complete' or sha256(approach_report/'motion.npz')!=patch['motion_sha256']:raise ValueError('Completed approach required')
    if verification['approach_patch']['result_sha256']!=sha256(approach_report/'result.json') or sha256(dense_audit/'candidate.glb')!=verification['variants']['candidate']['glb_sha256']:raise ValueError('Dense audit belongs to another approach')
    study=ROOT/patch_protocol['base_study'];protocol=read(study/'protocol.json');fit=ROOT/protocol['study']/'fit';summary=read(fit/'summary.json')
    folder=fit/'assets'/summary['trials'][0]['id']/'A';base=dict(np.load(folder/'limb-motion.npz',allow_pickle=False));source=dict(np.load(approach_report/'motion.npz',allow_pickle=False))
    config=read(folder/'recipe.json')['contact']['config'];existing=source['root_positions'][:,1]-base['root_positions'][:,1]
    capacity=config['max_root_lift_m']-existing;free=list(range(1,protocol['edited_interval'][0]));settings=dict(target_height_m=config['clearance_m']+.000002,smoothness=12.,free_frames=free)
    inputs={p.relative_to(ROOT).as_posix():sha256(p) for p in [approach_report/'protocol.json',approach_report/'result.json',approach_report/'motion.npz',dense_audit/'verification.json',dense_audit/'candidate.json',dense_audit/'candidate.glb',study/'protocol.json',folder/'limb-motion.npz',folder/'recipe.json']}
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    methods=['correct_region_floor.py','region_floor_envelope.py'];implementation={n:sha256(ROOT/'scripts'/n) for n in methods}
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
    save(output/'protocol.json',dict(at=now(),approach_report=approach_report.relative_to(ROOT).as_posix(),dense_audit=dense_audit.relative_to(ROOT).as_posix(),base_study=study.relative_to(ROOT).as_posix(),inputs=inputs,implementation=implementation,settings=settings,
         scope='Root-Y translation only before the approach; frame0 and frames48 onward locked. Minimum-energy nonnegative lift constrained at original dense decoded sample times, with 2 micrometre numerical reserve. Original rotations, horizontal root, contacts and event timing unchanged. Must recheck serialized full skin and motion metrics.',quality_approved=False))
    delta,solver=solve_lift(dense['frames'],dense['floor_height_m'],capacity,free,settings['target_height_m'],settings['smoothness'])
    candidate={k:v.copy() for k,v in source.items()};candidate['root_positions'][:,1]+=delta;candidate['posed_joints'][:,:,1]+=delta[:,None]
    locked=np.setdiff1d(np.arange(len(delta)),free)
    for name in source:np.testing.assert_array_equal(source[name][locked],candidate[name][locked])
    np.savez(output/'motion.npz',**candidate)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
    save(output/'result.json',dict(at=now(),status='complete',solver=solver,root_lift_delta_m=delta.tolist(),locked_frames_exact=len(locked),motion_sha256=sha256(output/'motion.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    print(dict(solver=solver,locked_frames_exact=len(locked)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('approach_report',type=Path);parser.add_argument('dense_audit',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.approach_report,args.dense_audit,args.output)
