"""Real pinned-engine sampling; generated fixtures only, no renderer or model."""
from pathlib import Path
import os
import pytest
from test_native_engine_rotation_speed import make_scene
from native_engine_rotation_speed import run,verify
from strep import read


@pytest.mark.parametrize('mode,helper',[('import',True),('native-authoring',True),('import',False)])
def test_actual_engine_imported_worlds_and_fresh_speed_replay(tmp_path,mode,helper):
    engine=os.environ.get('STREP_TEST_GODOT')
    if not engine:pytest.skip('Actual pinned engine path required; source mocks are separate')
    assert Path(engine).is_file()
    contacts,policy,_=make_scene(tmp_path/'input',helper=helper)
    folder=tmp_path/'engine';result=run(contacts,policy,folder,engine=engine,playback_mode=mode)
    assert result==verify(contacts,policy,folder)
    assert result['engine']['major']==4 and result['engine']['minor']==7 and result['engine']['patch']==2
    assert result['tracks'][0]['comparisons']==4
    assert result['tracks'][0]['speed_acceptance_allowance']==0
    if helper:assert [n['node'] for n in result['capture_mapping']['A']]==[0,7]
    assert result['all_sampled_conditions_pass'],result
    assert not result['rendering_verified'] and not result['quality_approved']
    actual=read(folder/'engine-output.json');assert actual['cases'][0]['frames']
