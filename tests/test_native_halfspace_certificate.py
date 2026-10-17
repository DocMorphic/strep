"""Independent algebraic fixtures and tamper rejection for proxy certificates."""
import copy,json,math,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_halfspace_certificate import SCHEMA,region_digest,verify


def fixture():
    regions=[dict(vertices=[42],normal_world=[1.,0.,0.],offset_m=0.,sign=-1,minimum_gap_m=0.),dict(vertices=[42],normal_world=[1.,0.,0.],offset_m=1.,sign=1,minimum_gap_m=0.)]
    certificate=dict(schema=SCHEMA,regions_sha256=region_digest(regions),vertex=42,support=[dict(region_index=i,weight_rational='1/2') for i in [0,1]])
    return regions,certificate


def test_two_opposing_requirements_prove_zero_is_at_most_negative_half():
    regions,certificate=fixture();before=copy.deepcopy((regions,certificate));result=verify(regions,certificate)
    assert result['weighted_normal_rational']==['0','0','0'] and result['weighted_bound_rational']=='-1/2'
    assert result['sum_weights_rational']=='1' and result['contradiction_established'] and not result['quality_approved']
    assert (regions,certificate)==before


def test_four_plane_tetrahedral_contradiction_uses_exact_binary_constants():
    q=1/math.sqrt(3);regions=[dict(vertices=[7],normal_world=axis,offset_m=offset,sign=-1,minimum_gap_m=0.) for axis,offset in [([1.,0,0],0.),([0,1.,0],0.),([0,0,1.],0.),([-q,-q,-q],-1.)]]
    exact=F(q);denominator=1+3*exact;weights=[exact/denominator]*3+[1/denominator]
    certificate=dict(schema=SCHEMA,regions_sha256=region_digest(regions),vertex=7,support=[dict(region_index=i,weight_rational=str(w)) for i,w in enumerate(weights)])
    result=verify(regions,certificate);assert F(result['weighted_bound_rational'])==-1/denominator


@pytest.mark.parametrize('change',['digest','vertex','index','duplicate','negative_weight','nonunit_sum','nonzero_normal','zero_division','decimal_weight','long_weight','extra_field','bool_vertex'])
def test_invalid_or_tampered_certificate_rejects(change):
    regions,certificate=fixture()
    if change=='digest':certificate['regions_sha256']='0'*64
    elif change=='vertex':certificate['vertex']=1
    elif change=='index':certificate['support'][0]['region_index']=2
    elif change=='duplicate':certificate['support'][1]['region_index']=0
    elif change=='negative_weight':certificate['support'][0]['weight_rational']='-1/2'
    elif change=='nonunit_sum':certificate['support'][0]['weight_rational']='1/3'
    elif change=='nonzero_normal':certificate['support'][0]['weight_rational']='1/4';certificate['support'][1]['weight_rational']='3/4'
    elif change=='zero_division':certificate['support'][0]['weight_rational']='1/0'
    elif change=='decimal_weight':certificate['support'][0]['weight_rational']='0.5'
    elif change=='long_weight':certificate['support'][0]['weight_rational']='1'*4097
    elif change=='extra_field':certificate['accepted']=True
    else:certificate['vertex']=True
    with pytest.raises(ValueError):verify(regions,certificate)


@pytest.mark.parametrize('offset',[0.,-1.])
def test_feasible_or_touching_requirements_do_not_certify_infeasibility(offset):
    regions,certificate=fixture();regions[1]['offset_m']=offset;certificate['regions_sha256']=region_digest(regions)
    with pytest.raises(ValueError):verify(regions,certificate)


def test_changed_unselected_region_also_invalidates_complete_request_binding():
    regions,certificate=fixture();regions.append(dict(vertices=[9],normal_world=[0.,1.,0.],offset_m=0.,sign=1,minimum_gap_m=0.));certificate['regions_sha256']=region_digest(regions)
    assert verify(regions,certificate)['contradiction_established'];regions[-1]['offset_m']=.001
    with pytest.raises(ValueError):verify(regions,certificate)


@pytest.mark.parametrize('change',['normal','gap','sign','vertices','bool_normal','nonfinite','huge_normal','huge_offset','total_vertex_budget'])
def test_invalid_region_requests_reject(change):
    regions,certificate=fixture()
    if change=='normal':regions[0]['normal_world']=[2.,0,0]
    elif change=='gap':regions[0]['minimum_gap_m']=-.1
    elif change=='sign':regions[0]['sign']=True
    elif change=='vertices':regions[0]['vertices']=[42,42]
    elif change=='bool_normal':regions[0]['normal_world']=[True,0,0]
    elif change=='nonfinite':regions[0]['offset_m']=float('nan')
    elif change=='huge_normal':regions[0]['normal_world']=[10**1000,0,0]
    elif change=='huge_offset':regions[0]['offset_m']=10**1000
    else:regions[0]['vertices']=list(range(100001))
    with pytest.raises(ValueError):verify(regions,certificate)


def test_portable_cli_verifies_json_without_loading_models(tmp_path):
    regions,certificate=fixture();a=tmp_path/'regions.json';b=tmp_path/'certificate.json';a.write_text(json.dumps(regions));b.write_text(json.dumps(certificate))
    result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/native_halfspace_certificate.py'),str(a),str(b)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['weighted_bound_rational']=='-1/2'
