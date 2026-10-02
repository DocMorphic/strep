"""Coordinate search must obey boxes and decoded gates, including warm chains."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.sparse import csr_matrix
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_support_coordinates as coordinate


class BoxProblem:
    lower = np.array([0., 0., 0.])
    upper = np.array([.001, .001, .001])
    def rotations(self, x):
        assert x.shape == self.lower.shape
        assert np.all(x >= self.lower) and np.all(x <= self.upper)
        return x.copy(), []
    def sparsity(self):
        return csr_matrix([[1, 0, 0], [0, 1, 0]])


def test_piecewise_coordinate_steps_use_decoded_gates_and_freeze_unrelated_control(monkeypatch):
    p = BoxProblem(); calls = []
    # A discontinuous two-contact screen, independent of the search code.
    def constraints(x):
        stored = x.astype(np.float32).astype(float)
        cells = np.floor(stored[:2]/.00005+1e-8)
        return np.array([cells[0]-4., cells[1]-2.])
    monkeypatch.setattr(coordinate, 'constraint_model', lambda p, z, **kw: constraints(z))
    def evaluate(x, label):
        p.rotations(x); calls.append((label, x.copy()))
        return constraints(x)
    x, report = coordinate.restore(p, [.0004, .0004, .0007], evaluate, iterations=8, trust=.0002)
    assert report['sampled_proxy_feasible'] and report['reason'] == 'sampled_constraints_satisfied'
    assert np.max(evaluate(x, 'check')) <= 0
    assert x[2] == .0007 and not report['quality_approved']
    assert all(2 not in r['columns'] for r in report['history'])
    assert len(calls)-1 == 1+sum(len(r['probes']) for r in report['history'])
    for row in report['history']:
        start = np.asarray(row['starting_controls'])
        for screen in row['numerical_screens']:
            z = start.copy(); z[screen['column']] += screen['delta']
            p.rotations(z)
            assert abs(screen['delta']) <= row['trust_radians']+1e-18
            np.testing.assert_array_equal(coordinate.merit(constraints(z)), screen['proxy_merit'])
        assert row['after_merit'][0] < row['before_merit'][0]


def test_improving_proxy_cannot_replace_a_rejected_decoded_clip(monkeypatch):
    p = BoxProblem(); calls = []
    monkeypatch.setattr(coordinate, 'constraint_model', lambda p, z, **kw: np.array([z[0]/.001, -1.]))
    def evaluate(x, label):
        p.rotations(x); calls.append(label)
        return np.array([1., -1.])
    start = np.array([.0005, .0004, .0007])
    x, report = coordinate.restore(p, start, evaluate, iterations=8, trust=2e-7)
    np.testing.assert_array_equal(x, start)
    assert not report['sampled_proxy_feasible'] and report['reason'] == 'coordinate_search_stalled'
    assert all(r['selected_screen_index'] is None for r in report['history'])
    assert all(not p['accepted'] for r in report['history'] for p in r['probes'])
    assert len(calls) == 1+sum(len(r['probes']) for r in report['history'])
    assert all(len(r['probes']) == 3 for r in report['history'])


def test_constraint_population_change_is_rejected(monkeypatch):
    monkeypatch.setattr(coordinate, 'constraint_model', lambda p, z, **kw: np.array([1., -1., 1.]))
    with pytest.raises(ValueError, match='population'):
        coordinate.restore(BoxProblem(), [.0005, .0004, .0007], lambda z, label: np.array([1., -1.]))


@pytest.mark.parametrize('iterations,trust', [(0,.0002),(33,.0002),(True,.0002),(8,0),(8,.00101),(8,True),(8,float('nan'))])
def test_invalid_budgets_rejected_before_evaluation(iterations,trust):
    with pytest.raises(ValueError):
        coordinate.restore(None, None, None, iterations=iterations, trust=trust)


@pytest.mark.parametrize('mode',[True,1,'yes',None])
def test_coordinate_mode_needs_explicit_warm_job(mode):
    from native_support_job import run
    with pytest.raises(ValueError, match='[Rr]epair'):
        run(None, None, None, repair_coordinates=mode)


def test_real_coordinate_jobs_preserve_bounds_and_chained_evidence(tmp_path,monkeypatch):
    from test_native_support import fixture
    from strep import read,save,sha256
    import native_support_job as job
    monkeypatch.setattr(job, 'ROOT', tmp_path); (tmp_path/'reports').mkdir()
    source,rig,reader,spec = fixture(tmp_path,plane=.2)
    draft=tmp_path/'draft.json';save(draft,spec)
    flags=dict(joint_rates=True,joint_swivel=True,joint_foot_orientation=True)
    warm=tmp_path/'reports'/'warm'
    first=job.run(source,draft,warm,**flags,joint_evaluations=1)
    frozen={str(p):sha256(p) for p in warm.rglob('*') if p.is_file()}
    output=tmp_path/'reports'/'coordinate'
    result=job.run(source,draft,output,**flags,repair_from=warm,repair_coordinates=True,
                   repair_iterations=1,repair_trust=2e-7)
    request=read(output/'request.json')
    assert request['proposal_method']=='serialized_native_support_coordinate_repair'
    assert request['repair_coordinate_search'] and request['repair_quantized_differences']
    assert request['spec']==spec and request['rate_tolerance']==1e-5
    assert sha256(output/'implementation/native_support_coordinates.py')==request['implementation']['native_support_coordinates.py']
    assert result['status']=='complete' and result['retained_input'] and not result['quality_approved']
    for t in result['trials']:
        assert t['status']=='complete'
        q=t['proposal'][0];assert q['method']==request['proposal_method']
        assert q['probes'][0]['sha256']==first['trials'][t['trial']]['sha256']
        assert q['final_merit'][0]<=q['initial_merit'][0]
        assert q['numerical_screens']==sum(len(r['numerical_screens']) for r in q['history'])
        for probe in q['probes']:assert sha256(output/probe['file'])==probe['sha256']
        old=read(warm/f"trial-{t['trial']}.controls.json");new=read(output/q['controls_file'])
        for k in ('lower','upper','intervals'):assert old[k]==new[k]
    chained=tmp_path/'reports'/'chained'
    child=job.run(source,draft,chained,**flags,repair_from=output,repair_coordinates=True,
                  repair_iterations=1,repair_trust=2e-7)
    bound=read(chained/'request.json')
    assert set(request['inputs']).issubset(bound['inputs'])
    assert sha256(output/'result.json')==bound['inputs'][str(output/'result.json')]
    assert all(t['proposal'][0]['probes'][0]['sha256']==result['trials'][t['trial']]['sha256'] for t in child['trials'])
    assert all(sha256(p)==h for p,h in frozen.items())
    probe=output/result['trials'][0]['proposal'][0]['probes'][0]['file']
    probe.write_bytes(probe.read_bytes()+b'changed')
    rejected=tmp_path/'reports'/'rejected'
    with pytest.raises(ValueError,match='hash'):
        job.run(source,draft,rejected,**flags,repair_from=chained,repair_coordinates=True)
    assert not rejected.exists()
