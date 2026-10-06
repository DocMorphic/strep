"""Complete decoded native restoration, preserved caps and rejected false evidence."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_scene_key_restore as restoration
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_scene_contacts import SceneContacts
from strep import read,save,sha256
from test_native_partner_surface_rows import scene_fixture


def fixture(tmp_path):
    scene,_,_=scene_fixture(tmp_path)
    path=tmp_path/'contacts.json';spec=read(path);row=spec['contacts'][0]
    row.update(mode='touch',interval_s=[0.,0.])
    row['limits']={'position_m':row['limits']['position_m']}
    row['target']=dict(space='world',points_m=scene.actor_points('A',scene.rows[0]['ids'],np.array([0.]))[0].tolist())
    save(path,spec);digest=sha256(path);scene=SceneContacts(spec,tmp_path)
    permission=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,
        actors={'A':dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
            tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.000001)})
    problem=SceneProblem(scene,SceneEdits(permission,scene,digest));seen=[]
    def decode(value,label):
        folder=tmp_path/label;folder.mkdir();files={}
        for name in problem.edits.actors:
            path=folder/(name+'.glb');problem.edits.export(name,value,path)
            assert problem.edits.audit(name,path,scene.actors[name]['animation_index'])['passed'];files[name]=path
        residual,worlds=problem.decoded(files,value);seen.append((label,residual.copy()))
        return residual,worlds
    return problem,decode,seen


def test_real_failed_translation_is_restored_through_exported_complete_assets(tmp_path):
    problem,decode,seen=fixture(tmp_path);start=np.array([.003,0.,0.]);frozen={n:[a.copy() for a in c.caps] for n,c in problem.caps.items()}
    value,report=restoration.restore(problem,start,decode,trust=.02)
    assert seen[0][1].max()>0 and report['native_conditions_pass']
    assert np.all(seen[-1][1]<=0) and not np.array_equal(start,value)
    assert all(step['all_native_norms_hard'] for step in report['history'])
    for n,c in problem.caps.items():
        for a,b in zip(c.caps,frozen[n]):np.testing.assert_array_equal(a,b)
    assert not report['geometry_assessed'] and not report['quality_approved'] and not report['release_approved']


def test_already_passing_start_has_no_solver_or_difference_work(tmp_path,monkeypatch):
    problem,decode,seen=fixture(tmp_path)
    monkeypatch.setattr(restoration,'linearize',lambda *a,**kw:pytest.fail('unnecessary difference work'))
    value,report=restoration.restore(problem,problem.initial,decode)
    assert report['native_conditions_pass'] and report['history']==[] and len(seen)==1
    np.testing.assert_array_equal(value,problem.initial)


@pytest.mark.parametrize('fault',['missing-actor','missing-time','nonfinite','false-residual','changed-cap'])
def test_complete_native_evidence_and_original_limits_cannot_be_replaced(tmp_path,fault):
    problem,decode,_=fixture(tmp_path)
    def corrupt(value,label):
        residual,worlds=decode(value,label)
        if fault=='missing-actor':worlds.pop('B')
        elif fault=='missing-time':worlds['A']=worlds['A'][:-1]
        elif fault=='nonfinite':worlds['A'][0,0,0,0]=np.nan
        elif fault=='false-residual':residual=np.zeros_like(residual)
        else:
            problem.caps['A'].caps[0]+=1.
            residual=problem.constraints(value,worlds)
        return residual,worlds
    with pytest.raises(ValueError):restoration.restore(problem,np.array([.003,0,0]),corrupt)


def test_no_direction_preserves_rejected_anchor_and_reports_failure(tmp_path,monkeypatch):
    problem,decode,_=fixture(tmp_path);start=np.array([.003,0,0])
    monkeypatch.setattr(restoration,'direction',lambda *a,**kw:(None,dict(status='PrimalInfeasible')))
    value,report=restoration.restore(problem,start,decode)
    np.testing.assert_array_equal(value,start)
    assert not report['native_conditions_pass'] and report['history'][0]['probes']==[]


def test_outside_original_boxes_rejects_before_decoding(tmp_path):
    problem,_,_=fixture(tmp_path)
    with pytest.raises(ValueError,match='control boxes'):
        restoration.restore(problem,[1.001,0,0],lambda *a:pytest.fail('decode outside boxes'))


@pytest.mark.parametrize('settings',[dict(steps=True),dict(steps=0),dict(steps=5),dict(trust=True),dict(trust=0),dict(trust=.021),dict(difference_step=True),dict(difference_step=0),dict(difference_step=float('nan'))])
def test_invalid_settings_reject_before_decoded_or_model_queries(settings):
    with pytest.raises(ValueError):restoration.restore(None,None,lambda *a:None,**settings)
