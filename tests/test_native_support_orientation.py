"""Independent native foot-world orientation checks and serialized proxy checks."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_support_swivel import problem as swivel_problem
from native_support_orientation import SupportOrientationProblem
from native_leg_floor import export_rotations
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import read,sha256


def problem(tmp_path,disjoint=False):
    base=swivel_problem(tmp_path,disjoint)
    return SupportOrientationProblem(base.rig,base.reader,base.rows)


def test_zero_orientation_preserves_swivel_only_proposal_exactly(tmp_path):
    base=swivel_problem(tmp_path);p=SupportOrientationProblem(base.rig,base.reader,base.rows)
    x=p.initial.copy();z=base.initial.copy()
    for d,e in zip(p.data,base.data):
        x[d['swivel_ids']]=.015;z[e['swivel_ids']]=.015
    actual,aa=p.rotations(x);expected,ea=base.rotations(z)
    for node in actual:np.testing.assert_array_equal(actual[node],expected[node])
    np.testing.assert_array_equal(aa,ea)


@pytest.mark.parametrize('vector',[[.002,0,0],[0,-.003,0],[0,0,.004],[.002,-.003,.004]])
def test_world_orientation_changes_without_moving_native_ankle(tmp_path,vector):
    p=problem(tmp_path);x=p.initial.copy();zero,za=p.rotations(x);before=p.world(zero)
    for d in p.data:
        x[d['swivel_ids']]=.01
    fixed,_=p.rotations(x);fixed_world=p.world(fixed)
    for d in p.data:x[d['orientation_ids']]=vector
    values,angles=p.rotations(x);world=p.world(values)
    for d in p.data:
        foot=d['row']['chain'][-1];ids=np.searchsorted(p.times,d['clock']);middle=ids[d['orientation_keys']]
        delta=Rotation.from_rotvec(vector).as_matrix()
        np.testing.assert_allclose(world[middle,foot,:3,:3],delta@d['worlds'][d['orientation_keys'],foot,:3,:3],atol=1e-14,rtol=0)
        np.testing.assert_array_equal(world[ids,foot,:3,3],fixed_world[ids,foot,:3,3])
        for node in d['row']['chain'][:-1]:np.testing.assert_array_equal(values[node],fixed[node])
        for node in d['row']['chain']:
            a,b=d['row']['edit_keys'];np.testing.assert_array_equal(values[node][[a,b]],p.channels[node][2][[a,b]])
    np.testing.assert_array_equal(world[:,[0,5,6]],p.raw[:,[0,5,6]])
    free=(p.times<=p.rows[0]['edit_s'][0])|(p.times>=p.rows[0]['edit_s'][1])
    np.testing.assert_array_equal(world[free],p.raw[free])
    path=tmp_path/'oriented.glb';export_rotations(p.rig.document,p.rig.binary,values,path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    quantized=p.world({n:q.astype(np.float32).astype(float) for n,q in values.items()})
    np.testing.assert_allclose(quantized,np.array([reader.sample(float(t)) for t in p.times]),atol=2e-14,rtol=0)


@pytest.mark.parametrize('disjoint',[False,True])
def test_orientation_sparse_graph_covers_every_changed_row(tmp_path,disjoint):
    p=problem(tmp_path,disjoint);x=p.initial.copy()
    for d in p.data:x[d['orientation_ids']]=[.001,-.002,.003]
    pattern=p.sparsity().toarray()
    for col in range(len(x)):
        h=min(1e-5,(p.upper[col]-p.lower[col])/4);z=x.copy();z[col]=np.clip(z[col],p.lower[col]+h/2,p.upper[col]-h/2)
        a=z.copy();b=z.copy();a[col]+=h/2;b[col]-=h/2
        changed=np.abs(p.residual(a)-p.residual(b));assert changed[pattern[:,col]==0].max(initial=0)<1e-9


def test_component_boxes_bound_world_orientation_norm(tmp_path):
    p=problem(tmp_path)
    for d in p.data:
        np.testing.assert_allclose(np.linalg.norm(p.upper[d['orientation_ids']],axis=1),np.deg2rad(1.),atol=1e-16,rtol=0)


@pytest.mark.parametrize('limit',[0,1.01,True,float('nan')])
def test_invalid_orientation_limit_rejected_before_rig_load(limit):
    with pytest.raises(ValueError):SupportOrientationProblem(None,None,None,orientation_limit_degrees=limit)


def test_saved_controls_reproduce_exact_serialized_proposal(tmp_path):
    from native_support_orientation import propose
    p=problem(tmp_path);path=tmp_path/'fit.glb'
    result=propose(p.rig,p.reader,p.rows,path,maximum_evaluations=1)[0]
    controls=read(tmp_path/result['controls_file'])
    assert sha256(tmp_path/result['controls_file'])==result['controls_sha256']
    assert controls['proposal_sha256']==sha256(path)
    values,_=p.rotations(controls['parameters']);replay=tmp_path/'replay.glb'
    export_rotations(p.rig.document,p.rig.binary,values,replay)
    assert replay.read_bytes()==path.read_bytes()
    assert not result['success'] and result['evaluations']==1
    assert controls['intervals'][0]['clock_s']==p.data[0]['clock'].tolist()
    with pytest.raises(ValueError,match='fresh'):propose(p.rig,p.reader,p.rows,path,maximum_evaluations=1)


@pytest.mark.parametrize('budget',[0,2001,True,1.5])
def test_invalid_search_budget_rejected_before_rig_load(budget):
    from native_support_orientation import propose
    with pytest.raises(ValueError,match='evaluations'):propose(None,None,None,None,maximum_evaluations=budget)


@pytest.mark.parametrize('rates,swivel,orientation',[(False,False,True),(True,False,True),(False,False,'yes'),(True,True,1)])
def test_job_rejects_ambiguous_orientation_modes_before_input_load(rates,swivel,orientation):
    from native_support_job import run
    with pytest.raises(ValueError,match='orientation'):
        run(None,None,None,joint_rates=rates,joint_swivel=swivel,joint_foot_orientation=orientation)


def test_job_archives_orientation_method_and_preserves_failed_controls(tmp_path,monkeypatch):
    from test_native_support import fixture
    from native_support_job import run
    from strep import save
    source,rig,reader,spec=fixture(tmp_path,plane=.2);draft=tmp_path/'draft.json';save(draft,spec)
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path)
    (tmp_path/'reports').mkdir();folder=tmp_path/'reports'/'fit-job'
    result=run(source,draft,folder,joint_rates=True,joint_swivel=True,joint_foot_orientation=True,joint_evaluations=1)
    request=read(folder/'request.json')
    assert request['proposal_method']=='joint_support_source_rate_orientation_search'
    assert request['joint_foot_orientation_limit_degrees']==1.
    assert sha256(folder/'implementation/native_support_orientation.py')==request['implementation']['native_support_orientation.py']
    assert result['status']=='complete' and result['retained_input'] and not result['quality_approved']
    assert (folder/'candidate.glb').read_bytes()==source.read_bytes()
    assert len(result['trials'])==4
    for trial in result['trials']:
        assert trial['status']=='complete' and not trial['source_rates_pass']
        proposal=trial['proposal'][0];name=proposal['controls_file']
        assert name in result['outputs'] and sha256(folder/name)==proposal['controls_sha256']
        assert proposal['maximum_native_orientation_edit_degrees']<=1.
