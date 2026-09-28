import json
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_prepared_contact_trajectory import load_plan
from strep import ROOT


@pytest.fixture
def plan(tmp_path):
    source=ROOT/'reports/knee-hold-pilot-plan-v1'
    for name in ['protocol.json','spec.json','prepared.npz']:
        shutil.copyfile(source/name,tmp_path/name)
    return tmp_path


def test_changed_prepared_trajectory_is_rejected(plan):
    with (plan/'prepared.npz').open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='Prepared data or contract changed'):load_plan(plan)


@pytest.mark.parametrize('frames',[[0,60,61],[60,60,61],[60,179]])
def test_invalid_edit_windows_are_rejected(plan,frames):
    path=plan/'protocol.json';protocol=json.loads(path.read_text());protocol['frames']=frames
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError,match='sorted unique interior keys'):load_plan(plan)


def test_declared_window_cannot_silently_omit_masked_frames(plan):
    path=plan/'protocol.json';protocol=json.loads(path.read_text());protocol['frames']=list(range(48,103))
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError,match='Editable mask differs'):load_plan(plan)
