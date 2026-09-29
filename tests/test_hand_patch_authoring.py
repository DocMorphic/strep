import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read
from build_soma_preview import ASSET
from scene_region_job import metadata,validate,prepare,JOBS
from hand_patch_authoring import hand_mesh,custom_patch


@pytest.fixture(scope='module')
def payload():
    data=metadata('/files/scene-region-jobs/development-region-sources-v1/sphere.json')
    contacts=[]
    for c in data['contacts']:
        edit=copy.deepcopy(c['edit'])
        edit.update(patch_mode='custom',patch_face_ids=c['patch_face_ids'],patch_mesh_sha256=c['hand_mesh']['mesh_sha256'])
        contacts.append(edit)
    return dict(source_url=data['source_url'],revision=data['revision'],actor='A',label='Custom hand test',contacts=contacts)


def test_custom_selection_preserves_declared_faces_and_source(payload):
    source,scene,ids=validate(copy.deepcopy(payload))
    assert read(source['path'])==source['bundle']
    for c in scene['contacts']:
        edit=next(e for e in payload['contacts'] if e['id']==c['id'])
        assert c['region_contact']['face_ids']==sorted(edit['patch_face_ids'])
        assert c['region_contact']['mesh_sha256']==edit['patch_mesh_sha256']


@pytest.mark.parametrize('fault',['mesh','wrong_hand','body','duplicate','empty','negative','out_of_range','bool','too_large'])
def test_custom_selection_rejects_wrong_or_unsafe_identity(payload,fault):
    p=copy.deepcopy(payload);e=p['contacts'][0];skin=dict(np.load(ASSET,allow_pickle=False))
    if fault=='mesh':e['patch_mesh_sha256']='stale'
    elif fault=='wrong_hand':e['patch_face_ids']=[hand_mesh(skin,'RightHand')['faces'][0]['id']]
    elif fault=='body':e['patch_face_ids']=[0]
    elif fault=='duplicate':e['patch_face_ids']*=2
    elif fault=='empty':e['patch_face_ids']=[]
    elif fault=='negative':e['patch_face_ids']=[-1]
    elif fault=='out_of_range':e['patch_face_ids']=[len(skin['faces'])]
    elif fault=='bool':e['patch_face_ids']=[True]
    else:e['patch_face_ids']=[f['id'] for f in hand_mesh(skin,'LeftHand')['faces']]
    with pytest.raises(ValueError):validate(p)


def test_anchor_is_rebound_inside_a_changed_patch(payload):
    skin=dict(np.load(ASSET,allow_pickle=False));source,scene,_=validate(payload)
    contact=scene['contacts'][0];edit=copy.deepcopy(payload['contacts'][0]);old=contact['effector']['surface_vertex']
    f=next(f for f in hand_mesh(skin,'LeftHand')['faces'] if old not in f['vertices'])
    edit['patch_face_ids']=[f['id']]
    binding,anchor=custom_patch(skin,contact,edit)
    assert anchor in f['vertices'] and anchor!=old
