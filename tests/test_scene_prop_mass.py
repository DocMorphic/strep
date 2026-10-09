"""Matched response population and malformed-data guards; no engine quality proof."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_scene_prop_mass import compare_runs


def record(mass):
    rows=[]
    for tick in range(4):
        rows.append(dict(tick=tick,session=0,transport='live',source_time_s=tick/60,modes={'P':'held' if tick<3 else 'released'},members={'P':['grip'] if tick<3 else []},
            props={'P':dict(pose=np.eye(4).tolist(),gravity=[0,-9.81,0],inverse_mass=1/mass)},scene=dict(actors={'A':dict(bones=np.zeros((2,4,3)).tolist())})))
    return dict(faults=[],quality_approved=False,release_approved=False,bodies={'P':dict(mass_kg=mass,continuous_cd=True,inertia_diagonal=[mass/2]*3)},
        engine={'fixture':'Synthetic comparison only'},collision_settings={},gravity_m_s2=9.81,gravity_direction=[0,-1,0],records=rows,physics_fps=60,last_tick=3)


def test_complete_mass_changes_do_not_imply_held_pose_or_strength_response():
    a,b=record(2),record(200);before=copy.deepcopy((a,b));result=compare_runs(a,b,'P',[2,200])
    assert result['records']==4 and result['held_ticks']==[0,1,2] and result['held_records']==3
    assert result['native_inertia_ratios']==[100]*3 and result['gravity_weight_N']==[19.62,1962]
    assert result['held_body_gravity_weight_N'][1]==dict(minimum=1962,maximum=1962)
    assert not result['measured_held_pose_mass_response'] and not result['quality_approved'] and not result['release_approved']
    assert (a,b)==before


@pytest.mark.parametrize('kind',['prop','actor'])
def test_detected_pose_response_is_separate_from_quality(kind):
    a,b=record(2),record(200)
    if kind=='prop':b['records'][1]['props']['P']['pose'][0][3]=.01
    else:b['records'][1]['scene']['actors']['A']['bones'][1][3][0]=.02
    result=compare_runs(a,b,'P',[2,200]);assert result['measured_held_pose_mass_response'] and not result['quality_approved']


@pytest.mark.parametrize('fault',['truncated-both','tick','session','transport','time','owner','mode','mass','mass-bool','ccd','fault','approved','rate-bool','last-bool','empty-actors','missing-actor','pose-shape','pose-nan','bones-shape','bones-nan','inertia-zero','inertia-nan','gravity-nan','inverse-mass','inverse-bool'])
def test_incomplete_or_unmatched_runs_are_never_a_valid_negative_result(fault):
    a,b=record(2),record(200);row=b['records'][1]
    if fault=='truncated-both':a['records'].pop();b['records'].pop()
    elif fault=='tick':row['tick']=0
    elif fault=='session':row['session']=1
    elif fault=='transport':row['transport']='preview'
    elif fault=='time':row['source_time_s']+=.001
    elif fault=='owner':row['members']['P']=[]
    elif fault=='mode':row['modes']['P']='released'
    elif fault=='mass':b['bodies']['P']['mass_kg']=2
    elif fault=='mass-bool':b['bodies']['P']['mass_kg']=True
    elif fault=='ccd':b['bodies']['P']['continuous_cd']=False
    elif fault=='fault':b['faults']=['bad']
    elif fault=='approved':b['quality_approved']=True
    elif fault=='rate-bool':b['physics_fps']=True
    elif fault=='last-bool':b['last_tick']=True
    elif fault=='empty-actors':a['records'][1]['scene']['actors']={};row['scene']['actors']={}
    elif fault=='missing-actor':row['scene']['actors']['B']=row['scene']['actors'].pop('A')
    elif fault=='pose-shape':row['props']['P']['pose']=[[1]]
    elif fault=='pose-nan':row['props']['P']['pose'][0][0]=float('nan')
    elif fault=='bones-shape':row['scene']['actors']['A']['bones']=[]
    elif fault=='bones-nan':row['scene']['actors']['A']['bones'][0][0][0]=float('nan')
    elif fault=='inertia-zero':b['bodies']['P']['inertia_diagonal'][0]=0
    elif fault=='inertia-nan':b['bodies']['P']['inertia_diagonal'][0]=float('nan')
    elif fault=='gravity-nan':row['props']['P']['gravity'][0]=float('nan')
    elif fault=='inverse-mass':row['props']['P']['inverse_mass']=.5
    else:row['props']['P']['inverse_mass']=True
    with pytest.raises((ValueError,KeyError,TypeError)):compare_runs(a,b,'P',[2,200])


@pytest.mark.parametrize('masses',[[2,2],[True,200],[-1,200],[2,float('nan')],[2,10001]])
def test_equal_or_invalid_mass_pairs_are_not_a_response_study(masses):
    with pytest.raises(ValueError):compare_runs(record(2),record(200),'P',masses)
