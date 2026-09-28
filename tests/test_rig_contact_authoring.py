import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rig_contact_authoring as author
from strep import ROOT,read,sha256

SOURCE='20260926-185422-40a6c246'


def payload(variant='transfer'):
    data=author.metadata(SOURCE,variant)
    return dict(source_job=SOURCE,variant=variant,spec=data['spec'])


def test_contact_metadata_maps_every_primitive_and_exact_version():
    a,b=author.metadata(SOURCE,'transfer'),author.metadata(SOURCE,'corrected')
    assert a['glb_sha256']!=b['glb_sha256'] and a['frames']==120
    assert sum(p['vertices'] for p in a['primitives'])==a['vertex_count']
    assert a['primitives'][0]['vertex_offset']==0
    assert all(set(p)=={'vertices'} for p in a['spec']['patches'].values())
    assert {'Head','Chest','LeftHand'} <= {j['label'] for j in a['editable_joints']}


@pytest.mark.parametrize('fault',['source','variant','hash','root','vertex','overlap','threshold','too_many_joints'])
def test_contact_authoring_rejects_invalid_or_misbound_drafts(fault):
    p=payload()
    if fault=='source':p['source_job']='../../models'
    if fault=='variant':p['variant']='../../source'
    if fault=='hash':p['spec']['glb_sha256']='0'*64
    if fault=='root':p['spec']['root_node']=0
    if fault=='vertex':next(iter(p['spec']['patches'].values()))['vertices']=[999999]
    if fault=='overlap':p['spec']['contacts'].append(copy.deepcopy(p['spec']['contacts'][0]))
    if fault=='threshold':p['spec']['screen']['floor_depth_m']=100
    if fault=='too_many_joints':p['spec']['edit_joints']={str(i):dict(node=i,limit_degrees=25) for i in range(21)}
    with pytest.raises(ValueError):author.validate_request(p)


def test_edit_snapshots_selected_corrected_glb_and_preserves_parent(tmp_path):
    original=ROOT/'reports/rig-jobs'/SOURCE/'corrected/character.glb';digest=sha256(original)
    p=payload('corrected');folder=tmp_path/'new-edit';request=author.prepare(p,folder)
    assert sha256(folder/'transfer/character.glb')==digest==sha256(original)
    assert request['input_glb_sha256']==digest and request['kind']=='contact_edit'
    assert read(folder/'transfer/report.json')['source']==str((folder/'source/motion.npz').resolve())
    assert read(folder/'transfer/report.json')['glb_sha256']==digest
    assert request['authored_spec_sha256']==sha256(folder/'contact-spec.json')
    assert not (folder/'corrected').exists()
