"""Imported support geometry must use actual binds and raw influence weights."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support_engine import study,observations
import run_native_support_engine as engine_audit
import audit_native_support_skin as audit
from strep import read,save,sha256


def surface(case,rig):
    p=rig.primitives[0];order=np.arange(len(p['positions']))[::-1];names=[rig.document['nodes'][n]['name'] for n in rig.joints]
    inverse=lambda m:np.vstack([m[:3,:3].T,m[:3,3]]).tolist()
    # Both bind and vertex order differ from glTF, as allowed by import.
    return dict(id=case['id'],path=case['path'],surfaces=[dict(positions=p['positions'][order].tolist(),
        bones=(len(names)-1-p['joints'][order]).astype(int).ravel().tolist(),weights=p['weights'][order].ravel().tolist(),
        binds=[dict(bone=names[i],pose=inverse(rig.inverse[i])) for i in range(len(names)-1,-1,-1)])])


def setup(study):
    folder,out=study;q,r,_=engine_audit.bind_study(folder)
    cases,refs,rows=engine_audit.prepare_cases(folder,q,r,out)
    c,ref=cases[1],refs[1]
    return c,ref,rows,surface(c,ref[0]),observations(c,ref)


def test_reordered_imported_skin_reproduces_source_support_exactly(study):
    c,ref,rows,data,poses=setup(study)
    check,errors,heights=audit.check_skin(c,data,poses,ref[0],ref[1],rows)
    assert check['skin_data_check']['passed'] and check['imported_skin_support_pass']
    assert check['skin_data_check']['influences']==4 and check['samples']==c['frames']
    assert check['maximum_vertex_distance_m']<1e-14 and len(errors)==c['frames']
    assert len(heights[0]['times_s'])==check['supports'][0]['samples']


def test_import_quantization_is_measured_without_weight_renormalization(study):
    c,ref,rows,data,poses=setup(study)
    data['surfaces'][0]['weights'][0]-=1e-5
    check,_,_=audit.check_skin(c,data,poses,ref[0],ref[1],rows)
    assert check['skin_data_check']['passed']
    assert abs(check['skin_data_check']['maximum_weight_sum_error']-1e-5)<1e-14
    assert check['maximum_vertex_distance_m']>1e-6


@pytest.mark.parametrize('fault',['bind','weight','case','surface','clock','bone_clock'])
def test_misbound_or_invalid_imported_support_rejected(study,fault):
    c,ref,rows,data,poses=setup(study)
    if fault=='bind':data['surfaces'][0]['binds'][0]['pose'][3][0]+=.05
    if fault=='weight':data['surfaces'][0]['weights'][0]-=.01
    if fault=='case':data['id']='other'
    if fault=='surface':data['surfaces'].append(data['surfaces'][0])
    if fault=='clock':c['sample_times_s'].pop()
    if fault=='bone_clock':poses['frames'][-1]['actual_time_s']-=.001
    with pytest.raises(ValueError):audit.check_skin(c,data,poses,ref[0],ref[1],rows)


def test_source_penetration_survives_a_passing_imported_data_check(study):
    folder,out=study;q,r,_=engine_audit.bind_study(folder);cases,refs,rows=engine_audit.prepare_cases(folder,q,r,out)
    c,ref=cases[0],refs[0]
    check,_,_=audit.check_skin(c,surface(c,ref[0]),observations(c,ref),ref[0],ref[1],rows)
    assert check['skin_data_check']['passed'] and not check['imported_skin_support_pass']
    assert check['supports'][0]['minimum_height_m']<0


def test_skin_runner_uses_bound_bone_evidence_and_retains_resources(study,monkeypatch):
    from types import SimpleNamespace
    folder,out=study;monkeypatch.setattr(audit,'ROOT',folder.parent.parent)
    q,r,_=engine_audit.bind_study(folder);cases,refs,rows=engine_audit.prepare_cases(folder,q,r,out)
    engine=folder.parent/'fixture-engine';engine.write_bytes(b'fixture; not Godot')
    def fake_pose(argv,**kw):
        request=read(argv[-2])
        for c in request['cases']:Path(c['native_animation_output']).write_bytes(b'fixture resource')
        save(argv[-1],dict(engine=dict(test_fixture=True),cases=[observations(c,r) for c,r in zip(cases,refs)]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(engine_audit.subprocess,'run',fake_pose)
    assert engine_audit.run(folder,out,engine=engine)
    target=folder.parent/'skin'
    frozen={str(p):sha256(p) for p in out.rglob('*') if p.is_file()}
    def fake_skin(argv,**kw):
        save(argv[-1],dict(engine=dict(test_fixture=True),cases=[surface(c,r[0]) for c,r in zip(cases,refs)]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(audit.subprocess,'run',fake_skin)
    assert audit.run(out,target,engine=engine)
    v=read(target/'verification.json');result=read(target/'result.json');request=read(target/'request.json')
    assert len(v['checks'])==5 and v['imported_data_pass'] and not v['gpu_render_verified'] and not v['quality_approved']
    assert not v['checks'][0]['imported_skin_support_pass']
    for p,h in request['inputs'].items():assert sha256(p)==h
    for p,h in result['outputs'].items():assert sha256(target/p)==h
    assert all(sha256(p)==h for p,h in frozen.items())
