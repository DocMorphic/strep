"""Exercise the decoded verifier with an actual GLB, including a bad edit."""
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from test_rig_clearance import setup
from strep import save,sha256
from rig_loop import encode,place
from verify_breadth_contact import verify


@pytest.mark.parametrize('vertical_shift',[0,.13])
def test_decoded_verifier_rejects_root_budget_violation(tmp_path,vertical_shift):
    rig,world,_,spec,targets=setup(5)
    root=spec['root_node']
    (tmp_path/'input').mkdir();(tmp_path/'candidate').mkdir()
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}
    encode(copy.deepcopy(rig),world,animated,root,tmp_path/'input/character.glb','Control')
    transform=np.eye(4);transform[1,3]=vertical_shift
    changed=place(world,rig.parents,root,transform)
    times,_=encode(copy.deepcopy(rig),changed,animated,root,tmp_path/'candidate/character.glb','Candidate')
    spec['glb_sha256']=sha256(tmp_path/'input/character.glb')
    save(tmp_path/'spec.json',spec)
    save(tmp_path/'request.json',dict(input_glb_sha256=spec['glb_sha256'],targets_m={k:v.tolist() for k,v in targets.items()},
        support=dict(guides={k:dict(weights=[0]*5,anchors_xz_m=[[0,0]]*5) for k in spec['patches']})))
    for version in ['input','candidate']:
        save(tmp_path/version/'contacts.json',dict(intervals=[dict(joint='LeftFoot',start_frame=0,end_frame_exclusive=5)]))
    save(tmp_path/'candidate/root-motion.json',dict(times_s=times.tolist(),positions_m=changed[:,root,:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(changed[:,root,:3,:3]).as_quat().tolist()))
    if vertical_shift:
        with pytest.raises(ValueError,match='root edit exceeds root_vertical_m'):verify(tmp_path)
    else:
        result=verify(tmp_path)
        assert result['bounds_and_preservation_passed']
        assert result['quality_approved'] is False and result['human_review'] is None
        assert result['metrics']['candidate']['feet']['Left']['predicted_support_steps']==4
