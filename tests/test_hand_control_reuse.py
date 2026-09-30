import sys,shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,save,read,sha256
from hand_control_reuse import CONTROL_METHODS,embed,load_controls
from oriented_terminal_hand import OrientedTerminalMotion
from test_decoded_motion_edges import rig_fixture
from scipy.spatial.transform import Rotation


@pytest.mark.parametrize('actor',[0,1])
def test_earlier_support_preserves_entire_verified_three_key_motion(actor):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    old,new=clock[4:9].astype(float),clock[1:9].astype(float);times=np.arange(241)/120
    placement=Rotation.from_euler('xyz',[7,-29,13],degrees=True).as_matrix()
    source=OrientedTerminalMotion(rig,[1,2,3],old,times,[],placement,actor)
    target=OrientedTerminalMotion(rig,[1,2,3],new,times,[],placement,actor)
    row=np.array([.001,-.002,.003,1.,-2.,.3,-.7,.2,-.4,.8,-.6])
    control=(np.array([.4,1.,.7])[:,None]*row).ravel();expanded=embed(control,old,new)
    np.testing.assert_array_equal(expanded.reshape(-1,11)[:3],0.)
    np.testing.assert_array_equal(expanded[-33:],control)
    np.testing.assert_array_equal(source.evaluate_vector(control)[0],target.evaluate_vector(expanded)[0])
    for clock in [new+1e-10,new[:-1],new[::-1]]:
        with pytest.raises(ValueError):embed(control,old,clock)


def fixture(folder):
    (folder/'implementation').mkdir();methods={}
    for name in CONTROL_METHODS:
        shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name);methods[name]=sha256(folder/'implementation'/name)
    source=folder/'source.dat';source.write_bytes(b'source');required={str(source):sha256(source)}
    save(folder/'request.json',dict(inputs=required,implementation=methods,hand_orientation=True,edit_native_times_s=[.3,.4,.5,.6,.7]))
    save(folder/'selected.json',dict(controls=(np.arange(33)/1000).tolist(),motion_domain_feasible=True))
    decoded=[]
    for name in ['A','B']:
        path=folder/(name+'.glb');path.write_bytes(name.encode())
        decoded.append(dict(actor=name,path=path.name,sha256=sha256(path),positional=dict(failures=0),
            angular={'angular_speed_rad_s':dict(exceeding_observations=0),'angular_acceleration_rad_s2':dict(exceeding_observations=0)}))
    save(folder/'decoded.json',decoded);seal(folder);return required


def seal(folder):
    save(folder/'result.json',dict(status='complete',full_clock_motion_pass=True,
        **{name+'_sha256':sha256(folder/(name+'.json')) for name in ['request','selected','decoded']}))


@pytest.mark.parametrize('fault',[None,'source','clip','controls_hash','infeasible','decoded_failure','method','end','incomplete'])
def test_warm_start_requires_bound_feasible_donor_and_exact_native_mapping(tmp_path,fault):
    required=fixture(tmp_path);native=[0.,.1,.2,.3,.4,.5,.6,.7]
    if fault=='source':(tmp_path/'source.dat').write_bytes(b'changed')
    if fault=='clip':(tmp_path/'A.glb').write_bytes(b'changed')
    if fault=='controls_hash':save(tmp_path/'selected.json',dict(controls=[0]*33,motion_domain_feasible=True))
    if fault=='infeasible':
        row=read(tmp_path/'selected.json');row['motion_domain_feasible']=False;save(tmp_path/'selected.json',row);seal(tmp_path)
    if fault=='decoded_failure':
        rows=read(tmp_path/'decoded.json');rows[0]['positional']['failures']=1;save(tmp_path/'decoded.json',rows);seal(tmp_path)
    if fault=='method':
        row=read(tmp_path/'request.json');name=CONTROL_METHODS[0];path=tmp_path/'implementation'/name
        path.write_text('# changed');row['implementation'][name]=sha256(path);save(tmp_path/'request.json',row);seal(tmp_path)
    if fault=='end':native[-1]+=.001
    if fault=='incomplete':
        row=read(tmp_path/'result.json');row['status']='running';save(tmp_path/'result.json',row)
    if fault:
        with pytest.raises(ValueError):load_controls(tmp_path,required,native)
    else:
        controls,paths,files=load_controls(tmp_path,required,native)
        np.testing.assert_array_equal(controls[:33],0);np.testing.assert_array_equal(controls[33:],np.arange(33)/1000)
        assert [p.name for p in paths]==['A.glb','B.glb']
        assert all(str(p) in files for p in paths) and str(tmp_path/'source.dat') in files


@pytest.mark.parametrize('dimensions',[66,84])
def test_solver_retains_full_control_finite_difference_batch(monkeypatch,dimensions):
    import continuous_terminal_hand as module
    observed=[]
    def evaluate(c):
        observed.append(c.copy());return .02,np.ones(1)
    def minimize(fun,initial,**kwargs):
        constraint=kwargs['constraints'][0]['fun'];constraint(initial)
        for i in range(dimensions):
            step=initial.copy();step[i]+=1e-4;constraint(step)
        constraint(initial)
        return SimpleNamespace(x=initial,success=True,status=0,message='fixture',nit=1,nfev=1)
    monkeypatch.setattr(module,'minimize',minimize)
    best,_,records=module.solve(evaluate,np.ones(dimensions),[np.zeros(dimensions)],iterations=1)
    assert len(observed)==len(records)==dimensions+1
    assert best['motion_domain_feasible']


@pytest.mark.parametrize('independent_donor',[False,True])
def test_control_layout_conversion_preserves_individual_rows_and_binds_method(tmp_path,independent_donor):
    from independent_hand_motion import from_symmetric,INDEPENDENT_LAYOUT
    required=fixture(tmp_path);native=[0.,.1,.2,.3,.4,.5,.6,.7]
    expected=from_symmetric(np.arange(33)/1000)
    if independent_donor:
        expected.reshape(-1,14)[:,3:6]+=.017  # deliberately not equal/opposite
        row=read(tmp_path/'request.json');row['control_layout']=INDEPENDENT_LAYOUT
        name='independent_hand_motion.py';shutil.copyfile(ROOT/'scripts'/name,tmp_path/'implementation'/name)
        row['implementation'][name]=sha256(tmp_path/'implementation'/name);save(tmp_path/'request.json',row)
        save(tmp_path/'selected.json',dict(controls=expected.tolist(),motion_domain_feasible=True));seal(tmp_path)
    controls,_,files=load_controls(tmp_path,required,native,independent_wrists=True)
    np.testing.assert_array_equal(controls[:42],0);np.testing.assert_array_equal(controls[42:],expected)
    if independent_donor:
        assert str(tmp_path/'implementation'/'independent_hand_motion.py') in files
        with pytest.raises(ValueError,match='discard'):load_controls(tmp_path,required,native)
        row=read(tmp_path/'request.json');path=tmp_path/'implementation'/'independent_hand_motion.py'
        path.write_text('# altered independent interpretation');row['implementation'][path.name]=sha256(path)
        save(tmp_path/'request.json',row);seal(tmp_path)
        with pytest.raises(ValueError,match='interpretation'):load_controls(tmp_path,required,native,independent_wrists=True)


def test_unknown_layout_is_rejected_even_with_resealed_artifacts(tmp_path):
    from independent_hand_motion import layout
    required=fixture(tmp_path);row=read(tmp_path/'request.json');row['control_layout']='future-v9'
    save(tmp_path/'request.json',row);seal(tmp_path)
    with pytest.raises(ValueError,match='Unknown'):load_controls(tmp_path,required,[.3,.4,.5,.6,.7],independent_wrists=True)
    with pytest.raises(ValueError,match='Unknown'):layout('future-v9')


@pytest.mark.parametrize('actor',[0,1])
def test_fourteen_control_embedding_keeps_export_byte_identical_with_asymmetric_wrists(actor,tmp_path):
    from independent_hand_motion import IndependentHandMotion
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    old,new=clock[4:9].astype(float),clock[1:9].astype(float);times=np.arange(241)/120
    placement=Rotation.from_euler('xyz',[7,-29,13],degrees=True).as_matrix()
    control=(np.array([.4,1.,.7])[:,None]*np.array([.001,-.002,.003,.004,.001,-.002,1.,-2.,.3,-.7,.2,-.4,.8,-.6])).ravel()
    paths=[tmp_path/'old.glb',tmp_path/'new.glb']
    for native,values,path in zip([old,new],[control,embed(control,old,new,width=14)],paths):
        model=IndependentHandMotion(rig,[1,2,3],native,times,[],placement,actor);model.export_vector(values,path)
    assert paths[0].read_bytes()==paths[1].read_bytes()
