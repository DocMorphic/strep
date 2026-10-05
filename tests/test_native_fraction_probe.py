"""Local fraction diagnostics must agree with exports without admitting clips."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_fraction_probe import neighbors, local_rates
from native_rate_stage_trace import trace
from native_condition_ledger import RATE_METRICS
from test_native_rate_stage_trace import fixture


def test_finite_neighborhood_preserves_original_centers_and_does_not_truncate():
    result = neighbors([1, .5, .25, .125, .0625], [1e-6, 1e-5, 1e-4])
    assert len(result) == 221 and result == sorted(set(result), reverse=True)
    assert set([1, .5, .25, .125, .0625]).issubset(result)
    assert .062525 in result and min(result) > 0 and max(result) == 1
    with pytest.raises(ValueError, match='population exceeds'):
        neighbors([1, .5, .25, .125, .0625], [1e-6, 1e-5, 1e-4], maximum_probes=220)


@pytest.mark.parametrize('centers,radii,kwargs', [
    ([], [.001], {}), ([True], [.001], {}), ([0], [.001], {}), ([1.01], [.001], {}),
    ([np.nan], [.001], {}), ([.5,.5], [.001], {}), ([.5], [], {}), ([.5], [False], {}),
    ([.5], [0], {}), ([.5], [.02], {}), ([.5], [np.inf], {}), ([.5], [.001,.001], {}),
    ([.5], [.001], {'subdivisions':False}), ([.5], [.001], {'subdivisions':0}),
    ([.5], [.001], {'maximum_probes':False}), ([.5], [.001], {'maximum_probes':513})])
def test_invalid_grid_contract_rejects(centers, radii, kwargs):
    with pytest.raises(ValueError): neighbors(centers, radii, **kwargs)


@pytest.mark.parametrize('rotation', [False, True])
@pytest.mark.parametrize('kind', [name for name, _, _ in RATE_METRICS])
def test_all_native_rate_kinds_match_actually_serialized_nearby_curves(tmp_path, rotation, kind):
    _, edits, problem, _, row, cap, direction, _ = fixture(tmp_path, rotation, kind)
    origin = direction * .3; step = direction * .001
    fractions = neighbors([.5], [1e-4], subdivisions=1)
    origin_before=origin.copy(); direction_before=step.copy()
    result=local_rates(edits,origin,step,fractions,[row],[cap],[problem.caps['A'].tolerance],trust=.001)
    for i, probe in enumerate(result['probes']):
        path=tmp_path/f'nearby-{i}.glb'; edits.export('A',probe['controls'],path)
        actual=trace(edits,probe['controls'],row,path,source_cap=cap,source_tolerance=problem.caps['A'].tolerance)
        measured=probe['rows'][0]; decoded=actual['stages']['decoded']
        np.testing.assert_allclose(measured['vector'],decoded['vector'],atol=1e-10,rtol=1e-12)
        assert measured['residual']==pytest.approx(decoded['residual'],abs=1e-7,rel=1e-12)
        assert result['rows'][0] == actual['row'] and probe['all_requested_local_rows_pass']==measured['local_row_pass']
    np.testing.assert_array_equal(origin,origin_before);np.testing.assert_array_equal(step,direction_before)
    assert result['source_interval_s']==problem.caps['A'].dt
    for flag in ('source_cap_provenance_checked','actual_exports_decoded','full_native_conditions_checked',
                 'full_contact_or_geometry_checked','quantization_cells_proved','exhaustive_feasibility_proved',
                 'retained_clip_selected','quality_approved','release_approved'):
        assert result[flag] is False


@pytest.mark.parametrize('fault', ['fraction-bool','fraction-zero','fraction-nan','duplicates','too-many-probes',
    'row-bool','non-rate-row','row-outside','missing-cap','cap-bool','cap-negative','tolerance-inf',
    'zero-direction','trust-bool','too-large-direction','outside-origin','outside-candidate'])
def test_bad_contract_or_bound_rejects_before_motion_queries(tmp_path,monkeypatch,fault):
    _,edits,problem,_,row,cap,direction,_=fixture(tmp_path)
    args=dict(origin=edits.initial.copy(),direction=direction*.001,fractions=[.5],row_indices=[row],
        source_caps=[cap],source_tolerances=[1e-5],trust=.001)
    if fault=='fraction-bool':args['fractions']=[True]
    if fault=='fraction-zero':args['fractions']=[0]
    if fault=='fraction-nan':args['fractions']=[np.nan]
    if fault=='duplicates':args['fractions']=[.5,.5]
    if fault=='too-many-probes':args.update(fractions=[.5,.4],maximum_probes=1)
    if fault=='row-bool':args['row_indices']=[True]
    if fault=='non-rate-row':args['row_indices']=[0]
    if fault=='row-outside':args['row_indices']=[999999]
    if fault=='missing-cap':args['source_caps']=[]
    if fault=='cap-bool':args['source_caps']=[True]
    if fault=='cap-negative':args['source_caps']=[-1]
    if fault=='tolerance-inf':args['source_tolerances']=[np.inf]
    if fault=='zero-direction':args['direction']=edits.initial.copy()
    if fault=='trust-bool':args['trust']=True
    if fault=='too-large-direction':args['direction'][0]=np.nextafter(.001,np.inf)
    if fault=='outside-origin':args['origin'][0]=np.nextafter(1.,np.inf)
    if fault=='outside-candidate':args['origin'][0]=1.;args['direction'][0]=.0001
    monkeypatch.setattr(edits,'worlds',lambda *a,**k:pytest.fail('No motion query allowed'))
    with pytest.raises(ValueError):local_rates(edits,**args)


def test_changed_source_is_rejected_and_every_requested_row_is_measured(tmp_path):
    scene,edits,problem,ledger,row,cap,direction,_=fixture(tmp_path)
    other=row+1
    identity=ledger.locate(other); other_cap=float(problem.caps['A'].caps[3][identity['sample_index'],identity['joint_index']])
    result=local_rates(edits,edits.initial,direction*.001,[.5],[row,other],[cap,other_cap],[1e-5,1e-5],trust=.001)
    assert [r['row_index'] for r in result['probes'][0]['rows']]==[row,other]
    source=Path(next(iter(scene.inputs)));source.write_bytes(source.read_bytes()+b'changed')
    with pytest.raises(ValueError):
        local_rates(edits,edits.initial,direction*.001,[.5],[row],[cap],[1e-5],trust=.001)


def test_addition_ulp_is_moved_inward_to_meet_fraction_scaled_trust_without_slack(tmp_path):
    _,edits,_,_,row,cap,_,_=fixture(tmp_path)
    origin=edits.initial.copy();origin[0]=.04
    direction=edits.initial.copy();direction[0]=.001
    assert (origin+direction)[0]-origin[0]>.001
    result=local_rates(edits,origin,direction,[1.],[row],[cap],[1e-5],trust=.001)
    candidate=np.array(result['probes'][0]['controls'])
    assert candidate[0]==np.nextafter((origin+direction)[0],origin[0])
    assert abs(candidate-origin).max()<=.001 and result['exact_fraction_scaled_trust_box']


def test_changed_source_during_sampling_cannot_return_partial_success(tmp_path,monkeypatch):
    scene,edits,_,_,row,cap,direction,_=fixture(tmp_path)
    original=edits.worlds;path=Path(next(iter(scene.inputs)))
    def change(*args,**kwargs):
        result=original(*args,**kwargs);path.write_bytes(path.read_bytes()+b'changed');return result
    monkeypatch.setattr(edits,'worlds',change)
    with pytest.raises(ValueError):
        local_rates(edits,edits.initial,direction*.001,[.5],[row],[cap],[1e-5],trust=.001)


def test_rows_for_both_edited_partner_actors_match_their_actual_export(tmp_path):
    from test_native_contact_norms import prepared
    from native_scene_edit import SceneEdits
    from native_scene_fit import SceneProblem
    from native_condition_ledger import NativeConditionLedger
    import copy
    original,_,digest=prepared(tmp_path,partner=True,hold=True)
    declaration=dict(window_s=[0,2],protected_s=[],knots_s=[0,1,2],
        tracks=[dict(node=3,path='rotation',maximum_change=5)],maximum_joint_displacement_m=.02)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,
        actors=dict(B=copy.deepcopy(declaration),A=declaration))
    edits=SceneEdits(permissions,original.scene,digest,rotation_storage_policy='source-scale')
    problem=SceneProblem(original.scene,edits);ledger=NativeConditionLedger(original.scene,edits)
    rows=[];caps=[]
    for actor in ['B','A']:
        block=next(b for b in ledger.blocks if b['actor']==actor and b['kind']=='joint_angular_acceleration')
        row=block['start']+113*len(block['items'])+3
        rows.append(row);caps.append(float(problem.caps[actor].caps[3][113,3]))
    direction=np.full(edits.size,1e-7)
    result=local_rates(edits,edits.initial,direction,[.4999,.5,.5001],rows,caps,[1e-5,1e-5],trust=.001)
    assert [r['actor'] for r in result['rows']]==['B','A']
    for i,probe in enumerate(result['probes']):
        for actor,row,cap,measured in zip(['B','A'],rows,caps,probe['rows']):
            path=tmp_path/f'{actor}-{i}.glb';edits.export(actor,probe['controls'],path)
            actual=trace(edits,probe['controls'],row,path,source_cap=cap,source_tolerance=1e-5)
            np.testing.assert_allclose(measured['vector'],actual['stages']['decoded']['vector'],atol=1e-10,rtol=1e-12)
