import sys
from pathlib import Path
from unittest.mock import patch
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from complete_scene_region_study import owner_live


def test_reused_pid_does_not_wait_on_unrelated_process():
    with patch('complete_scene_region_study.psutil.Process') as process:
        process.return_value.is_running.return_value=True
        process.return_value.create_time.return_value=200.
        assert owner_live(123,100.) is False
        assert owner_live(123,200.) is True


def test_missing_owner_is_terminal():
    with patch('complete_scene_region_study.psutil.Process',side_effect=psutil.NoSuchProcess(123)):
        assert owner_live(123,100.) is False
