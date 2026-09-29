import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_timing_job import validate_options,listing
from action_studio_server import validate_contact_request
from strep import ROOT


def request():
    return dict(collection='body-contact-v1',take_id='get-up-seed-11',
        contact_spec=dict(schema_version=1,fps=30,frame_count=180,regions={'LeftFoot':dict(mode='explicit',segments=[
            dict(start_frame=30,end_frame=149,space='world',position_m=[0.,.002,0.])])}),timing_check=dict(edit_window=[20,159]))


def test_existing_source_api_accepts_explicit_check_without_changing_spec():
    payload=request();original=copy.deepcopy(payload)
    source,spec=validate_contact_request(payload)
    assert source==ROOT/'reports/body-contact-v1/takes/get-up-seed-11'
    assert spec==original['contact_spec'] and payload==original


@pytest.mark.parametrize('window',[[0,159],[20,179],[30,159],[20,149],[True,159],[159,20]])
def test_nonheld_or_noncontaining_window_rejected(window):
    payload=request();payload['timing_check']['edit_window']=window
    with pytest.raises(ValueError):validate_contact_request(payload)


def test_unknown_check_options_and_nonstationary_target_rejected():
    p=request();p['timing_check']['allow_incompatible']=True
    with pytest.raises(ValueError):validate_contact_request(p)
    p=request();pin=p['contact_spec']['regions']['LeftFoot']['segments'][0];pin['space']='baseline';pin.pop('position_m')
    with pytest.raises(ValueError):validate_contact_request(p)


def test_listing_keeps_check_separate_from_animation_and_links_bound_points():
    state=dict(kind='timing_check',status='needs_authoring_change',message='Three conflicts',source='source/takes/a')
    data=listing(ROOT/'reports/contact-jobs/example',state)
    assert data['kind']=='contact_check' and data['timing_message']=='Three conflicts'
    assert data['bound_contacts']=='/files/contact-jobs/example/bound-contact-spec.json'
    assert 'ready' not in data and listing(ROOT/'reports/contact-jobs/example',{'status':'complete'})=={}


def test_changed_snapshot_is_rejected_before_measurement(tmp_path):
    from contact_timing_job import prepare,run
    p=request();source,spec=validate_contact_request(p);folder=tmp_path/'check'
    prepare(source,spec,p['timing_check'],folder)
    (folder/'contact-spec.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='Frozen check inputs changed'):run(folder)


def test_encoded_weight_change_is_rejected_even_if_decoded_skin_is_valid(monkeypatch):
    import numpy as np
    import gltf_tools
    from build_soma_preview import ASSET
    from contact_timing_job import verify_source
    source=ROOT/'reports/body-contact-v1/takes/get-up-seed-11'
    original=gltf_tools.accessor
    def changed(*args,**kwargs):
        value=original(*args,**kwargs).copy();value.flat[0]+=.000001;return value
    monkeypatch.setattr(gltf_tools,'accessor',changed)
    with pytest.raises(ValueError,match='Encoded preview weights'):
        verify_source(source/'soma.glb',dict(np.load(source/'motion.npz')),dict(np.load(ASSET)))
