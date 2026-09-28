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
