import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sampled_motion_caps import SampledMotionCaps
from diagnose_terminal_hand_rates import explain


def test_explanation_identifies_actor_joint_and_rate_stencil_time():
    times=np.arange(7)/10
    source=dict(positions=np.zeros((7,2,3)),rotations=np.tile(np.eye(3),(7,2,1,1)))
    caps=SampledMotionCaps(source,times,[0,.3,.6])
    payload=dict(indices=np.arange(2,6),positions=source['positions'][2:6].copy(),rotations=source['rotations'][2:6].copy())
    assert not any(row['violations'] for row in explain(payload,caps,['A:Hand','B:Hand']).values())
    payload['positions'][1,1,0]=.1
    rows=explain(payload,caps,['A:Hand','B:Hand'])
    assert rows['positional_speed']['violations']==2 and rows['positional_acceleration']['violations']==2
    assert rows['positional_acceleration']['worst']['joint']=='B:Hand'
    assert rows['positional_acceleration']['worst']['time_s']==pytest.approx(.3)
    assert rows['positional_acceleration']['worst']['value']==pytest.approx(20)
    assert rows['angular_speed']['violations']==rows['angular_acceleration']['violations']==0
    with pytest.raises(ValueError):explain(payload,caps,['A:Hand'])
