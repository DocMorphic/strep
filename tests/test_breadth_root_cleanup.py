import copy
import shutil
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from study_breadth_root_cleanup import active_frames,BreadthProblem,support_audit
from authored_root_correction import POLICY,export


def test_support_union_preserves_boundaries():
    annotations=dict(intervals=[dict(joint='LeftFoot',start_frame=0,end_frame_exclusive=3),dict(joint='LeftToeBase',start_frame=2,end_frame_exclusive=5),dict(joint='RightFoot',start_frame=5,end_frame_exclusive=7)])
    assert active_frames(annotations,'Left',7).tolist()==[True]*5+[False]*2
    annotations['intervals'][0]['end_frame_exclusive']=8
    with pytest.raises(ValueError,match='interval'):active_frames(annotations,'Left',7)


@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    origin=ROOT/'reports/whole-support-breadth-v1/takes/motion-026-rig-03'
    if not origin.exists():pytest.skip('Provisioned breadth fixture required')
    folder=tmp_path_factory.mktemp('breadth-root')
    for variant in ['input','candidate']:
        (folder/variant).mkdir();shutil.copyfile(origin/variant/'character.glb',folder/variant/'character.glb')
    shutil.copyfile(origin/'spec.json',folder/'contact-spec.json');shutil.copyfile(origin/'input/contacts.json',folder/'contacts.json')
    spec=read(origin/'spec.json');save(folder/'result.json',{k:spec[k] for k in ['frames','fps','root_node']})
    save(folder/'support.json',read(origin/'request.json')['support'])
    case=dict(source='input',candidate='candidate',files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()})
    return BreadthProblem(folder,case,copy.deepcopy(POLICY))


def test_initial_constraints_and_map_match_decoded_foot(problem):
    linear=[];norms=[]
    counts=problem.additional_constraints(lambda m,b:linear.append((m,b)),lambda v,m,c:norms.append((v,m,c)),lambda *_:None)
    assert set(counts)=={'Left','Right'} and all(c['hover']>0 and c['edges']>0 and c['anchors']>0 for c in counts.values())
    assert min(float(b) for m,b in linear)>=-1e-12
    assert max(np.linalg.norm(v)-cap for v,m,cap in norms)<=1e-12
    delta=np.zeros((problem.frames,3));delta[20]=[.0001,-.0002,.0003]
    path=problem.folder/'map-check.glb';export(problem.rig,problem.root,delta,path)
    from verify_authored_root_correction import samples
    rig,world=samples(path,problem.frames)
    for side,patch in problem.spec['patches'].items():
        actual=rig.vertices(world[40])[patch['vertices']].mean(0)-problem.points[40,patch['vertices']].mean(0)
        expected=np.asarray(problem.maps[40]@delta.ravel()).ravel()*problem.weights[patch['vertices']].mean()
        np.testing.assert_allclose(actual,expected,atol=6e-8,rtol=0)


def test_separate_support_audit_detects_hover_and_drift_mutants(problem):
    unchanged=support_audit(problem.folder,problem.source)
    assert unchanged['passed']
    for label,axis in [('hover',1),('drift',0)]:
        desired=np.zeros(3);desired[axis]=.01
        offsets=np.zeros((problem.frames,3));offsets[20]=np.linalg.solve(problem.maps[40][:,60:63].toarray(),desired)
        path=problem.folder/(label+'.glb');export(problem.rig,problem.root,offsets,path)
        result=support_audit(problem.folder,path)
        assert not result['passed']
        if axis==1:assert max(r['hover_excess_m'] for r in result['rows'])>.009
        else:assert max(r['speed_excess_m_s'] for r in result['rows'])>.2
