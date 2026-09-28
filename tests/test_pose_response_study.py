import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_response_study import response_screen

def rows():
 return [dict(condition=c,seed=s,effector_position_m=[0,.06 if c=='offset' else 0,0],offset_target_error_m=.01) for c in ['free','captured','offset'] for s in [501,502,503]]

def test_response_counts_paired_seeds_and_target_accuracy():
 data=rows();assert response_screen(data,[0,.06,0])['numerical_response_screen_pass']
 for r in data:
  if r['condition']=='offset' and r['seed'] in [501,502]:r['offset_target_error_m']=.031
 assert not response_screen(data,[0,.06,0])['numerical_response_screen_pass']

def test_displacement_wrong_direction_fails_even_when_error_small():
 data=rows()
 for r in data:
  if r['condition']=='offset':r['effector_position_m']=[0,-.06,0]
 assert not response_screen(data,[0,.06,0])['numerical_response_screen_pass']

@pytest.mark.parametrize('mutation',['missing','duplicate','nan','zero'])
def test_incomplete_or_nonfinite_cannot_pass(mutation):
 data=rows();offset=[0,.06,0]
 if mutation=='missing':data.pop()
 if mutation=='duplicate':data.append(data[0])
 if mutation=='nan':data[-1]['effector_position_m']=[float('nan'),0,0]
 if mutation=='zero':offset=[0,0,0]
 with pytest.raises(ValueError):response_screen(data,offset)
