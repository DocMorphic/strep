import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read, sha256
from rig_contact_authoring import source
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_joint_recipe import envelope, validate, prepare, compile_recipe


def request(variant='transfer'):
    previous, result, original, report, glb = source('20260926-202244-c3c3bb14', variant)
    rig = RigAsset.load(glb); world, _ = baseline(rig, report['frames'])
    node = report['mapping']['RightHand']; frame = 30
    return dict(source_job=previous.name, variant=variant, edit=dict(schema='strep-rig-joint-edit-v1',
        glb_sha256=sha256(glb), label='World target', start_frame=15, last_frame=45,
        goals=[dict(frame=frame, node=node, position_m=world[frame,node,:3,3].tolist(),
                    rotation_xyzw=Rotation.from_matrix(world[frame,node,:3,:3]).as_quat().tolist())]))


def test_window_keeps_two_samples_at_both_edges_and_all_context():
    e=envelope(61,15,45)
    assert not e[:17].any() and not e[44:].any() and e[30]==1
    np.testing.assert_array_equal(e[15:46],e[15:46][::-1])
    with pytest.raises(ValueError):envelope(61,15,19)


@pytest.mark.parametrize('fault', ['hash','duplicate','boundary','node','nan','quaternion','unknown','window','empty'])
def test_invalid_joint_requests_rejected(fault):
    p=request();edit=p['edit'];goal=edit['goals'][0]
    if fault=='hash':edit['glb_sha256']='0'*64
    if fault=='duplicate':edit['goals'].append(copy.deepcopy(goal))
    if fault=='boundary':goal['frame']=16
    if fault=='node':goal['node']=9999
    if fault=='nan':goal['position_m'][0]=float('nan')
    if fault=='quaternion':goal['rotation_xyzw']=[0,0,0,2]
    if fault=='unknown':edit['hidden_limit_override']=90
    if fault=='window':edit['last_frame']=61
    if fault=='empty':edit['goals']=[]
    with pytest.raises(ValueError):validate(p)


@pytest.mark.parametrize('variant', ['transfer','corrected'])
def test_snapshot_compiles_real_imported_rig_and_preserves_authored_contacts(tmp_path,variant):
    from rig_pose_trajectory import PoseTrajectoryFitter
    from rig_coupled_pose import CoupledPoseFitter,window_basis
    from rig_pose_tolerances import PoseTolerances
    p=request(variant);previous,_,report,glb,edit=validate(p);original_hash=sha256(glb)
    folder=tmp_path/'edit';job=prepare(p,folder)
    assert job['kind']=='joint_edit' and sha256(glb)==original_hash
    assert sha256(folder/'input/character.glb')==original_hash
    assert all(sha256(folder/name)==digest for name,digest in job['input_files'].items())
    assert read(folder/'input/contact-spec.json')['glb_sha256']==original_hash
    assert sha256(folder/'input/parent-contact-spec.json')==sha256(previous/'contact-spec.json')
    targets=read(folder/'joint-targets.json');spec=read(folder/'joint-spec.json')
    authored=read(previous/'contact-spec.json')['contacts'][0];support=targets['supports'][0]
    assert support['target_position_m']==authored['target_position_m']
    assert support['start_frame']==authored['start_frame'] and support['end_frame_exclusive']==authored['end_frame_exclusive']
    assert report['mapping']['RightHand'] in [v['node'] for v in spec['edit_joints'].values()]
    rig=RigAsset.load(folder/'input/character.glb');data=dict(np.load(folder/'joint-input.npz'))
    fitter=PoseTrajectoryFitter(rig,spec,data['local'],{k:np.array(v) for k,v in targets['targets_m'].items()},targets['envelope'],targets['supports'],targets['goals'])
    coupled=CoupledPoseFitter(fitter,window_basis(targets['envelope'],spacing=10))
    metrics=PoseTolerances(coupled).metrics(np.zeros(np.prod(coupled.shape)))
    assert all(r['within_tolerances'] for r in metrics)
    np.testing.assert_allclose(fitter.world,data['before'],atol=1e-12)


def test_unconfirmed_predictions_not_converted_to_authored_support():
    p=request();_,_,report,glb,edit=validate(p)
    compiled=compile_recipe(RigAsset.load(glb),report,edit)
    assert compiled['supports']==[]
    assert set(compiled['targets'])=={'Left','Right'}
