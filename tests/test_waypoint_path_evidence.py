import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from waypoint_lattice import shortest_path
from waypoint_path_evidence import load_path


def fixture(root):
    times=np.array([1.,2.,3.]);states=np.array([[0.,0.,0.],[.04,15,-15]])
    costs=np.array([[0.,np.inf],[10.,0.],[0.,np.inf]])
    limits=[.8,300,300];parameters,report=shortest_path(times,states,costs,limits,.1)
    source=root/'source.dat';source.write_bytes(b'source');inputs={str(source):sha256(source)}
    request=dict(source_plan=str(root/'plan'),window_s=[1,2,3],inputs=inputs,implementation={},
        times_s=times.tolist(),states=states.tolist(),axes=dict(Xplus=[1.,0.,0.]),guide_rate_limits=limits,transition_weight=.1)
    save(root/'request.json',request)
    save(root/'routes.json',[dict(axis_name='Xplus',axis=[1.,0.,0.],parameters=parameters.tolist(),solver=report)])
    np.savez(root/'lattice.npz',states=states,times=times,costs=costs[None])
    save(root/'result.json',dict(status='complete',selected='Xplus',request_sha256=sha256(root/'request.json'),
        lattice_sha256=sha256(root/'lattice.npz'),routes_sha256=sha256(root/'routes.json')))
    return inputs


@pytest.mark.parametrize('fault',[None,'matrix','parameters','score','selection','population','source','window','snapshot'])
def test_binding_and_independent_search_replay(tmp_path,fault):
    inputs=fixture(tmp_path);result=read(tmp_path/'result.json')
    if fault=='matrix':(tmp_path/'lattice.npz').write_bytes(b'changed')
    if fault in ['parameters','score','population']:
        routes=read(tmp_path/'routes.json')
        if fault=='parameters':routes[0]['parameters'][1][0]=.02
        if fault=='score':routes[0]['solver']['total_cost']=0.
        if fault=='population':routes=[]
        save(tmp_path/'routes.json',routes);result['routes_sha256']=sha256(tmp_path/'routes.json')
    if fault=='selection':result['selected']='Yplus'
    if fault=='source':(tmp_path/'source.dat').write_bytes(b'changed')
    if fault in ['window','snapshot']:
        request=read(tmp_path/'request.json')
        if fault=='window':request['window_s']=[1,2,4]
        else:request['implementation']={'../source.dat':sha256(tmp_path/'source.dat')}
        save(tmp_path/'request.json',request);result['request_sha256']=sha256(tmp_path/'request.json')
    save(tmp_path/'result.json',result)
    if fault is None:
        guide,axis,route,files=load_path(tmp_path,tmp_path/'plan',[1,2,3],inputs)
        np.testing.assert_allclose(guide(1.5),[.02,7.5,-7.5]);np.testing.assert_array_equal(axis,[1,0,0])
        assert route['axis_name']=='Xplus' and str(tmp_path/'source.dat') in files
    else:
        with pytest.raises((ValueError,AssertionError)):load_path(tmp_path,tmp_path/'plan',[1,2,3],inputs)


@pytest.mark.parametrize('fault',[None,'missing','shifted','protected','unknown'])
def test_native_clock_recomputed_from_sources_and_guards(tmp_path,fault):
    inputs=fixture(tmp_path);window=[.8,2,3.3]
    request=read(tmp_path/'request.json');request['window_s']=window
    request['clock_mode']='native_shared' if fault!='unknown' else 'guessed'
    save(tmp_path/'request.json',request);result=read(tmp_path/'result.json')
    result['request_sha256']=sha256(tmp_path/'request.json');save(tmp_path/'result.json',result)
    clocks=[np.arange(5.)]*6;protected=[]
    if fault=='missing':clocks=None
    if fault=='shifted':clocks=[np.arange(5.)+.01]*6
    if fault=='protected':protected=[[2,2]]
    if fault is None:
        guide,_,_,_=load_path(tmp_path,tmp_path/'plan',window,inputs,native_clocks=clocks,protected=protected)
        np.testing.assert_array_equal(guide.times,[1,2,3])
    else:
        with pytest.raises((ValueError,AssertionError)):
            load_path(tmp_path,tmp_path/'plan',window,inputs,native_clocks=clocks,protected=protected)


@pytest.mark.parametrize('fault',[None,'authored','guard','peak','missing','policy'])
def test_full_interval_is_recomputed_from_bound_authored_request(tmp_path,fault):
    inputs=fixture(tmp_path);window=[.8,2,3.3];request=read(tmp_path/'request.json')
    request.update(window_s=window,clock_mode='native_shared',planning_interval_policy='guarded_precontact')
    if fault=='policy':request['planning_interval_policy']='unbounded'
    save(tmp_path/'request.json',request);result=read(tmp_path/'result.json')
    result['request_sha256']=sha256(tmp_path/'request.json');save(tmp_path/'result.json',result)
    authored=[.8,4];protected=[[3.3,3.3]];peak=2.
    if fault=='authored':authored=[.9,4]
    if fault=='guard':protected=[[3.1,3.1]]
    if fault=='peak':peak=2.1
    if fault=='missing':authored=None
    kwargs=dict(native_clocks=[np.arange(5.)]*6,protected=protected,authored_window=authored,peak_time=peak)
    if fault is None:
        guide,_,_,_=load_path(tmp_path,tmp_path/'plan',window,inputs,**kwargs)
        np.testing.assert_array_equal(guide.times,[1,2,3])
    else:
        with pytest.raises((ValueError,AssertionError)):load_path(tmp_path,tmp_path/'plan',window,inputs,**kwargs)


@pytest.mark.parametrize('fault',[None,'missing_route','forged_optimum','other_route_score'])
def test_explicit_route_audit_preserves_and_replays_original_optimum(tmp_path,fault):
    inputs=fixture(tmp_path);request=read(tmp_path/'request.json');routes=read(tmp_path/'routes.json')
    with np.load(tmp_path/'lattice.npz') as data:states=data['states'];times=data['times'];costs=data['costs'][0]
    alternative=costs+2
    parameters,report=shortest_path(times,states,alternative,request['guide_rate_limits'],.1)
    request['axes']['Zminus']=[0.,0.,-1.]
    routes.append(dict(axis_name='Zminus',axis=[0.,0.,-1.],parameters=parameters.tolist(),solver=report))
    if fault=='other_route_score':routes[0]['solver']['total_cost']=100
    save(tmp_path/'request.json',request);save(tmp_path/'routes.json',routes)
    np.savez(tmp_path/'lattice.npz',states=states,times=times,costs=np.stack([costs,alternative]))
    result=read(tmp_path/'result.json')
    for name,key in [('request.json','request_sha256'),('routes.json','routes_sha256'),('lattice.npz','lattice_sha256')]:
        result[key]=sha256(tmp_path/name)
    if fault=='forged_optimum':result['selected']='Zminus'
    save(tmp_path/'result.json',result);original=(tmp_path/'result.json').read_bytes()
    name='missing' if fault=='missing_route' else 'Zminus'
    if fault is None:
        guide,axis,chosen,_=load_path(tmp_path,tmp_path/'plan',[1,2,3],inputs,route_name=name)
        assert chosen['axis_name']=='Zminus';np.testing.assert_array_equal(axis,[0,0,-1])
        assert (tmp_path/'result.json').read_bytes()==original
        assert load_path(tmp_path,tmp_path/'plan',[1,2,3],inputs)[2]['axis_name']=='Xplus'
    else:
        with pytest.raises(ValueError):load_path(tmp_path,tmp_path/'plan',[1,2,3],inputs,route_name=name)
