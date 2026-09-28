import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from scene_generation import actor_guides,requests


def scene():
    return read(ROOT/'reports/hand-frame-fit-v1/hand-frame-high-five-seed-11/candidate.json')['scene']


def plan():
    return {name:dict(segments=[dict(prompt='A person raises a hand.',duration_s=4)],seeds=[77 if name=='A' else 88]) for name in ['A','B']}


def test_scene_actor_conditions_preserve_native_pose_and_shared_clock():
    value=scene();original=copy.deepcopy(value);batch=requests(value,plan())
    assert value==original
    assert len(batch['requests'])==4
    assert 'generation_constraints' not in batch['requests'][0]
    guide=batch['requests'][1]['generation_constraints'][0]
    assert guide['frame_indices']==guide['source_frames']==[60]
    assert guide['motion']==value['actors']['A']['motion']
    assert guide['joint_names']==['RightHand']


def test_simultaneous_hands_become_one_nonconflicting_model_guide():
    value=scene();extra=copy.deepcopy(next(c for c in value['contacts'] if c['actor']=='A'))
    extra['effector']['joint']='LeftHand';value['contacts'].append(extra)
    guide=actor_guides(value,'A')
    assert len(guide)==1 and guide[0]['joint_names']==['LeftHand','RightHand']


@pytest.mark.parametrize('mutation',['hash','tilt','elevation','frame','effector','clock','missing_actor'])
def test_unrepresentable_or_stale_scene_guide_rejected(mutation):
    value=scene();p=plan()
    if mutation=='hash':value['actors']['A']['source_sha256']='0'*64
    if mutation=='tilt':value['actors']['A']['transform']['rotation_xyzw']=[1,0,0,0]
    if mutation=='elevation':value['actors']['A']['transform']['translation_m'][1]=1
    if mutation=='frame':value['contacts'][0]['end_frame']=120
    if mutation=='effector':value['contacts'][0]['effector']['joint']='Head'
    if mutation=='clock':p['A']['segments'][0]['duration_s']=3
    if mutation=='missing_actor':del p['B']
    with pytest.raises(ValueError):requests(value,p)


def test_unfitted_new_target_is_not_silently_conditioned_on_old_pose(tmp_path):
    from scene_generation import prepare
    from strep import save
    value=scene();value['contacts'][0]['target']['point_m'][0]+=1
    save(tmp_path/'scene.json',value);save(tmp_path/'plan.json',plan())
    with pytest.raises(ValueError,match='Fit source poses'):
        prepare(tmp_path/'scene.json',tmp_path/'plan.json',tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_scene_markers_keep_authored_window_semantics_and_terminal_end():
    from package_generated_scenes import contact_events
    value=scene();value['contacts'][0]['start_frame']=119;value['contacts'][0]['end_frame']=119
    document=contact_events(value)
    assert 'not detected or successful' in document['provenance']
    assert [e['frame'] for e in document['events']]==sorted(e['frame'] for e in document['events'])
    end=next(e for e in document['events'] if e['contact_id']==value['contacts'][0]['id'] and e['type']=='contact_window_end')
    assert end['frame']==120 and end['time_s']==4
