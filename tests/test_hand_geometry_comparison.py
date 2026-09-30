import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_geometry_comparison import compare,load_warm_geometry
from strep import save,sha256


def row(sample,a,b):
    return dict(sample=sample,time_s=sample/120,directions=[
        dict(max_depth_m=v,vertices_checked=3,source_full_vertex_count=8) for v in [a,b]])


def test_lower_pair_peak_cannot_hide_opposite_direction_regression_or_extra_times():
    old=[row(2,.02,.001),row(3,.001,.002)]
    new=[row(1,.03,.001),row(2,.015,.009),row(3,.003,.006)]
    result=compare(old,new)
    assert result['compared_samples']==2 and result['uncompared_candidate_samples']==[1]
    assert result['reference_peak_m']==.02 and result['candidate_peak_m']==.015
    assert result['new_failed_samples']==[3]
    assert result['maximum_sample_increase_m']==pytest.approx(.004)
    assert result['maximum_directional_increase_m']==pytest.approx(.008)
    assert result['direction_observations_worsened']==3


@pytest.mark.parametrize('fault',['duplicate','time','missing','direction','hand_count','full_count','nan','negative'])
def test_comparison_rejects_incompatible_or_incomplete_measurements(fault):
    old=[row(2,.02,.001)];new=copy.deepcopy(old)
    if fault=='duplicate':new.append(copy.deepcopy(new[0]))
    if fault=='time':new[0]['time_s']+=1e-10
    if fault=='missing':new=[row(3,.02,.001)]
    if fault=='direction':new[0]['directions'].pop()
    if fault=='hand_count':new[0]['directions'][0]['vertices_checked']=4
    if fault=='full_count':new[0]['directions'][0]['source_full_vertex_count']=9
    if fault=='nan':new[0]['directions'][0]['max_depth_m']=float('nan')
    if fault=='negative':new[0]['directions'][0]['max_depth_m']=-.001
    with pytest.raises(ValueError):compare(old,new)


@pytest.mark.parametrize('fault',[None,'unbound','geometry','incomplete_clock','incomplete_study'])
def test_warm_geometry_uses_declared_donor_and_bound_complete_mesh_evidence(tmp_path,fault):
    save(tmp_path/'request.json',dict(hand_samples=[2,3]))
    geometry=[row(2,.02,.001),row(3,.001,.002)]
    if fault=='incomplete_clock':geometry=geometry[:1]
    save(tmp_path/'geometry.json',geometry)
    save(tmp_path/'result.json',dict(status='running' if fault=='incomplete_study' else 'complete',
        request_sha256=sha256(tmp_path/'request.json'),geometry_sha256=sha256(tmp_path/'geometry.json')))
    files={str(tmp_path/(name+'.json')):sha256(tmp_path/(name+'.json')) for name in ['request','result']}
    if fault=='geometry':save(tmp_path/'geometry.json',[row(2,0.,0.),row(3,0.,0.)])
    if fault=='unbound':files={}
    request=dict(warm_start_study=str(tmp_path))
    if fault:
        with pytest.raises(ValueError):load_warm_geometry(request,files)
    else:
        rows,bound=load_warm_geometry(request,files)
        assert rows==geometry and bound[str(tmp_path/'geometry.json')]==sha256(tmp_path/'geometry.json')
