import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read
from profile_inputs import DEFAULT_STUDY,validate_study,constraints_for,brief
from profile_metrics import canonical_cycle,phase_distance,speed_screen


def test_profile_config_and_time_path_are_consistent():
    study=validate_study(read(DEFAULT_STUDY));path=constraints_for(study)[0]
    assert len(path['frame_indices'])==120
    np.testing.assert_allclose(np.diff(path['smooth_root_2d'],axis=0),np.tile([0,.1],(119,1)))
    assert path['smooth_root_2d'][0]==[0,0]
    assert path['smooth_root_2d'][-1][1]==11.9
    assert len(study['profiles'])*len(study['seeds'])==15


def test_stats_are_explicitly_metadata_and_fatigue_preserves_capabilities():
    study=read(DEFAULT_STUDY);profiles={p['id']:p for p in study['profiles']}
    assert profiles['parkour']['capabilities']==profiles['fatigued']['capabilities']
    original=brief(study,profiles['parkour'],11)
    changed=copy.deepcopy(profiles['parkour']);changed['capabilities']['strength']=5
    assert brief(study,changed,11)['prompt']==original['prompt']
    assert 'not validated' in original['stat_status']


def test_profile_rejects_unsafe_ids_and_invalid_controls():
    study=read(DEFAULT_STUDY);study['id']='../bad'
    with pytest.raises(ValueError):validate_study(study)
    study=read(DEFAULT_STUDY);study['profiles'][0]['id']='../bad'
    with pytest.raises(ValueError):validate_study(study)
    study=read(DEFAULT_STUDY);study['profiles'][0]['capabilities']['agility']=101
    with pytest.raises(ValueError):validate_study(study)


def test_profile_cache_rejects_unknown_text_and_isolates_returned_tensors():
    from profile_encoder import ProfileEncoder
    from strep import ROOT
    import torch
    encoder=ProfileEncoder(ROOT/'models/prompt-cache-profile-pilot-v1/manifest.json')
    original,_=encoder([encoder.texts[0]])
    changed,_=encoder([encoder.texts[0]]);changed.zero_()
    actual,_=encoder([encoder.texts[0]])
    assert torch.equal(original,actual) and torch.count_nonzero(actual)>0
    assert len({row.view(torch.uint8).numpy().tobytes() for row in encoder.features})==5
    with pytest.raises(ValueError,match='real encoding'):encoder(['An unknown description.'])


def test_profile_cache_rejects_corrupted_embedding(tmp_path):
    from profile_encoder import ProfileEncoder
    from strep import ROOT,save
    import shutil
    source=ROOT/'models/prompt-cache-profile-pilot-v1'
    metadata=read(source/'manifest.json')
    for entry in metadata['entries'].values():shutil.copyfile(source/entry['file'],tmp_path/entry['file'])
    entry=next(iter(metadata['entries'].values()))
    (tmp_path/entry['file']).write_bytes(b'corrupt')
    save(tmp_path/'manifest.json',metadata)
    with pytest.raises(ValueError,match='checksum'):ProfileEncoder(tmp_path/'manifest.json')


def test_speed_screen_detects_wrong_speed_and_lateral_path():
    study=read(DEFAULT_STUDY);root=np.zeros((120,3));root[:,2]=np.arange(120)*.1
    assert speed_screen({'root_positions':root},study)['accepted']
    root[:,0]=np.linspace(0,.3,120)
    assert 'pelvis_path' in speed_screen({'root_positions':root},study)['flags']
    root[:,0]=0;root[:,2]*=1.2
    assert 'speed' in speed_screen({'root_positions':root},study)['flags']


def test_phase_distance_ignores_phase_and_root_translation_but_detects_pose_change():
    n=32;positions=np.zeros((n,77,3));positions[:,12,1]=np.sin(np.arange(n)*2*np.pi/n)
    root=np.column_stack([np.zeros(n),np.zeros(n),np.arange(n)*.1])
    rotations=np.broadcast_to(np.eye(3),(n,77,3,3)).copy()
    a={'posed_joints':positions+root[:,None],'root_positions':root,'global_rot_mats':rotations}
    b={'posed_joints':np.roll(positions,8,axis=0)+(root+10)[:,None],'root_positions':root+10,'global_rot_mats':rotations}
    assert phase_distance(canonical_cycle(a),canonical_cycle(b))<1e-6
    b['posed_joints'][:,12,0]+=.2
    assert phase_distance(canonical_cycle(a),canonical_cycle(b))>.01
