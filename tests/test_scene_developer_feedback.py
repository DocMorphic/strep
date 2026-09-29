"""Synthetic observations only; no human-review evidence is created."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_developer_feedback as feedback
from gltf_tools import write_glb
from strep import save,sha256,read


@pytest.fixture
def packet(tmp_path,monkeypatch):
    monkeypatch.setattr(feedback,'ROOT',tmp_path)
    folder=tmp_path/'reports/scene-region-jobs/synthetic';folder.mkdir(parents=True)
    actors={};bindings=[]
    for name in ['A','B']:
        clip=folder/(name+'.glb')
        write_glb(clip,dict(asset={'version':'2.0'},buffers=[dict(byteLength=4)]),b'\0'*4)
        actors[name]=dict(preview_glb=clip.name)
        bindings.append(dict(actor=name,glb_url='/files/scene-region-jobs/synthetic/'+clip.name,glb_sha256=sha256(clip)))
    bundle=folder/'candidate.json'
    save(folder/'manifest.json',dict(scenes=[dict(variants={'palm':'candidate.json'})]))
    save(bundle,dict(scene=dict(id='synthetic',fps=30,frame_count=120,actors=actors,objects={'box':{'position':[0,0,0]}})))
    data=dict(schema='strep-scene-observation-v1',created_at='2026-09-29T00:00:00Z',reviewer_id='Synthetic fixture',notes='Synthetic test only.',review_type='non_blind_developer',independent_human=False,cleanup_test_performed=False,quality_approved=False,frame_range=dict(start=0,end_inclusive=119),source=dict(bundle_url='/files/scene-region-jobs/synthetic/candidate.json',bundle_sha256=sha256(bundle),scene_id='synthetic',frames=120,fps=30,actors=bindings))
    data['source']['collection_url']='/files/scene-region-jobs/synthetic/'
    return bundle,data


def test_scene_import_preserves_user_observation_without_approval(packet,tmp_path):
    bundle,data=packet;response=tmp_path/'response.json';save(response,data)
    result=feedback.import_feedback(bundle,response,tmp_path/'imported')
    assert result['valid'] and not result['quality_approved'] and not result['independent_review']
    assert read(tmp_path/'imported/observation.json')==data
    with pytest.raises(ValueError,match='Preserve'):feedback.import_feedback(bundle,response,tmp_path/'imported')


def test_nested_bundle_uses_collection_relative_actor_paths(packet):
    bundle,data=packet;folder=bundle.parent
    nested=folder/'nested/candidate.json';nested.parent.mkdir();bundle.rename(nested)
    save(folder/'manifest.json',dict(scenes=[dict(variants={'palm':'nested/candidate.json'})]))
    data['source']['bundle_url']='/files/scene-region-jobs/synthetic/nested/candidate.json'
    assert feedback.validate(data,nested)['valid']


@pytest.mark.parametrize('change',['object','partner','missing_partner','scene_id','bundle_hash','frame','boolean_frame','approval','independent','cleanup','blank','time','escape','external_buffer'])
def test_stale_scene_or_invalid_claims_rejected(packet,change):
    bundle,data=packet;data=copy.deepcopy(data)
    if change=='object':
        saved=read(bundle);saved['scene']['objects']['box']['position'][0]=1;save(bundle,saved)
    if change=='partner':
        write_glb(bundle.parent/'B.glb',dict(asset={'version':'2.0'},buffers=[dict(byteLength=4)]),b'1234')
    if change=='missing_partner':data['source']['actors'].pop()
    if change=='scene_id':data['source']['scene_id']='other'
    if change=='bundle_hash':data['source']['bundle_sha256']='0'*64
    if change=='frame':data['frame_range']['end_inclusive']=120
    if change=='boolean_frame':data['frame_range']['start']=False
    if change in ['approval','independent','cleanup']:
        data[dict(approval='quality_approved',independent='independent_human',cleanup='cleanup_test_performed')[change]]=True
    if change=='blank':data['notes']=' '
    if change=='time':data['created_at']='2026-09-29'
    if change=='escape':
        saved=read(bundle);saved['scene']['actors']['A']['preview_glb']='../A.glb';save(bundle,saved)
    if change=='external_buffer':
        write_glb(bundle.parent/'A.glb',dict(asset={'version':'2.0'},buffers=[dict(byteLength=4,uri='outside.bin')]),b'1234')
    with pytest.raises(ValueError):feedback.validate(data,bundle)
