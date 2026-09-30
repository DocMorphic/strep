import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pair_activity import matches_study
from strep import ROOT


def test_only_exact_workspace_study_process_matches():
    assert matches_study(dict(cmdline=['python',str(ROOT/'scripts/study_scene_pair_fit.py'),'input','output'],cwd=str(ROOT)))
    assert matches_study(dict(cmdline=['python','scripts/study_scene_pair_fit.py','input','output'],cwd=str(ROOT)))
    assert not matches_study(dict(cmdline=['python','scripts/study_scene_pair_fit.py'],cwd=str(ROOT.parent)))
    assert not matches_study(dict(cmdline=['python','another.py','study_scene_pair_fit.py'],cwd=str(ROOT)))
    assert not matches_study(dict(cmdline=None,cwd=None))
