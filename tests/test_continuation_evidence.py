import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from continuation_evidence import cumulative_controls,load_continuation
from strep import save,read,sha256


@pytest.mark.parametrize('fault',[None,'delta_only','extra','matrix','nan','factor','failed'])
def test_cumulative_controls_cannot_be_replaced_by_the_increment(fault):
    request=dict(cumulative_controls=[.01,.02,.03])
    solver=dict(increment=[.001,-.002,.003],solver=dict(proposal_hard_checks=True))
    expected=np.array(request['cumulative_controls'])+.5*np.array(solver['increment'])
    trial=dict(factor=.5,controls=expected.tolist())
    if fault=='delta_only': trial['controls']=(.5*np.array(solver['increment'])).tolist()
    if fault=='extra': trial['controls'].append(0.)
    if fault=='matrix': trial['controls']=[trial['controls']]
    if fault=='nan': trial['controls'][0]=float('nan')
    if fault=='factor': trial['factor']=True
    if fault=='failed': solver['solver']['proposal_hard_checks']=False
    if fault is None: np.testing.assert_array_equal(cumulative_controls(request,solver,trial),expected)
    else:
        with pytest.raises((ValueError,AssertionError)): cumulative_controls(request,solver,trial)


def fixture(root):
    (root/'current').mkdir();(root/'implementation').mkdir();(root/'trial-0').mkdir()
    save(root/'current/sample-000.json',dict(sample=0))
    save(root/'current-index.json',{'sample-000.json':sha256(root/'current/sample-000.json')})
    (root/'implementation/method.py').write_text('# fixture\n')
    save(root/'request.json',dict(cumulative_controls=[.01,.02,.03],inputs={},
        implementation={'method.py':sha256(root/'implementation/method.py')}))
    save(root/'solver.json',dict(increment=[0.,0.,0.],solver=dict(proposal_hard_checks=True)))
    np.savez(root/'linearization.npz',gaps=np.array([-.01]))
    actors=[]
    for i in range(2):
        path=root/'trial-0'/f'actor-{i}.glb';path.write_bytes(b'fixture'+bytes([i]))
        actors.append(dict(actor=str(i),path=path.name,sha256=sha256(path)))
    trial=dict(factor=.5,controls=[.01,.02,.03],actors=actors,angular_rates=[dict(actor=a['actor']) for a in actors])
    save(root/'trials.json',[trial]);save(root/'trial-0/review.json',trial)
    result=dict(status='complete')
    for name in ['request.json','trials.json','current-index.json','linearization.npz','solver.json']:
        result[name.split('.')[0].replace('-','_')+'_sha256']=sha256(root/name)
    save(root/'result.json',result)
    return trial


@pytest.mark.parametrize('fault',[None,'incomplete','request','matrix','witness','snapshot','clip','review','angular_order','clip_escape'])
def test_completed_replay_requires_bound_inputs_and_exports(tmp_path,fault):
    trial=fixture(tmp_path)
    if fault=='incomplete':
        result=read(tmp_path/'result.json');result['status']='processing';save(tmp_path/'result.json',result)
    if fault=='request':save(tmp_path/'request.json',{})
    if fault=='matrix':np.savez(tmp_path/'linearization.npz',gaps=np.array([0.]))
    if fault=='witness':save(tmp_path/'current/sample-000.json',{})
    if fault=='snapshot':(tmp_path/'implementation/method.py').write_text('changed')
    if fault=='clip':(tmp_path/'trial-0/actor-0.glb').write_bytes(b'changed')
    if fault=='review':save(tmp_path/'trial-0/review.json',{})
    if fault in ['angular_order','clip_escape']:
        if fault=='angular_order':trial['angular_rates'].reverse()
        else:trial['actors'][0]['path']='../actor-0.glb'
        save(tmp_path/'trials.json',[trial]);save(tmp_path/'trial-0/review.json',trial)
        result=read(tmp_path/'result.json');result['trials_sha256']=sha256(tmp_path/'trials.json');save(tmp_path/'result.json',result)
    if fault is None:
        _,_,trials,files=load_continuation(tmp_path)
        assert trials==[trial] and str(tmp_path/'current/sample-000.json') in files
    else:
        with pytest.raises(ValueError):load_continuation(tmp_path)


def test_continuation_replay_reconstructs_nonzero_glbs_and_keeps_failed_trials(tmp_path,monkeypatch):
    pytest.importorskip('trimesh')
    from types import SimpleNamespace
    from test_scene_pair_problem import actors,samples
    from scene_pair_problem import ScenePairProblem
    import scene_pair_problem
    import diagnose_scene_pair_limits
    from diagnose_scene_pair_refinement import refine_knots
    from refined_reserve_inputs import install_refined_models
    from gltf_tools import read_glb
    import rig_asset
    from study_scene_pair_fit import exported_motion
    from joint_angular_rates import compare_angular_rates
    from verify_scene_pair_continuation import run
    study=tmp_path/'continuation';study.mkdir();parent=tmp_path/'parent';parent.mkdir()
    (parent/'source').mkdir();(study/'current').mkdir();(study/'implementation').mkdir()
    def make_pair():
        pair=actors()
        for i,a in enumerate(pair):
            a['source']=tmp_path/f'source-{i}.glb'
            a['rig'].document=a['model'].document
        return pair
    pair=make_pair();descriptions=[]
    for a in pair:
        old=a['model'];old.export(np.zeros(old.size),a['source'])
        knots,mapping=refine_knots(old.knots,len(old.nodes))
        descriptions.append(dict(actor=a['name'],original_knots_s=old.knots.tolist(),refined_knots_s=knots.tolist(),
            original_controls=old.size,refined_controls=mapping.shape[0]))
    original_models=[a['model'] for a in pair]
    install_refined_models(pair,descriptions)
    rows=samples(pair);problem=ScenePairProblem(pair,rows)
    gaps=problem.surface_rows([a['model'].source_world for a in pair])['gaps']
    count=len(rows)
    for i,row in enumerate(rows):
        for s in [0,1]:row['directions'][s]['records'][0]['gap_m']=float(gaps[s*count+i])
    index={}
    for i,row in enumerate(rows):
        name=f'sample-{i:03d}.json';save(parent/'source'/name,row);save(study/'current'/name,row)
        index[name]=sha256(parent/'source'/name)
    save(parent/'source-index.json',index);save(study/'current-index.json',index)
    # The fixture has synthetic skin points, but native tracks use actual GLB
    # export/decoding. This test makes no full-mesh collision claim.
    def load(path):
        doc,binary=read_glb(path)
        return SimpleNamespace(document=doc,binary=binary,joints=doc['skins'][0]['joints'])
    monkeypatch.setattr(rig_asset.RigAsset,'load',staticmethod(load))
    base=np.cos(np.arange(problem.size))*.0002;increment=np.sin(np.arange(problem.size))*.0001
    controls=base+.5*increment
    records,worlds,bounds=exported_motion(problem,controls,study/'trial-0')
    angular=[]
    for a,old,world in zip(pair,original_models,worlds):
        joints=a['rig'].joints
        names=[a['model'].document['nodes'][j]['name'] for j in joints]
        angular.append(dict(actor=a['name'],rates=compare_angular_rates(old.source_world[:,joints,:,:][:,:,:3,:3],
            world[:,joints,:,:][:,:,:3,:3],old.times,old.knots,names,speed_tolerance=1e-5,acceleration_tolerance=1e-5)))
    surface=problem.surface_rows(worlds);excess=float(np.maximum(-surface['gaps']-surface['depth_caps'],0).max(initial=0))
    reasons=[]
    if any(a['rate_failures'] for a in records):reasons.append('exported_motion')
    if any(not a['preserved'] for a in records):reasons.append('preservation_or_budget')
    if max(bounds.values())>1e-6:reasons.append('original_surface_bounds')
    if any(v['exceeding_observations'] for a in angular for v in a['rates'].values()):reasons.append('exported_angular_motion')
    if excess>1e-6:reasons.append('refreshed_surface_planes')
    assert reasons
    trial=dict(factor=.5,controls=controls.tolist(),actors=records,bounds=bounds,angular_rates=angular,
        refreshed_plane_excess_m=excess,reasons=reasons,preliminary_pass=False)
    save(study/'trials.json',[trial]);save(study/'trial-0/review.json',trial)
    save(study/'solver.json',dict(increment=increment.tolist(),solver=dict(proposal_hard_checks=True)))
    save(parent/'trials.json',[dict(folder='selected',accepted_local_step=True,reasons=[],controls=base.tolist())])
    save(parent/'result.json',dict(status='complete',selected='selected',trials_sha256=sha256(parent/'trials.json')))
    inputs={str(parent/name):sha256(parent/name) for name in ['trials.json','result.json']}
    save(study/'request.json',dict(study=str(parent),inputs=inputs,implementation={},cumulative_controls=base.tolist()))
    np.savez(study/'linearization.npz',gaps=gaps)
    result=dict(status='complete')
    for name in ['request.json','solver.json','linearization.npz','current-index.json','trials.json']:
        result[name.split('.')[0].replace('-','_')+'_sha256']=sha256(study/name)
    save(study/'result.json',result)
    monkeypatch.setattr(diagnose_scene_pair_limits,'load_bound_study',lambda _: (dict(prepared_request=str(parent/'request.json'),curve_actors=descriptions),{},{}))
    monkeypatch.setattr(scene_pair_problem,'load_actors',lambda _: ({},make_pair()))
    output=tmp_path/'replay';run(study,output)
    verification=read(output/'verification.json');reviews=read(output/'reviews.json')
    assert verification['reconstructed_exports']==2
    assert verification['positional_observations']==2872
    assert verification['preliminary_passes']==0 and not verification['accepted_for_publication']
    assert reviews[0]['reasons']==reasons
    assert all(a['exact_export_reconstruction'] for a in reviews[0]['actors'])


@pytest.mark.parametrize('fault',[None,'unbound','different','rejected','duplicate'])
def test_continuation_must_start_from_selected_bound_parent(tmp_path,fault):
    from continuation_evidence import parent_trial
    row=dict(folder='candidate',accepted_local_step=True,reasons=[],controls=[.1,.2,.3])
    if fault=='rejected':row['reasons']=['failed']
    save(tmp_path/'trials.json',[row,row] if fault=='duplicate' else [row])
    save(tmp_path/'result.json',dict(status='complete',selected='candidate',trials_sha256=sha256(tmp_path/'trials.json')))
    request=dict(study=str(tmp_path),cumulative_controls=[.1,.2,.3],inputs={str(tmp_path/name):sha256(tmp_path/name) for name in ['result.json','trials.json']})
    if fault=='unbound':request['inputs'].pop(str(tmp_path/'trials.json'))
    if fault=='different':request['cumulative_controls'][0]+=.01
    if fault is None:assert parent_trial(request)==row
    else:
        with pytest.raises((ValueError,AssertionError)):parent_trial(request)
