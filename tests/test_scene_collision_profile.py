"""A CCD comparison must reject hidden changes in the engine protocol."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_collision_profile import (PREFIX,THRESHOLD,PENETRATION,TRACKED_SETTINGS,
    profile_settings,config_lines,verify_settings,matched_settings)


def settings():
    return {THRESHOLD:.75,PENETRATION:.25,
        PREFIX+'simulation/penetration_slop':.001,
        PREFIX+'simulation/baumgarte_stabilization_factor':.2,
        PREFIX+'simulation/position_steps':2,PREFIX+'simulation/velocity_steps':10,
        PREFIX+'collisions/collision_margin_fraction':0.,
        PREFIX+'simulation/speculative_contact_distance':.02,
        'physics/common/physics_ticks_per_second':60,'physics/3d/default_gravity':9.81}


@pytest.mark.parametrize('name',[None,False,'unknown','strict-ccd\n'])
def test_unknown_profile_rejects(name):
    with pytest.raises(ValueError):profile_settings(name)


def test_profiles_only_override_two_ccd_settings_and_return_detached_values():
    assert profile_settings('engine-default')=={} and config_lines('engine-default')==''
    assert profile_settings('ccd-threshold')=={THRESHOLD:.05}
    value=profile_settings('strict-ccd');value[THRESHOLD]=999
    assert profile_settings('strict-ccd')=={THRESHOLD:.05,PENETRATION:.01}
    assert 'physics/' not in config_lines('strict-ccd') and 'simulation/continuous_cd_movement_threshold=0.05\n' in config_lines('strict-ccd')


@pytest.mark.parametrize('fault',['missing','extra','bool','nan','null','wrong-rate','slop','margin','threshold','penetration'])
def test_actual_setting_echo_cannot_be_missing_nonfinite_or_change_declared_controls(fault):
    echo=settings();echo.update(profile_settings('strict-ccd'))
    if fault=='missing':echo.pop(THRESHOLD)
    elif fault=='extra':echo['undocumented']=1
    elif fault in ('bool','nan','null'):echo[THRESHOLD]={'bool':True,'nan':float('nan'),'null':None}[fault]
    elif fault=='wrong-rate':echo['physics/common/physics_ticks_per_second']=120
    elif fault=='slop':echo[PREFIX+'simulation/penetration_slop']=.01
    elif fault=='margin':echo[PREFIX+'collisions/collision_margin_fraction']=.1
    elif fault=='threshold':echo[THRESHOLD]=.75
    else:echo[PENETRATION]=.25
    with pytest.raises(ValueError):verify_settings('strict-ccd',echo,60)


@pytest.mark.parametrize('key',[PREFIX+'simulation/position_steps',PREFIX+'simulation/velocity_steps',PREFIX+'simulation/speculative_contact_distance',PREFIX+'simulation/baumgarte_stabilization_factor',PENETRATION])
def test_hidden_solver_changes_do_not_count_as_a_threshold_only_comparison(key):
    baseline=settings();candidate={**baseline,**profile_settings('ccd-threshold')};candidate[key]*=2
    with pytest.raises(ValueError,match='Unrelated'):matched_settings(baseline,candidate,'ccd-threshold',60)


def test_explicit_tightening_keeps_every_other_control_identical():
    baseline=settings();candidate={**baseline,**profile_settings('strict-ccd')}
    changes=matched_settings(baseline,candidate,'strict-ccd',60)
    assert changes=={THRESHOLD:{'before':.75,'after':.05},PENETRATION:{'before':.25,'after':.01}}
    assert set(baseline)==set(TRACKED_SETTINGS) and verify_settings('engine-default',baseline,60)==baseline


def test_native_study_rejects_wrong_backend_and_disabled_actual_body_ccd():
    from study_scene_prop_ownership import verify
    request=dict(collision_profile='engine-default',tracked_collision_settings=list(TRACKED_SETTINGS),physics_fps=60,cases=[{'id':'shared'}])
    actual=dict(backend='Godot Physics',collision_settings=settings(),cases=[])
    with pytest.raises(ValueError,match='Jolt'):verify(request,actual)
    actual.update(backend='Jolt Physics',cases=[dict(id='shared',malformed_rejected=5,second_owner_rejected=True,continuous_cd={'P':True,'Q':False})])
    with pytest.raises(ValueError,match='actual prop CCD'):verify(request,actual)
