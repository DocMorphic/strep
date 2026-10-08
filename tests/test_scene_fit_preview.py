import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_scene_fit import preview_asset


def test_saved_collection_preview_and_missing_or_escaping_assets(tmp_path):
    collection=tmp_path/'collection';collection.mkdir()
    asset=collection/'actor.glb';asset.write_bytes(b'fixture')
    assert preview_asset(dict(preview_glb='actor.glb'),collection)==asset
    outside=tmp_path/'outside.glb';outside.write_bytes(b'fixture')
    with pytest.raises(ValueError,match='escapes'):preview_asset(dict(preview_glb='../outside.glb'),collection)
    with pytest.raises(ValueError,match='missing'):preview_asset(dict(preview_glb='missing.glb'),collection)


@pytest.mark.parametrize('preserve_body',[False,True])
def test_passing_preflight_directory_hands_exact_assets_to_preprocessing(tmp_path,monkeypatch,preserve_body):
    import numpy as np
    import run_scene_fit as fit
    from strep import save,read,sha256
    skin=tmp_path/'skin.npz'
    np.savez(skin,bind_rig_transform=np.repeat(np.eye(4)[None],77,axis=0),
        bind_vertices=np.zeros((1,3)),lbs_indices=np.zeros((1,8),dtype=int),
        lbs_weights=np.array([[1.,0,0,0,0,0,0,0]]))
    raw=tmp_path/'motion.npz'
    np.savez(raw,posed_joints=np.zeros((4,77,3)),global_rot_mats=np.broadcast_to(np.eye(3),(4,77,3,3)))
    preview=tmp_path/'actor.glb';preview.write_bytes(b'preserved fixture GLB')
    scene=tmp_path/'scene.json'
    save(scene,dict(id='fixture',frame_count=4,actors={'A':dict(motion=str(raw),preview_glb='actor.glb')},objects={},contacts=[]))
    spec=dict(frame_count=4,regions={'LeftHand':dict(mode='explicit',segments=[
        dict(start_frame=1,end_frame=2,space='world',vertex_id=0,position_m=[0,0,0],tolerance_m=.03)])})
    monkeypatch.setattr(fit,'ASSET',skin);monkeypatch.setattr(fit,'SOMASkeleton77',lambda:object())
    monkeypatch.setattr(fit,'compile_contacts',lambda *args:(spec,{}))
    monkeypatch.setattr(fit,'scene_evaluate',lambda *args:dict(contacts=[],object_collisions=[]))
    def reached(*args):raise RuntimeError('Reached preprocessing with saved assets')
    monkeypatch.setattr(fit,'floor_correct',reached)
    output=tmp_path/'study'
    with pytest.raises(RuntimeError,match='Reached preprocessing'):
        fit.run([scene],output,17,tmp_path,preserve_body=preserve_body)
    assets=output/'assets/fixture/A'
    assert sha256(assets/'raw-motion.npz')==sha256(raw)
    assert (assets/'raw.glb').read_bytes()==preview.read_bytes()
    assert read(output/'pipeline.json')['status']=='failed'
    assert (output/'fixture/before.json').is_file()
    assert not (assets/'motion.npz').exists()
    if preserve_body:
        assert read(assets/'body-reach-preflight.json')['status']=='not_proven_incompatible'
    else:
        assert not (assets/'body-reach-preflight.json').exists()
