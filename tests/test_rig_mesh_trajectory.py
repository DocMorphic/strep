"""Independent derivatives, anticipation, original bounds and decoded rejection."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from target_rig_contact import baseline, Fitter
from rig_mesh_trajectory import MeshContactTrajectoryFitter, CoupledMeshContactFitter, run
from rig_coupled_pose import window_basis
from strep import read, save, sha256


def make(tmp_path, frames=7):
    source, rig, _, _ = fixture(tmp_path)
    before, local = baseline(rig, frames)
    target = rig.vertices(before[3]).mean(axis=0)+[0, .03, 0]
    spec = dict(schema='strep-target-contact-v1', glb_sha256=sha256(source),
        fps=30, frames=frames, provenance='Synthetic arbitrary mesh patch; no anatomical claim',
        root_node=0, patches={'Palm proxy': dict(vertices=[0, 1, 2])},
        contacts=[dict(patch='Palm proxy', start_frame=3, end_frame_exclusive=4,
                       target_position_m=target.tolist())],
        edit_joints={str(n): dict(node=n, limit_degrees=25) for n in (1, 2, 3)},
        limits=dict(root_horizontal_m=.04, root_vertical_m=.12, root_step_m=.015,
                    joint_step_degrees=5), screen=dict(floor_depth_m=.005, contact_error_m=.02),
        objective=dict(contact_weight=12., floor_weight=4., rotation_prior_m_per_radian=.035,
                       root_prior=1., temporal_weight=.5), max_nfev=120)
    return source, rig, before, local, spec


def independent_energy(fitter, parameters):
    original = Fitter(fitter.rig, fitter.spec, fitter.local)
    previous = np.zeros(parameters.shape[1]); total = 0.
    for frame, value in enumerate(parameters):
        residual = original.residual(frame, value, previous)
        total += residual@residual; previous = value
    return total


@pytest.mark.parametrize('vertical_shift', [0., -.26])
def test_coupled_gradient_matches_original_objective_and_independent_skin(tmp_path, vertical_shift):
    _, rig, _, local, spec = make(tmp_path)
    local[:, spec['root_node'], 1, 3] += vertical_shift
    spec['patches']['Shin proxy'] = dict(vertices=[1, 2])
    spec['contacts'].append(dict(patch='Shin proxy', start_frame=1, end_frame_exclusive=3,
                                 target_position_m=[-.2, .15, .03]))
    f = MeshContactTrajectoryFitter(rig, spec, local, np.ones(7))
    assert bool(np.any(f.positions[:, :, 1]<0)) == (vertical_shift<0)
    coupled = CoupledMeshContactFitter(f, window_basis(f.envelope, 2))
    rng = np.random.default_rng(462)
    x = rng.normal(size=np.prod(coupled.shape))*.003
    value, gradient = coupled.objective_pair(x)
    assert value == pytest.approx(independent_energy(f, coupled.parameters(x)), abs=1e-10)
    for _ in range(12):
        direction = rng.normal(size=len(x)); direction /= np.linalg.norm(direction); step=1e-7
        numeric = (independent_energy(f, coupled.parameters(x+step*direction))
                   - independent_energy(f, coupled.parameters(x-step*direction)))/(2*step)
        assert gradient@direction == pytest.approx(numeric, rel=5e-5, abs=1e-6)


@pytest.mark.parametrize('frame', [0, 2, 3, 6])
def test_coordinate_jacobian_with_contact_and_both_temporal_neighbors(tmp_path, frame):
    _, rig, _, local, spec = make(tmp_path)
    f = MeshContactTrajectoryFitter(rig, spec, local, np.ones(7)); rng=np.random.default_rng(79)
    for index in range(7): f.accept(index, rng.normal(size=len(f.bounds))*.003)
    x = f.values[frame].copy(); residual, jac = f.trajectory_pair(frame, x)
    for column in range(len(x)):
        d = np.eye(len(x))[column]*1e-7
        numeric = (f.trajectory_pair(frame, x+d)[0]-f.trajectory_pair(frame, x-d)[0])/2e-7
        np.testing.assert_allclose(jac[:, column], numeric, atol=5e-7, rtol=5e-5)
        plus=f.values.copy(); minus=f.values.copy(); plus[frame]+=d; minus[frame]-=d
        slope=(independent_energy(f, plus)-independent_energy(f, minus))/2e-7
        assert (2*jac.T@residual)[column] == pytest.approx(slope, abs=1e-6, rel=5e-5)


def test_anticipates_future_contact_and_preserves_fixed_context_and_limits(tmp_path):
    _, rig, before, local, spec = make(tmp_path)
    envelope=np.array([0, 1, 1, 1, 1, 1, 0.])
    f=MeshContactTrajectoryFitter(rig, spec, local, envelope)
    coupled=CoupledMeshContactFitter(f, window_basis(envelope, 2))
    initial_error=np.linalg.norm(f.positions[3].mean(axis=0)-spec['contacts'][0]['target_position_m'])
    with threadpool_limits(limits=1): values, _, summary=coupled.solve(tmp_path, 40)
    assert summary['cost_after'] < summary['cost_before'] and summary['constraint_min']>=-1e-8
    assert np.linalg.norm(f.positions[3].mean(axis=0)-spec['contacts'][0]['target_position_m']) < initial_error*.6
    assert values[2, 1]>.001 # A real adjustment before the target activates.
    np.testing.assert_array_equal(values[[0, -1]], 0)
    np.testing.assert_allclose(f.world[[0, -1]], before[[0, -1]], atol=1e-12)
    assert np.all(np.abs(values)<=f.bounds*envelope[:, None]+1e-8)
    for index, value in enumerate(values): assert f.constraints(index, value)[0].min()>=-1e-7


def test_actual_export_binds_original_draft_and_retains_rejected_input(tmp_path):
    source, _, _, _, spec = make(tmp_path)
    # The target is deliberately outside the existing edit budget.
    spec['contacts'][0]['target_position_m'][1]+=2
    draft=tmp_path/'draft.json'; save(draft, spec); hashes=(sha256(source), sha256(draft))
    output=tmp_path/'trial'; result=run(source, draft, output, spacing=2, max_iterations=2)
    assert result['retained_input'] and result['selected_file']=='original.glb'
    assert not result['quality_approved'] and not result['numerical_screen_passed']
    assert sha256(output/'original.glb')==hashes[0] and sha256(output/'contact-spec.json')==hashes[1]
    assert read(output/'independent-inspection.json')['failed_intervals']==1
    assert result['roundtrip']['skin_error_m']<1e-5
    assert (sha256(source), sha256(draft))==hashes
    for name, digest in result['outputs'].items(): assert sha256(output/name)==digest
    for name, digest in read(output/'request.json')['implementation'].items():
        assert sha256(output/'implementation'/name)==digest
    with pytest.raises(FileExistsError): run(source, draft, output, spacing=2, max_iterations=2)


@pytest.mark.parametrize('spacing,iterations', [(True, 2), (0, 2), (121, 2), (2, True), (2, 0), (2, 201)])
def test_invalid_control_budgets_rejected_without_output(tmp_path, spacing, iterations):
    source, _, _, _, spec=make(tmp_path); draft=tmp_path/'draft.json'; save(draft, spec)
    with pytest.raises(ValueError): run(source, draft, tmp_path/'trial', spacing, iterations)
    assert not (tmp_path/'trial').exists()


def test_misbound_source_and_trajectory_length_rejected(tmp_path):
    source, rig, _, local, spec=make(tmp_path); draft=tmp_path/'draft.json'
    wrong=copy.deepcopy(spec); wrong['glb_sha256']='0'*64; save(draft, wrong)
    with pytest.raises(ValueError, match='source changed'): run(source, draft, tmp_path/'trial')
    with pytest.raises(ValueError, match='length differ'):
        MeshContactTrajectoryFitter(rig, spec, local[:-1], np.ones(6))
