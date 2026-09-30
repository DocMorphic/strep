import sys
from pathlib import Path
import numpy as np
import pytest
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_scene_pair_fit import rate_check


@pytest.mark.parametrize('fault', ['extra','missing','nan','matrix','actors','order'])
def test_replay_rejects_incomplete_or_unconsumed_controls(fault):
    from verify_scene_pair_fit import trial_controls
    actors=[dict(name=n,model=SimpleNamespace(size=3)) for n in ['A','B']]
    trial=dict(actors=[dict(actor=n) for n in ['A','B']],controls=[0.]*6)
    if fault=='extra':trial['controls'].append(0.)
    if fault=='missing':trial['controls'].pop()
    if fault=='nan':trial['controls'][0]=float('nan')
    if fault=='matrix':trial['controls']=[[0.,0.,0.],[0.,0.,0.]]
    if fault=='actors':trial['actors'].pop()
    if fault=='order':trial['actors'].reverse()
    with pytest.raises(ValueError):trial_controls(trial,actors)


def test_independent_replay_detects_rate_increase_and_counts_every_joint():
    times = np.arange(25)/120; source = np.zeros((25, 2, 3))
    source[:, 0, 0] = times; knots = [0., .05, .1, .15, .2]
    candidate = source.copy(); candidate[12, 1, 1] = .001
    result = rate_check(source, candidate, times, knots)
    assert result['checked'] == (24+23)*2
    assert result['failures'] == 5  # Two velocity and three acceleration stencils.
    assert result['maximum_excess'] > 20
    unchanged = rate_check(source, source.copy(), times, knots)
    assert unchanged['failures'] == 0


def test_replay_preserves_local_span_caps_instead_of_global_peak_allowance():
    times = np.arange(61)/120; source = np.zeros((61, 1, 3))
    source[:25, 0, 0] = np.sin(times[:25]*10)
    candidate = source.copy(); candidate[50, 0, 1] = .0001
    result = rate_check(source, candidate, times, [0., .25, .4, .5])
    assert result['failures'] == 5


def test_full_refined_replay_reconstructs_glbs_and_uses_original_rate_bins(tmp_path,monkeypatch):
    import verify_scene_pair_fit as module
    from test_timed_rotation_edit import fixture
    from timed_rotation_edit import TimedRotationEdit
    from diagnose_scene_pair_refinement import refine_knots
    from gltf_tools import read_glb
    from rig_clip_import import AnimationSampler
    from paired_temporal_neighbor import rotation_channels
    from scipy.spatial.transform import Rotation
    from strep import save,read,sha256
    class Rig:
        @staticmethod
        def load(path):
            doc,binary=read_glb(path)
            return SimpleNamespace(document=doc,binary=binary,joints=doc['skins'][0]['joints'],
                vertices=lambda world:np.empty((0,3)))
    monkeypatch.setattr(module,'RigAsset',Rig)
    prepared=tmp_path/'prepared';prepared.mkdir();study=tmp_path/'study';study.mkdir()
    (study/'source').mkdir();(study/'candidate').mkdir()
    doc,binary=fixture();times=np.arange(181)/120;window=[.1,1.3];protected=[[.713,.713]]
    coarse=TimedRotationEdit(doc,binary,['Arm','Twin'],times,window,protected)
    fine_knots,_=refine_knots(coarse.knots,2)
    entries={};descriptions=[];reports=[];controls=[];expected=[]
    for index,name in enumerate(['A','B']):
        path=prepared/f'actor-{index}.glb';coarse.export(np.zeros(coarse.size),path)
        source_doc,source_binary=read_glb(path)
        model=TimedRotationEdit(source_doc,source_binary,['Arm','Twin'],times,window,protected,knots=fine_knots)
        part=np.sin(np.arange(model.size)+index)*.001
        target=study/'candidate'/path.name;model.export(part,target);controls.extend(part.tolist())
        edited_doc,edited_binary=read_glb(target);sampler=AnimationSampler(edited_doc,edited_binary,0)
        worlds=np.array([sampler.sample(t) for t in times]);source_world=model.source_world
        check=rate_check(source_world[:,:,:3,3],worlds[:,:,:3,3],times,coarse.knots);expected.append(check)
        original=rotation_channels(source_doc,source_binary);edited=rotation_channels(edited_doc,edited_binary)
        maximum=max(float(np.rad2deg((Rotation.from_quat(q).inv()*Rotation.from_quat(edited[n][2])).magnitude()).max()) for n,(_,_,q) in original.items())
        entries[name]=dict(path=path.name,sha256=sha256(path),placement=dict(rotation_xyzw=[0,0,0,1],translation_m=[0,0,0]))
        descriptions.append(dict(actor=name,original_knots_s=coarse.knots.tolist(),refined_knots_s=fine_knots.tolist(),original_controls=coarse.size,refined_controls=model.size))
        reports.append(dict(actor=name,path=path.name,sha256=sha256(target),rate_failures=check['failures'],maximum_edit_degrees=maximum))
    save(prepared/'request.json',dict(actors=entries,sample_times_seconds=times.tolist(),protected_seconds=protected,
        authored=dict(knots_s=coarse.knots.tolist(),window_s=window,limit_degrees=5,actors={name:dict(joints=['Arm','Twin']) for name in entries})))
    index={}
    for i,t in enumerate(times):
        name=f'sample-{i:03d}.json';save(study/'source'/name,dict(sample=i,time_s=float(t),directions=[dict(source=0,target=1,records=[]),dict(source=1,target=0,records=[])]));index[name]=sha256(study/'source'/name)
    save(study/'source-index.json',index);np.savez(study/'linearization.npz',gaps=np.empty(0))
    save(study/'trials.json',[dict(folder='candidate',actors=reports,controls=controls,geometry=None)])
    save(study/'request.json',dict(prepared_request=str(prepared/'request.json'),curve_actors=descriptions,
        inputs={str(prepared/'request.json'):sha256(prepared/'request.json')},implementation={}))
    save(study/'result.json',dict(status='complete',trials=1,request_sha256=sha256(study/'request.json'),
        trials_sha256=sha256(study/'trials.json'),linearization_sha256=sha256(study/'linearization.npz'),source_index_sha256=sha256(study/'source-index.json')))
    output=tmp_path/'replay';module.run(study,output)
    result=read(output/'verification.json')
    assert result['reconstructed_exports']==2 and result['rate_observations']==2872
    for found,wanted in zip(result['trials'][0]['actors'],expected):
        assert found['exact_export_reconstruction'] and found['rates']==wanted
    assert not result['quality_approved']
