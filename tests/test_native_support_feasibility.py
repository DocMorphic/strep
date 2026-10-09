"""Independent linear constraints, structural differences and exported repair."""
from pathlib import Path
import sys
import os
import subprocess
import numpy as np
import pytest
from scipy.sparse import csr_matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_support_feasibility as repair
from test_native_support_orientation import problem
from native_leg_floor import export_rotations
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import read,save,sha256


@pytest.mark.parametrize('initial_threads',[None,2])
def test_repair_after_another_highs_scheduler_has_started(initial_threads):
    """The public repair must work after a default or explicitly sized solve."""
    root=Path(__file__).resolve().parents[1]
    code='''
import sys,warnings
from scipy.optimize import linprog,OptimizeWarning
options={} if sys.argv[1]=='None' else {'threads':int(sys.argv[1])}
with warnings.catch_warnings():
    warnings.simplefilter('ignore',OptimizeWarning)
    warm=linprog([1.],bounds=[(0.,1.)],method='highs',options=options)
assert warm.success,warm.message
import pytest
names=['test_linear_direction_finds_smallest_feasible_step_inside_box',
       'test_conflicting_linear_constraints_keep_positive_slack',
       'test_restore_uses_serialized_samples_and_retains_each_probe',
       'test_serialized_plateau_retains_original_controls']
raise SystemExit(pytest.main(['-q',*[sys.argv[2]+'::'+name for name in names]]))
'''
    env=os.environ.copy();env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    result=subprocess.run([sys.executable,'-c',code,str(initial_threads),str(Path(__file__).resolve())],
        cwd=root,env=env,capture_output=True,text=True,timeout=60,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.stdout+result.stderr


def test_signed_constraints_keep_exact_parent_positive_residual(tmp_path):
    p=problem(tmp_path);x=p.initial.copy()
    for d in p.data:x[d['orientation_ids']]=[.001,-.002,.003]
    values,_=p.rotations(x);g=repair.signed_constraints(p,values,p.world(values))
    np.testing.assert_allclose(np.maximum(0,g),p.residual(x),atol=1e-14,rtol=0)
    assert (g<0).any() and np.isfinite(g).all()


@pytest.mark.parametrize('disjoint',[False,True])
def test_colored_native_differences_equal_individual_differences(tmp_path,disjoint):
    p=problem(tmp_path,disjoint);x=p.initial.copy();pattern=p.sparsity()
    for d in p.data:x[d['orientation_ids']]=[.001,-.002,.003]
    def function(z):
        values,_=p.rotations(z);return repair.signed_constraints(p,values,p.world(values))
    groups=repair.colors(pattern)
    for group in groups:assert np.asarray(pattern[:,group].sum(axis=1)).max()<=1
    jac=repair.colored_jacobian(function,x,p.lower,p.upper,pattern,groups).toarray();base=function(x)
    for col in range(len(x)):
        h=min(1e-5,(p.upper[col]-p.lower[col])/4)
        if p.upper[col]-x[col]<x[col]-p.lower[col]:h=-h
        z=x.copy();z[col]+=h
        np.testing.assert_allclose(jac[:,col],(function(z)-base)/h,atol=1e-8,rtol=0)


def test_signed_serialized_constraints_match_independent_decoder(tmp_path):
    p=problem(tmp_path);values,_=p.rotations(p.initial);path=tmp_path/'candidate.glb'
    export_rotations(p.rig.document,p.rig.binary,values,path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    from paired_temporal_neighbor import rotation_channels
    q={n:c[2] for n,c in rotation_channels(rig.document,rig.binary).items() if n in p.nodes}
    actual=np.array([reader.sample(float(t)) for t in p.times])
    promoted={n:v.astype(float) for n,v in q.items()}
    np.testing.assert_allclose(repair.signed_constraints(p,q,actual),repair.signed_constraints(p,promoted,p.world(promoted)),atol=1e-8,rtol=0)


def test_linear_direction_finds_smallest_feasible_step_inside_box():
    x=np.array([.4]);g=np.array([.6,-.9]);j=csr_matrix([[1.],[-1.]])
    delta,record=repair.direction(x,g,j,[-1.],[1.],trust=.7)
    assert record['success'] and record['l1_phase_success']
    assert np.max(g+j@delta)<2e-9
    np.testing.assert_allclose(delta,[-.6],atol=2e-9,rtol=0)
    assert -1<=x[0]+delta[0]<=1


def test_conflicting_linear_constraints_keep_positive_slack():
    delta,record=repair.direction([.4],[.6,-.2],csr_matrix([[1.],[-1.]]),[-1.],[1.],trust=.7)
    assert record['success'] and abs(record['linearized_worst_excess']-.2)<1e-8
    assert record['predicted_worst_excess']>0


class ScalarProblem:
    lower=np.array([-.001]);upper=np.array([.001])
    def rotations(self,x):
        assert x.shape==(1,) and np.all(x>=self.lower) and np.all(x<=self.upper)
        return x.copy(),[]
    def world(self,x):return x
    def sparsity(self):return csr_matrix([[1.],[1.]])


def test_restore_uses_serialized_samples_and_retains_each_probe(monkeypatch):
    p=ScalarProblem();calls=[]
    constraints=lambda x:np.array([x[0]/.001-.2,-x[0]/.001-.1])
    monkeypatch.setattr(repair,'signed_constraints',lambda p,v,w:constraints(v))
    def evaluate(x,label):
        calls.append((label,x.copy()));return constraints(x.astype(np.float32).astype(float))
    x,report=repair.restore(p,[.0005],evaluate,iterations=8)
    assert report['sampled_proxy_feasible'] and report['reason']=='sampled_constraints_satisfied'
    assert len(calls)==1+sum(len(row['probes']) for row in report['history'])
    assert all(row['after_merit'][0]<row['before_merit'][0] for row in report['history'])
    assert np.max(evaluate(x,'check'))<=0


def test_serialized_plateau_retains_original_controls(monkeypatch):
    p=ScalarProblem();calls=[]
    monkeypatch.setattr(repair,'signed_constraints',lambda p,v,w:np.array([v[0]/.001-.2,-v[0]/.001-.1]))
    def evaluate(x,label):calls.append(label);return np.array([1.,-1.])
    x,report=repair.restore(p,[.0005],evaluate,iterations=8)
    np.testing.assert_array_equal(x,[.0005])
    assert not report['sampled_proxy_feasible'] and report['reason']=='serialized_line_search_stalled'
    assert all(row['selected_fraction'] is None for row in report['history'])
    assert len(calls)==1+10*len(report['history'])


@pytest.mark.parametrize('iterations,trust',[(0,.0002),(33,.0002),(True,.0002),(8,0),(8,.00101),(8,True)])
def test_invalid_restore_budget_rejected_before_evaluation(iterations,trust):
    with pytest.raises(ValueError):repair.restore(None,None,None,iterations=iterations,trust=trust)


@pytest.mark.parametrize('kwargs',[dict(repair_from='missing'),dict(repair_iterations=1),dict(repair_trust=.0001),dict(repair_iterations=0)])
def test_job_rejects_ambiguous_repair_modes_before_reading_inputs(kwargs):
    from native_support_job import run
    with pytest.raises(ValueError,match='[Rr]epair'):run(None,None,None,**kwargs)


def test_real_job_warms_exact_controls_and_preserves_archived_inputs(tmp_path,monkeypatch):
    from test_native_support import fixture
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec=fixture(tmp_path,plane=.2);draft=tmp_path/'draft.json';save(draft,spec)
    warm=tmp_path/'reports'/'warm';flags=dict(joint_rates=True,joint_swivel=True,joint_foot_orientation=True)
    first=job.run(source,draft,warm,**flags,joint_evaluations=1)
    frozen={str(p):sha256(p) for p in warm.rglob('*') if p.is_file()}
    output=tmp_path/'reports'/'repair'
    result=job.run(source,draft,output,**flags,repair_from=warm,repair_iterations=1)
    assert result['status']=='complete' and result['retained_input'] and not result['quality_approved']
    request=read(output/'request.json')
    assert request['proposal_method']=='serialized_native_support_feasibility_repair'
    assert request['joint_search_maximum_evaluations'] is None and request['repair_iterations']==1
    assert sha256(warm/'result.json')==request['inputs'][str(warm/'result.json')]
    for t in result['trials']:
        assert t['status']=='complete';p=t['proposal'][0]
        assert p['final_merit'][0]<=p['initial_merit'][0]
        assert p['probes'][0]['sha256']==first['trials'][t['trial']]['sha256']
        assert all(sha256(output/probe['file'])==probe['sha256'] for probe in p['probes'])
        assert sha256(output/p['controls_file'])==p['controls_sha256']
    assert all(sha256(p)==h for p,h in frozen.items())
    # A completed repair can be chained without dropping ancestor/probe hashes.
    chained=tmp_path/'reports'/'quantized'
    chain=job.run(source,draft,chained,**flags,repair_from=output,repair_iterations=1,
                  repair_trust=2e-7,repair_quantized=True)
    bound=read(chained/'request.json')
    assert bound['repair_quantized_differences'] is True and bound['rate_tolerance']==request['rate_tolerance']
    assert bound['spec']==request['spec']
    assert set(request['inputs']).issubset(bound['inputs'])
    assert str(output/'pipeline.json') in bound['inputs']
    assert sha256(output/'result.json')==bound['inputs'][str(output/'result.json')]
    for t in chain['trials']:
        assert t['status']=='complete'
        q=t['proposal'][0];parent=result['trials'][t['trial']]['proposal'][0]
        assert q['difference_model']=='float32_keys_float64_interpolation'
        assert q['difference_step_radians']==1e-7 and q['minimum_trust_radians']==1e-9
        assert q['probes'][0]['sha256']==result['trials'][t['trial']]['sha256']
        assert q['final_merit'][0]<=q['initial_merit'][0]
        for probe in parent['probes']:assert str(output/probe['file']) in bound['inputs']
    # Conflicting output/proposal bindings cannot silently override each other.
    old_result=read(output/'result.json');bad=read(output/'result.json')
    bad['trials'][0]['proposal'][0]['controls_sha256']='0'*64;save(output/'result.json',bad)
    rejected=tmp_path/'reports'/'conflict'
    with pytest.raises(ValueError,match='Conflicting'):job.run(source,draft,rejected,**flags,repair_from=output)
    assert not rejected.exists();save(output/'result.json',old_result)
    # Any ancestor probe mutation blocks another warm job before creation.
    probe=output/result['trials'][0]['proposal'][0]['probes'][0]['file']
    original=probe.read_bytes();probe.write_bytes(original+b'changed')
    rejected=tmp_path/'reports'/'ancestor-change'
    with pytest.raises(ValueError,match='hash'):job.run(source,draft,rejected,**flags,repair_from=chained)
    assert not rejected.exists();probe.write_bytes(original)
    # Mutating the old control payload is rejected before a new study exists.
    control=warm/'trial-0.controls.json';control.write_bytes(control.read_bytes()+b'\n')
    rejected=tmp_path/'reports'/'rejected'
    with pytest.raises(ValueError,match='hash'):job.run(source,draft,rejected,**flags,repair_from=warm,repair_iterations=1)
    assert not rejected.exists()


@pytest.mark.parametrize('disjoint',[False,True])
def test_quantized_difference_probes_equal_separate_exports(tmp_path,disjoint):
    p=problem(tmp_path,disjoint);x=p.initial.copy()
    for d in p.data:x[d['orientation_ids']]=[.001,-.002,.003]
    def decoded(z,label):
        from paired_temporal_neighbor import rotation_channels
        values,_=p.rotations(z);path=tmp_path/f'{label}.glb'
        export_rotations(p.rig.document,p.rig.binary,values,path)
        rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,0)
        world=np.array([sampler.sample(float(t)) for t in p.times])
        q={n:c[2] for n,c in rotation_channels(rig.document,rig.binary).items() if n in p.nodes}
        for n in p.nodes:np.testing.assert_array_equal(q[n],values[n].astype(np.float32))
        stored={n:v.astype(float) for n,v in q.items()}
        np.testing.assert_allclose(p.world(stored),world,atol=2e-14,rtol=0)
        actual=repair.signed_constraints(p,q,world)
        proxy=repair.constraint_model(p,z,quantized=True)
        # Floating matrix arithmetic is amplified by second time differences.
        # This is a cross-platform model/decoder diagnostic, not clip acceptance.
        roundoff=64*np.finfo(float).eps/p.caps.dt**2
        np.testing.assert_allclose(proxy,actual,atol=roundoff,rtol=0)
        return actual,proxy
    base,base_proxy=decoded(x,'base');model=lambda z:repair.constraint_model(p,z,quantized=True)
    jac=repair.colored_jacobian(model,x,p.lower,p.upper,p.sparsity(),step=1e-7).toarray()
    for col in range(len(x)):
        h=min(1e-7,(p.upper[col]-p.lower[col])/4)
        if p.upper[col]-x[col]<x[col]-p.lower[col]:h=-h
        z=x.copy();z[col]+=h
        actual,proxy=decoded(z,str(col))
        # The structural coloring must match separate rounded-model probes.
        np.testing.assert_allclose(jac[:,col],(proxy-base_proxy)/h,atol=1e-8,rtol=0)
        # Independently exported differences may differ by measured roundoff
        # in both endpoint vectors, divided by the absolute difference step.
        propagated=(np.abs(actual-proxy)+np.abs(base-base_proxy))/abs(h)
        error=np.abs(jac[:,col]-(actual-base)/h)
        assert np.all(error<=propagated+1e-8)


@pytest.mark.parametrize('mode',[True,1,'yes',None])
def test_quantized_mode_needs_explicit_warm_job(mode):
    from native_support_job import run
    with pytest.raises(ValueError,match='[Rr]epair'):
        run(None,None,None,repair_quantized=mode)


@pytest.mark.parametrize('mode',[1,'yes',None])
def test_restore_quantization_flag_rejected_before_evaluation(mode):
    with pytest.raises(ValueError,match='quantized'):
        repair.restore(None,None,None,quantized=mode)
