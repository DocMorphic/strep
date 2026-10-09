"""Prevent rebuilding Studio from silently discarding shipped editor features."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_desktop import ROOT, render
from html.parser import HTMLParser
from collections import Counter


def test_checked_in_studio_matches_its_editable_sources():
    assert render()==(ROOT/'scripts/action-studio.html').read_text(encoding='utf8')


def test_rebuild_retains_resource_deferral_and_saved_request_retry():
    page=render()
    assert page.count("renderJobList($('jobList'),studies,busy")==1
    assert "from '/generation-job-status.mjs'" in page
    assert 'activityMessage(studies,busy)' in page
    assert "json('/api/jobs/retry'" in page and 'JSON.stringify({job:id})' in page
    assert 'const active=data.studies.find(s=>activeGenerationStatus(s.status))' in page
    assert 'generationJobMessage(job)' in page


def test_rebuild_retains_scene_region_editor_and_grip_picker():
    page=render()
    assert 'id="sceneRegionStatus"' in page
    assert 'const regionEditor=createSceneRegionEditor(' in page
    assert 'const gripPicker=createSceneGripPicker(' in page
    assert 'await regionEditor.bind(' in page
    assert 'gripPicker.cancel();' in page


def test_scene_feedback_controls_have_unambiguous_dom_ids():
    class IDs(HTMLParser):
        def __init__(self):super().__init__();self.ids=[]
        def handle_starttag(self,tag,attrs):self.ids.extend(value for key,value in attrs if key=='id')
    parser=IDs();parser.feed(render());counts=Counter(parser.ids)
    assert not [name for name,count in counts.items() if count>1]
    for name in ['sceneFeedbackFields','sceneReviewNote','sceneExportFeedback','sceneNoteStart','sceneNoteEnd']:
        assert counts[name]==1
