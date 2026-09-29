import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_scene_runtime import automatic_clock_passed


def test_short_clock_finishes_after_exact_required_number_of_updates():
    assert automatic_clock_passed(np.arange(1,7)/60,.1,1/60)
    assert automatic_clock_passed([2/30,1/30,0],.1,1/30,True)
    assert not automatic_clock_passed([2/30,1/30,6.94e-18,0],.1,1/30,True)
    assert not automatic_clock_passed([2/30,1/30],.1,1/30,True)
    assert not automatic_clock_passed(np.arange(1,6)/60,.1,1/60)


def test_long_clock_requires_correct_origin_rate_and_enough_observations():
    assert automatic_clock_passed(np.arange(1,14)/60,30,1/60)
    assert automatic_clock_passed(30-np.arange(1,15)/30,30,1/30,True)
    assert not automatic_clock_passed(np.arange(2,15)/60,30,1/60)
    assert not automatic_clock_passed(np.arange(1,10)/60,30,1/60)
    assert not automatic_clock_passed(np.arange(1,15)/30,30,1/60)


def test_partial_last_step_clamps_to_exact_endpoint():
    assert automatic_clock_passed([.04,.08,.11],.11,.04)
    assert automatic_clock_passed([.07,.03,0],.11,.04,True)
    assert not automatic_clock_passed([.04,.08,.12],.11,.04)
