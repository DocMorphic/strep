"""Strict source peaks must tighten objectives and independently gate output."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_peak_limits import limits, STRICT_PEAK_TOLERANCE
from absolute_rate_peaks import compare


def groups():
    return tuple(np.array([[1., 4., 0.], [3., 2., 0.], [2., 1., 0.]])*s for s in (1., 2., 3., 4.))


def test_intersection_keeps_local_caps_and_stricter_global_peaks():
    source=groups(); cap=tuple(np.array([[1., 4., 0.], [3., 4., 0.], [3., 1., 0.]])*s for s in (1., 2., 3., 4.))
    frozen=[a.copy() for a in cap]; caps=SimpleNamespace(caps=cap,tolerance=1e-5)
    result=limits(source,caps)
    for s,c,before,limit in zip(source,cap,frozen,result):
        np.testing.assert_array_equal(c,before)
        assert np.all(limit<=c+caps.tolerance)
        np.testing.assert_array_equal(limit[0,0],c[0,0]+1e-5)
        np.testing.assert_array_equal(limit[1,0],s[:,0].max()+1e-7)
        np.testing.assert_array_equal(limit[:,2],np.full(3,1e-7))
    assert STRICT_PEAK_TOLERANCE==compare(source,source)['tolerance']==1e-7


def test_bin_only_pass_cannot_hide_peak_regressions_in_signed_objective(monkeypatch):
    import native_support_feasibility as repair
    source=groups(); cap=tuple(np.broadcast_to(s.max(axis=0),s.shape).copy() for s in source)
    caps=SimpleNamespace(caps=cap,tolerance=1e-5,dt=1/120)
    actual=tuple(s.copy() for s in source)
    for a in actual:a[1,0]+=5e-6
    assert all(np.max(a-c)<=caps.tolerance for a,c in zip(actual,cap))
    assert not compare(source,actual)['absolute_peak_guard_pass']
    p=SimpleNamespace(caps=caps,rate_ids=np.array([0]),columns=np.array([0,2]),rig=SimpleNamespace(joints=[]),data=[])
    monkeypatch.setattr(repair,'features',lambda w,j:w)
    monkeypatch.setattr(repair,'measures',lambda f,dt:actual)
    old=repair.signed_constraints(p,{},np.zeros((1,)))
    assert old.max()<=0
    p.strict_rate_limits=limits(source,caps)
    strict=repair.signed_constraints(p,{},np.zeros((1,)))
    assert strict.shape==old.shape and np.all(strict>=old-1e-14)
    assert np.count_nonzero(strict>0)==4
    # Same source peak test, evaluated independently across every joint/time.
    for a,bound in zip(actual,p.strict_rate_limits):
        assert (a>bound).any()


@pytest.mark.parametrize('fault',['shape','negative','nan','count','tolerance'])
def test_invalid_peak_inputs_rejected(fault):
    source=list(groups()); cap=list(groups()); tolerance=1e-5
    if fault=='shape':cap[0]=cap[0][:-1]
    if fault=='negative':source[0][0,0]=-1
    if fault=='nan':cap[0][0,0]=np.nan
    if fault=='count':cap.pop()
    if fault=='tolerance':tolerance=-1
    with pytest.raises(ValueError):limits(source,SimpleNamespace(caps=cap,tolerance=tolerance))


@pytest.mark.parametrize('mode',[True,1,'yes',None])
def test_strict_mode_requires_explicit_warm_job(mode):
    from native_support_job import run
    with pytest.raises(ValueError,match='[Rr]epair'):run(None,None,None,repair_strict_peaks=mode)


def test_real_strict_repair_binds_peak_method_and_replays_original_controls(tmp_path,monkeypatch):
    from test_native_support import fixture
    from strep import read,save,sha256
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec=fixture(tmp_path,plane=.2);draft=tmp_path/'draft.json';save(draft,spec)
    flags=dict(joint_rates=True,joint_swivel=True,joint_foot_orientation=True)
    warm=tmp_path/'reports'/'warm';first=job.run(source,draft,warm,**flags,joint_evaluations=1)
    frozen={str(p):sha256(p) for p in warm.rglob('*') if p.is_file()}
    out=tmp_path/'reports'/'strict'
    result=job.run(source,draft,out,**flags,repair_from=warm,repair_quantized=True,
                   repair_strict_peaks=True,repair_iterations=1,repair_trust=2e-7)
    request=read(out/'request.json')
    assert request['repair_strict_peaks'] and request['absolute_peak_tolerance']==1e-7
    assert request['rate_tolerance']==1e-5 and request['spec']==spec
    assert sha256(out/'implementation/native_support_peak_limits.py')==request['implementation']['native_support_peak_limits.py']
    assert result['retained_input'] and result['status']=='complete' and not result['quality_approved']
    for t in result['trials']:
        assert t['status']=='complete';p=t['proposal'][0]
        assert p['strict_peak_limits'] and p['absolute_peak_tolerance']==1e-7
        assert p['probes'][0]['sha256']==first['trials'][t['trial']]['sha256']
        expected=t['source_rates_pass'] and t['support_samples_pass'] and t['absolute_peak_comparison']['absolute_peak_guard_pass']
        assert t['selection_gates_pass']==expected
        assert p['final_merit'][0]<=p['initial_merit'][0]
        old=read(warm/f"trial-{t['trial']}.controls.json");new=read(out/p['controls_file'])
        for key in ('lower','upper','intervals'):assert old[key]==new[key]
        for probe in p['probes']:assert sha256(out/probe['file'])==probe['sha256']
    assert all(sha256(path)==digest for path,digest in frozen.items())


def test_final_gate_is_independent_of_optimizer_and_optional_for_legacy_jobs(tmp_path,monkeypatch):
    from test_native_support import fixture
    from strep import save
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec=fixture(tmp_path,plane=.2);draft=tmp_path/'draft.json';save(draft,spec)
    # Isolate final decision routing: remove the bin gate in this synthetic test
    # and force the independent peak checker to reject, irrespective of solver.
    original=job.SampledMotionCaps
    def loose_bin_caps(*a,**kw):
        caps=original(*a,**kw);caps.caps=tuple(np.full_like(c,1e9) for c in caps.caps);return caps
    monkeypatch.setattr(job,'SampledMotionCaps',loose_bin_caps)
    monkeypatch.setattr(job,'compare',lambda *a,**kw:dict(absolute_peak_guard_pass=False,tolerance=1e-7))
    flags=dict(joint_rates=True,joint_swivel=True,joint_foot_orientation=True)
    warm=tmp_path/'reports'/'warm';legacy=job.run(source,draft,warm,**flags,joint_evaluations=1)
    assert legacy['selected_trial']==0 and not legacy['input_already_satisfied']
    strict=job.run(source,draft,tmp_path/'reports'/'strict',**flags,repair_from=warm,
                   repair_strict_peaks=True,repair_iterations=1,repair_trust=2e-7)
    assert all(t['support_samples_pass'] and t['source_rates_pass'] for t in strict['trials'])
    assert all(not t['selection_gates_pass'] for t in strict['trials'])
    assert strict['retained_input'] and strict['selected_trial'] is None
