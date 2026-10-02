"""Native packing fixtures; complete labels here are numerical, not human review."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from safetensors import safe_open
from safetensors.torch import load_file

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save,read,sha256
import pack_native_correction as packer

NAMES=[f'Joint{i}' for i in range(77)]


def channels(frames=3):
    return [{'joint':joint,'intervals':[{'start_frame':0,'end_frame_exclusive':frames,'contact':False}]} for joint in packer.CONTACT_JOINTS]


@pytest.fixture
def fixture(tmp_path):
    raw=tmp_path/'original.npz'
    local=np.repeat(np.eye(3,dtype=np.float32)[None,None],5,axis=0).repeat(77,axis=1)
    roots=np.arange(15,dtype=np.float32).reshape(5,3)/10
    contacts=np.zeros((5,6),dtype=np.float32);contacts[1:3,0]=1
    np.savez_compressed(raw,local_rot_mats=local,root_positions=roots,foot_contacts=contacts)
    preview=tmp_path/'soma.glb';preview.write_bytes(b'Fixture preview, not actual GLB')
    draft=tmp_path/'draft.json'
    save(draft,{'schema':'strep-native-target-review-draft-v1','training_admitted':False,
                'items':[{'id':'sample','fps':30,'source_start_frame':1,'source_end_frame_exclusive':4,
                          'source_motion':str(raw),'source_motion_sha256':sha256(raw),
                          'source_preview':str(preview),'source_preview_sha256':sha256(preview)}]})
    recipe_dir=tmp_path/'recipe'
    packer.template(draft,'sample',recipe_dir,NAMES)
    return dict(root=tmp_path,raw=raw,local=local,roots=roots,draft=draft,recipe=recipe_dir/'recipe.json')


def fill(f):
    value=read(f['recipe']);value['contacts']=channels()
    value['contacts'][0]['intervals']=[{'start_frame':0,'end_frame_exclusive':2,'contact':True},
                                     {'start_frame':2,'end_frame_exclusive':3,'contact':False}]
    save(f['recipe'],value)


def test_template_never_copies_predicted_contacts_into_the_annotation(fixture):
    f=fixture;recipe=read(f['recipe']);suggestions=read(f['recipe'].parent/'model-suggestions.json')
    assert all(row['intervals'][0]['contact'] is None for row in recipe['contacts'])
    assert suggestions['contacts'][0]['intervals']==[{'start_frame':0,'end_frame_exclusive':2,'contact':True},
                                                    {'start_frame':2,'end_frame_exclusive':3,'contact':False}]
    with pytest.raises(ValueError,match='Unreviewed'):
        packer.pack(f['recipe'],f['root']/'invalid',NAMES)
    assert not (f['root']/'invalid').exists()


def test_packed_geometry_labels_and_evidence_exact_but_review_rights_pending(fixture):
    f=fixture;fill(f);before=sha256(f['raw']);output=f['root']/'packed'
    result=packer.pack(f['recipe'],output,NAMES)
    values=load_file(str(output/'correction.safetensors'))
    assert torch.equal(values['local_rotations'],torch.from_numpy(f['local'][1:4]))
    assert torch.equal(values['root_positions'],torch.from_numpy(f['roots'][1:4]))
    assert values['foot_contacts'][:,0].tolist()==[True,True,False]
    assert not values['foot_contacts'][:,1:].any()
    assert result['frames']==3 and result['candidate_start_frame']==1
    assert result['training_admitted'] is result['quality_approved'] is result['release_approved'] is False
    assert result['correction']['sha256']==sha256(output/'correction.safetensors')
    assert read(output/'rights-unreviewed.json')['permitted'] is None
    assert read(output/'review-row-unreviewed.json')['decision']=='unreviewed'
    with safe_open(str(output/'correction.safetensors'),framework='pt') as archive:
        metadata=archive.metadata()
    assert json.loads(metadata['joint_names'])==NAMES
    assert json.loads(metadata['contact_joints'])==packer.CONTACT_JOINTS
    assert metadata['fps']=='30' and metadata['coordinates']=='right-handed-Y-up'
    for path,copied in result['archived_evidence'].items():
        assert sha256(output/copied)==result['inputs_sha256'][path]
    assert sha256(f['raw'])==before
    with pytest.raises(ValueError,match='Fresh correction'):
        packer.pack(f['recipe'],output,NAMES)


@pytest.mark.parametrize('intervals',[
    [{'start_frame':1,'end_frame_exclusive':3,'contact':True}],
    [{'start_frame':0,'end_frame_exclusive':1,'contact':True},{'start_frame':2,'end_frame_exclusive':3,'contact':False}],
    [{'start_frame':0,'end_frame_exclusive':2,'contact':True},{'start_frame':1,'end_frame_exclusive':3,'contact':False}],
    [{'start_frame':0,'end_frame_exclusive':4,'contact':True}],
    [{'start_frame':0,'end_frame_exclusive':2,'contact':True}],
    [{'start_frame':0,'end_frame_exclusive':3,'contact':1}],
    [{'start_frame':False,'end_frame_exclusive':3,'contact':True}],
])
def test_contact_clock_cannot_have_gaps_overlaps_unknown_numeric_or_missing_states(intervals):
    contacts=channels();contacts[0]['intervals']=intervals
    with pytest.raises(ValueError):packer.contacts_from_intervals(contacts,3)


def test_contact_channel_order_is_required():
    contacts=list(reversed(channels()))
    with pytest.raises(ValueError,match='Ordered foot'):
        packer.contacts_from_intervals(contacts,3)


@pytest.mark.parametrize('field,value',[('fps',60),('units','centimetres'),('coordinates','Z-up'),('joint_names',list(reversed(NAMES)))])
def test_wrong_clock_units_axes_or_joint_order_rejected(fixture,field,value):
    f=fixture;fill(f);recipe=read(f['recipe']);recipe[field]=value;save(f['recipe'],recipe)
    with pytest.raises(ValueError,match='Pinned native'):
        packer.pack(f['recipe'],f['root']/'wrong',NAMES)


def test_replaced_candidate_without_updated_hash_is_rejected(fixture):
    f=fixture;fill(f);f['raw'].write_bytes(f['raw'].read_bytes()+b'changed')
    with pytest.raises(ValueError,match='changed'):
        packer.pack(f['recipe'],f['root']/'stale',NAMES)


@pytest.mark.parametrize('failure',['rotations','nan','dtype','too_short'])
def test_candidate_geometry_is_checked_before_publication(fixture,failure):
    f=fixture;fill(f)
    candidate=f['root']/'edited.npz';local=f['local'].copy();roots=f['roots'].copy()
    if failure=='rotations':local[1,0,0,0]=2
    elif failure=='nan':roots[1,0]=np.nan
    elif failure=='dtype':local=local.astype(np.float64)
    else:local=local[:2];roots=roots[:2]
    np.savez_compressed(candidate,local_rot_mats=local,root_positions=roots)
    recipe=read(f['recipe']);recipe['candidate_motion']={'path':str(candidate),'sha256':sha256(candidate)};save(f['recipe'],recipe)
    with pytest.raises(ValueError):packer.pack(f['recipe'],f['root']/'badgeometry',NAMES)
    assert not (f['root']/'badgeometry').exists()


def test_edited_candidate_uses_explicit_independent_window(fixture):
    f=fixture;candidate=f['root']/'edited.npz';changed=f['roots'][1:4]+1
    np.savez_compressed(candidate,local_rot_mats=f['local'][1:4],root_positions=changed)
    with pytest.raises(ValueError,match='explicit matching-window'):
        packer.template(f['draft'],'sample',f['root']/'missing-window',NAMES,candidate=candidate)
    packer.template(f['draft'],'sample',f['root']/'edited-recipe',NAMES,candidate=candidate,candidate_start=0)
    recipe=f['root']/'edited-recipe/recipe.json';value=read(recipe);value['contacts']=channels();save(recipe,value)
    result=packer.pack(recipe,f['root']/'edited-pack',NAMES)
    assert result['original_start_frame']==1 and result['candidate_start_frame']==0
    values=load_file(result['correction']['path'])
    assert torch.equal(values['root_positions'],torch.from_numpy(changed))
