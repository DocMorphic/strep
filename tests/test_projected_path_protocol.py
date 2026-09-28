import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from compare_projected_partner_path import matching_protocol


def fixtures():
    # Actual frozen study requests bind the test to the declared comparison.
    a=dict(request=read(ROOT/'reports/enriched-surface-path-v1/request.json'),initial=read(ROOT/'reports/enriched-surface-path-v1/initial-parameters.json'),variants={'raw':{'curve':{'sample':'same'}}},manifest={'assets':{f'assets/{actor}/raw/{name}':{'sha256':'same'} for actor in ['A','B'] for name in ['character.glb','motion.npz']}})
    b=copy.deepcopy(a);b['request']=read(ROOT/'reports/projected-surface-path-v1/request.json')
    return a,b


def test_frozen_comparison_protocol_matches():
    matching_protocol(*fixtures())


@pytest.mark.parametrize('field',['frames','selection_screen','iterations','restoration','joint_edit_degrees','sampling_plan'])
def test_rejects_changed_scope_limits_or_budget(field):
    a,b=fixtures();b['request'][field]='changed'
    with pytest.raises(ValueError,match='protocol differs'):matching_protocol(a,b)


def test_rejects_changed_initialization_or_raw_geometry():
    a,b=fixtures();b['initial']={}
    with pytest.raises(ValueError,match='Initial parameters'):matching_protocol(a,b)
    a,b=fixtures();b['variants']['raw']['curve']={}
    with pytest.raises(ValueError,match='Raw full-clock'):matching_protocol(a,b)
