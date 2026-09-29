"""Prevent rebuilding Studio from silently discarding shipped editor features."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_desktop import ROOT, render


def test_checked_in_studio_matches_its_editable_sources():
    assert render()==(ROOT/'scripts/action-studio.html').read_text(encoding='utf8')


def test_rebuild_retains_scene_region_editor_and_grip_picker():
    page=render()
    assert 'id="sceneRegionStatus"' in page
    assert 'const regionEditor=createSceneRegionEditor(' in page
    assert 'const gripPicker=createSceneGripPicker(' in page
    assert 'await regionEditor.bind(' in page
    assert 'gripPicker.cancel();' in page
