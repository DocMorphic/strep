"""Real pinned-engine sampling; generated fixtures only, no renderer or model."""
from pathlib import Path
import os
import pytest
from test_native_engine_rotation_speed import make_scene
from native_engine_rotation_speed import run,verify
from strep import read


@pytest.mark.parametrize('mode,helper,maximum',[('import',True,200),('native-authoring',True,200),
    ('import',False,200),('native-authoring',True,100),('import',True,100)])
def test_actual_engine_imported_worlds_and_fresh_speed_replay(tmp_path,mode,helper,maximum):
    engine=os.environ.get('STREP_TEST_GODOT')
    if not engine:pytest.skip('Actual pinned engine path required; source mocks are separate')
    assert Path(engine).is_file()
    contacts,policy,_=make_scene(tmp_path/'input',helper=helper)
    from strep import save
    authored=read(policy);authored['tracks'][0]['maximum_degrees_per_second']=maximum;save(policy,authored)
    folder=tmp_path/'engine'
    try:result=run(contacts,policy,folder,engine=engine,playback_mode=mode)
    except Exception:
        if (folder/'engine.log').exists():print((folder/'engine.log').read_text(encoding='utf-8'))
        raise
    assert result==verify(contacts,policy,folder)
    assert result['engine']['major']==4 and result['engine']['minor']==7 and result['engine']['patch']==2
    assert result['tracks'][0]['comparisons']==4
    assert result['tracks'][0]['speed_acceptance_allowance']==0
    if helper:assert [n['node'] for n in result['capture_mapping']['A']]==[0,7]
    print('ACTUAL_SPEED_AUDIT',mode,helper,maximum,result['tracks'][0]['maximum_observed_degrees_per_second'],
        result['source_pose_comparison']['A']['maximum_world_element_error'],result['all_sampled_conditions_pass'])
    if mode=='native-authoring':
        assert result['source_pose_conditions_pass']
        assert result['rotation_speed_conditions_pass'] is (maximum==200)
        assert result['all_sampled_conditions_pass'] is (maximum==200)
    else:
        # Fixed-rate interpolation is intentionally not treated as source-key
        # identity. This fixture exposes an actual importer discrepancy.
        assert not result['source_pose_conditions_pass']
        assert result['source_pose_comparison']['A']['maximum_world_element_error']>.01
        assert not result['all_sampled_conditions_pass']
    assert not result['rendering_verified'] and not result['quality_approved']
    actual=read(folder/'engine-output.json');assert actual['cases'][0]['frames']
