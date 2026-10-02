"""Synthetic native/support bridge checks; no human or physical quality evidence."""
from pathlib import Path
import sys
import shutil
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_studio_correction_review import setup,preview_fixture,corpus_fixture
import studio_correction_review as review
import studio_native_support as support
import native_review_support as bridge
import native_support_job as fitter
import inspect_motion
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels
from gltf_tools import read_glb,write_glb,append_accessor,accessor
from strep import read,save,sha256


@pytest.fixture
def native(setup,monkeypatch):
    selection=preview_fixture(setup,monkeypatch);draft=read(setup.draft);item=draft['items'][0]
    doc,binary=read_glb(item['source_preview']);names=[n['name'] for n in doc['nodes'][1:]]
    for j,name in ((67,'LeftLeg'),(68,'LeftShin'),(69,'LeftFoot'),(72,'RightLeg'),(73,'RightShin'),(74,'RightFoot')):
        names[j]=name;doc['nodes'][j+1]['name']=name
    binary=bytearray(binary)
    attrs=doc['meshes'][0]['primitives'][0]['attributes']
    for k in ('JOINTS_0','JOINTS_1'):
        value=accessor(doc,binary,attrs[k]);entry=doc['accessors'][attrs[k]];view=doc['bufferViews'][entry['bufferView']]
        start=view.get('byteOffset',0)+entry.get('byteOffset',0);values=np.full(value.shape,69,dtype=value.dtype)
        binary[start:start+values.nbytes]=values.tobytes()
    write_glb(item['source_preview'],doc,binary);item['source_preview_sha256']=sha256(item['source_preview'])
    item['source_end_frame_exclusive']=6;save(setup.draft,draft);setup.digest=sha256(setup.draft)
    parents=[-1]+[(j-1 if j%5 else 0) for j in range(1,77)]
    monkeypatch.setattr(inspect_motion,'skeleton_metadata',lambda _: (names,parents,[]))
    monkeypatch.setattr(support,'ROOT',setup.root);monkeypatch.setattr(bridge,'ROOT',setup.root);monkeypatch.setattr(fitter,'ROOT',setup.root)
    selection['draft_sha256']=setup.digest;preview=review.preview_request(selection)
    data=support.metadata(preview['id'],'native_review')
    spec=dict(schema='strep-native-support-v1',glb_sha256=data['glb_sha256'],animation_index=0,
              duration_s=data['duration_s'],root_node=1,mapping=data['mapping'],supports=[dict(id='fixture',foot='LeftFoot',
              stance_s=[1/30,4/30],edit_keys=[0,5],plane=dict(normal_xyz=[0,1,0],offset_m=0),
              clearance_m=.00025,maximum_gap_m=.005,maximum_displacement_m=.03,maximum_angle_degrees=45)])
    body=dict(source_job=preview['id'],variant='native_review',spec=spec)
    return setup,selection,preview,body


def test_checked_native_preview_supplies_exact_clock_and_known_native_roles(native):
    setup,selection,preview,body=native
    data=support.metadata(preview['id'],'native_review')
    assert data['native_review_selection']==selection and data['root_node']==1
    assert data['mapping']['LeftFoot']==70 and data['source_url']==preview['preview_url']
    assert data['clocks'][0]['times_s']==(np.arange(6,dtype=np.float32)/30).astype(float).tolist()
    assert not data['quality_approved'];support.validate_request(body)


@pytest.mark.parametrize('fault',['identifier','preview','candidate','method_archive'])
def test_native_source_mutation_or_unknown_preview_rejected(native,fault):
    setup,selection,preview,body=native;identifier=preview['id']
    if fault=='identifier':identifier='../'+identifier
    if fault=='preview':path=setup.root/'reports'/preview['preview_url'].removeprefix('/files/');path.write_bytes(path.read_bytes()+b'changed')
    if fault=='candidate':Path(selection['candidate_motion']['path']).write_bytes(b'changed')
    if fault=='method_archive':
        path=setup.root/'reports/native-correction-previews'/identifier/'methods/native_candidate_preview.py';path.write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):bridge.source(identifier)


def conversion_fixture(native,angles=1.,node=68):
    setup,selection,preview,body=native;folder=support.folder_for('bridge-fixture')
    request=support.prepare(body,folder);output=setup.root/'reports/fixture-fit';output.mkdir()
    doc,binary=read_glb(folder/'source.glb');channels=rotation_channels(doc,binary)
    quats=channels[node][2].copy();q=Rotation.from_quat(quats[2]).as_matrix()@Rotation.from_euler('x',angles,degrees=True).as_matrix()
    quats[2]=Rotation.from_matrix(q).as_quat();export_rotations(doc,binary,{node:quats},output/'candidate.glb')
    save(output/'result.json',dict(retained_input=False,retention_reason=None,output_support_samples_pass=True,
                                 source_supports=[dict(passed=False)],quality_approved=False))
    return folder,request,output


def test_conversion_changes_only_authored_leg_channels_with_numerical_screen_fixture(native,monkeypatch):
    setup,selection,preview,body=native;folder,request,output=conversion_fixture(native)
    # Explicit numerical component stub, not evidence that this geometry meets real support/rate checks.
    monkeypatch.setattr(bridge,'serialized_screens',lambda *args:dict(passed=True,support_samples_pass=True,source_rates_pass=True))
    result=bridge.convert(folder,request,output)
    assert result['changed_joints']==['LeftLeg'] and result['max_fitted_glb_matrix_error']<1e-5
    assert not result['retained_input'] and result['selected_support_samples_pass']
    with np.load(result['candidate_motion']['path'],allow_pickle=False) as converted,np.load(selection['candidate_motion']['path'],allow_pickle=False) as original:
        np.testing.assert_array_equal(converted['root_positions'],original['root_positions'])
        np.testing.assert_array_equal(converted['local_rot_mats'][:,np.arange(77)!=67],original['local_rot_mats'][:,np.arange(77)!=67])
        for frame in (0,1,3,4,5):np.testing.assert_array_equal(converted['local_rot_mats'][frame],original['local_rot_mats'][frame])
        assert 'foot_contacts' not in converted.files
    assert all(result[k] is False for k in ('quality_approved','training_admitted','release_approved'))
    assert result['preview']['selection']['candidate_motion']==result['candidate_motion']
    assert result['selected_contact_diagnostics']['changes_acceptance_gates'] is False
    assert result['selected_contact_diagnostics']['supports']
    assert result['proposal_contact_diagnostics']['supports']
    assert read(result['selected_support_events']['path'])['target_clip_sha256']==result['preview']['preview_sha256']


def test_cumulative_bound_failure_retains_actual_source_and_failed_native_proposal(native):
    setup,selection,preview,body=native;folder,request,output=conversion_fixture(native,angles=40)
    result=bridge.convert(folder,request,output)
    assert result['retained_input'] and result['retention_reason']=='native_original_relative_bounds_failed'
    assert 'correction_step_degrees' in result['native_bound_error'] and not result['selected_support_samples_pass']
    with np.load(result['candidate_motion']['path'],allow_pickle=False) as converted,np.load(selection['candidate_motion']['path'],allow_pickle=False) as original:
        np.testing.assert_array_equal(converted['local_rot_mats'],original['local_rot_mats'])
    assert sha256(result['proposal']['path'])==result['proposal']['sha256']


@pytest.mark.parametrize('fault',['outside_joint','clock','translation','mesh','payload'])
def test_conversion_rejects_unpreserved_native_tracks_or_geometry(native,fault):
    folder,request,output=conversion_fixture(native,node=4 if fault=='outside_joint' else 68)
    doc,binary=read_glb(output/'candidate.glb');binary=bytearray(binary)
    if fault=='mesh':doc['meshes'][0]['name']='changed'
    if fault=='payload':binary[0]^=1
    if fault in ('clock','translation'):
        sampler=doc['animations'][0]['samplers'][0]
        if fault=='clock':sampler['input']=append_accessor(doc,binary,np.arange(6,dtype=np.float32)/30+.001,'SCALAR')
        else:sampler['output']=append_accessor(doc,binary,np.full((6,3),2,dtype=np.float32),'VEC3')
    write_glb(output/'candidate.glb',doc,binary)
    with pytest.raises(ValueError):bridge.convert(folder,request,output)


def test_real_native_wrapper_retains_unreachable_synthetic_input_and_conversion(native):
    setup,selection,preview,body=native;folder=support.folder_for('actual-fixture')
    support.prepare(body,folder);support.run(folder);result=support.manifest('actual-fixture')
    converted=result['native_review_candidate']
    assert result['retained_input'] and not result['output_support_samples_pass']
    assert converted['retained_input'] and not converted['selected_support_samples_pass']
    assert converted['selection']==selection and all(t['status']=='rejected' for t in result['trials'])
    assert len(result['versions'])==3
    assert result['versions'][1]['id']=='native-selected'
    markers=support.served_file(result['events_url'].removeprefix('/files/'))
    assert markers and read(markers)['target_clip_sha256']==converted['preview']['preview_sha256']
    for ref in (converted['candidate_motion'],converted['proposal']):assert sha256(ref['path'])==ref['sha256']
    Path(converted['candidate_motion']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='pose tracks'):support.manifest('actual-fixture')


def test_native_wrapper_hash_binds_parent_selection_and_method_archives(native):
    setup,selection,preview,body=native;folder=support.folder_for('bound')
    request=support.prepare(body,folder);assert support.frozen(folder)==request
    path=folder/'implementation/native_review_support.py';path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='archive'):support.frozen(folder)


def test_real_serialized_screens_override_mock_fitter_pass_and_retain_input(native):
    folder,request,output=conversion_fixture(native)
    result=bridge.convert(folder,request,output)
    assert result['fitted_support_samples_pass']
    assert not result['proposal_serialized_screens']['passed']
    assert result['retained_input'] and result['retention_reason']=='native_serialized_support_screens_failed'
    assert not result['selected_support_samples_pass']
    assert result['proposal_preview']['selection']['candidate_motion']==result['proposal']


def test_actual_converted_contact_failure_overrides_mock_support_pass(native,monkeypatch):
    folder,request,output=conversion_fixture(native)
    from native_studio_plant import policy
    request['planting']=dict(maximum_patch_anchor_error_m=0.,maximum_patch_speed_m_s=0.)
    save(folder/'plant-policy.json',policy(folder/'source.glb',folder/'draft.json',request['planting']))
    request['plant_policy_sha256']=sha256(folder/'plant-policy.json')
    # A support-only fixture stub isolates the new branch. Actual exported
    # native geometry and fixed-patch position/speed are still independently
    # measured; this is not a successful physical-animation assertion.
    monkeypatch.setattr(bridge,'serialized_screens',lambda *args:dict(passed=True,support_samples_pass=True,source_rates_pass=True,
        supports=[dict(minimum_height_m=.001)]))
    result=bridge.convert(folder,request,output)
    assert result['retained_input'] and result['retention_reason']=='native_serialized_planting_gates_failed'
    assert not result['proposal_planting_audit']['contact_samples_pass']
    assert not result['proposal_planting_audit']['passed']
    with np.load(result['candidate_motion']['path'],allow_pickle=False) as converted,np.load(result['selection']['candidate_motion']['path'],allow_pickle=False) as source:
        np.testing.assert_array_equal(converted['local_rot_mats'],source['local_rot_mats'])
    assert result['selected_planting_audit'] is not None


def test_native_conversion_rejects_changed_plant_policy_before_export(native):
    folder,request,output=conversion_fixture(native)
    from native_studio_plant import policy
    request['planting']=dict(maximum_patch_anchor_error_m=.001,maximum_patch_speed_m_s=.005)
    save(folder/'plant-policy.json',policy(folder/'source.glb',folder/'draft.json',request['planting']))
    request['plant_policy_sha256']=sha256(folder/'plant-policy.json')
    changed=read(folder/'plant-policy.json');changed['supports'][0]['maximum_patch_anchor_error_m']=.002;save(folder/'plant-policy.json',changed)
    with pytest.raises(ValueError,match='planting policy'):bridge.convert(folder,request,output)
    assert not (folder/'native-proposal.npz').exists()


def test_studio_native_decision_and_markers_follow_conversion_not_mock_fitter_pass(native,monkeypatch):
    setup,selection,preview,body=native
    original=fitter.run
    def mock_fitter_pass(*args,**kwargs):
        result=original(*args,**kwargs)
        # Deliberately false fitter approval: the independent conversion must
        # still govern the Studio decision, selected clip and event status.
        result.update(retained_input=False,retention_reason=None,output_support_samples_pass=True)
        save(Path(args[2])/'result.json',result)
        return result
    monkeypatch.setattr(fitter,'run',mock_fitter_pass)
    folder=support.folder_for('conversion-decision')
    support.prepare(body,folder);support.run(folder)
    result=support.manifest('conversion-decision')
    assert result['fitted_retained_input'] is False
    assert result['fitted_output_support_samples_pass'] is True
    assert result['retained_input'] is True
    assert result['retention_reason']=='native_serialized_support_screens_failed'
    assert result['output_support_samples_pass'] is False
    chosen=result['native_review_candidate']
    assert result['versions'][1]['url']==chosen['preview']['preview_url']
    audit=support.served_file(result['native_conversion_url'].removeprefix('/files/'))
    assert audit==folder/'native-conversion.json'
    assert read(audit)['retained_input'] is True
    markers=support.served_file(result['events_url'].removeprefix('/files/'))
    assert read(markers)['constraint_status']=='unverified_on_retained_input'
    assert read(markers)['target_clip_sha256']==chosen['preview']['preview_sha256']
    assert read(markers)['quality_approved'] is False
    markers.write_bytes(markers.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='markers'):support.manifest('conversion-decision')
    assert support.served_file(result['events_url'].removeprefix('/files/')) is None
