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
