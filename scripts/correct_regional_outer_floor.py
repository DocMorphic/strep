"""Root-only floor repair before the approach; preserve the interaction exactly."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from region_floor_envelope import solve_lift
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb


def run(boundary,base_audit,output):
    boundary,base_audit,output=[Path(p).resolve() for p in (boundary,base_audit,output)]
    prior,result=read(boundary/'protocol.json'),read(boundary/'result.json');base=ROOT/prior['base_study'];bp=read(base/'protocol.json')
    dense=read(base_audit/'geometry/verification.json')
    if result['status']!='complete' or sha256(boundary/'motion.npz')!=result['candidate_sha256'] or sha256(boundary/'protocol.json')!=result['protocol_sha256']:raise ValueError('Matching completed boundary patch required')
    if dense['result_sha256']!=sha256(base/'result.json') or dense['protocol_sha256']!=sha256(base/'protocol.json'):raise ValueError('Floor samples belong to another base trajectory')
    if dense['variants']['candidate']['glb_sha256']!=sha256(base/'candidate.glb'):raise ValueError('Base exported clip changed')
    source=dict(np.load(boundary/'motion.npz',allow_pickle=False));base_motion=dict(np.load(base/'motion.npz',allow_pickle=False));original=dict(np.load(base/'source-motion.npz',allow_pickle=False))
    cutoff=bp['edited_interval'][0];free=list(range(1,cutoff));prefix=np.arange(cutoff+1)
    # Reuse only measurements whose entire interpolation support is unchanged.
    for key in source:np.testing.assert_array_equal(source[key][prefix],base_motion[key][prefix])
    selected=[r for r in dense['variants']['candidate']['rows'] if r['frame']<=cutoff]
    times=[r['frame'] for r in selected];heights=[r['minimum_floor_m'] for r in selected]
    capacities=bp['config']['max_root_lift_m']-(source['root_positions'][:,1]-original['root_positions'][:,1])
    settings=dict(free_frames=free,sample_interval=[0,cutoff],target_height_m=bp['config']['clearance_m']+.000002,smoothness=12.)
    inputs=dict(prior['inputs']);inputs.update({str(p):sha256(p) for p in [boundary/'protocol.json',boundary/'result.json',boundary/'motion.npz',base_audit/'geometry/verification.json',base/'motion.npz',base/'candidate.glb',ASSET]})
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Floor input changed')
    for name,digest in prior['implementation'].items():
        if sha256(boundary/'implementation'/name)!=digest:raise ValueError('Boundary method snapshot changed')
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    protocol={**prior,**dict(at=now(),boundary_patch=boundary.relative_to(ROOT).as_posix(),floor_base_audit=base_audit.relative_to(ROOT).as_posix(),floor_settings=settings,
        inputs=inputs,implementation={q.name:sha256(q) for q in snap.iterdir()},
        scope='Root-Y-only correction in frames before approach. Reuse base dense samples only after proving unchanged native interpolation support. First key and approach/grasp/guard/release locked. Two-micrometre guidance reserve; original full-clip gates unchanged and actual export must be remeasured.',quality_approved=False)}
    save(output/'protocol.json',protocol)
    delta,solver=solve_lift(times,heights,capacities,free,settings['target_height_m'],settings['smoothness'])
    candidate={k:v.copy() for k,v in source.items()};candidate['root_positions'][:,1]+=delta;candidate['posed_joints'][:,:,1]+=delta[:,None]
    locked=np.setdiff1d(np.arange(bp['frame_count']),free)
    for key in source:np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:shutil.copyfile(boundary/name,output/name)
    np.savez(output/'motion.npz',**candidate);save(output/'recipe.json',dict(kind='pre-approach-root-lift-v1',root_lift_delta_m=delta.tolist(),quality_approved=False))
    skin=dict(np.load(ASSET,allow_pickle=False));doc,binary,_,_=make_preview(skin,candidate,np.zeros(3),repeat=False);write_glb(output/'candidate.glb',doc,binary)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Floor input changed during correction')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Floor method changed during correction')
    record=dict(at=now(),status='complete',solver=solver,root_lift_delta_m=delta.tolist(),locked_frames_exact=len(locked),
        candidate_sha256=sha256(output/'motion.npz'),candidate_glb_sha256=sha256(output/'candidate.glb'),source_glb_sha256=sha256(output/'source.glb'),
        recipe_sha256=sha256(output/'recipe.json'),authored_scene_sha256=sha256(output/'authored-scene.json'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False)
    save(output/'result.json',record);print(dict(solver=solver,locked_frames_exact=len(locked)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('boundary',type=Path);parser.add_argument('base_audit',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.boundary,args.base_audit,args.output)
