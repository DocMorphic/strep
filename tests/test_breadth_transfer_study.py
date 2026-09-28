import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from breadth_transfer_study import summarize


def test_missing_transfer_and_context_stay_unvalidated():
    spec={'planned_transfers':3,'floor_screen_m':.01,'motions':[
        dict(id='a',family='dance',case='a',seed=1,flat_floor_screen_applicable=True,scene_validation='not_required',native_mesh_depth_m=.005),
        dict(id='b',family='water',case='b',seed=1,flat_floor_screen_applicable=False,scene_validation='missing_required_context_validation',native_mesh_depth_m=None)]}
    data={'engine_groups':[],'rows':[
        dict(id='a-r1',motion='a',rig='r1',status='complete',result={'target_mesh_floor_depth_max_m':.03}),
        dict(id='a-r2',motion='a',rig='r2',status='failed',error='Unsupported input'),
        dict(id='b-r1',motion='b',rig='r1',status='pending')]}
    result=summarize(spec,data)
    assert result['planned']==3 and result['complete']==result['failed']==result['pending']==1
    assert result['rows'][0]['native_floor_screen'] is True and result['rows'][0]['target_floor_screen'] is False
    assert result['rows'][1]['target_floor_screen'] is None
    assert result['rows'][2]['target_floor_screen'] is None and result['rows'][2]['native_floor_screen'] is None
    assert not result['quality_approved'] and all(r['human_review'] is None for r in result['rows'])
