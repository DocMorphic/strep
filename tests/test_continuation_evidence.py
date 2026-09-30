import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from continuation_evidence import cumulative_controls,load_continuation
from strep import save,read,sha256


@pytest.mark.parametrize('fault',[None,'delta_only','extra','matrix','nan','factor','failed'])
def test_cumulative_controls_cannot_be_replaced_by_the_increment(fault):
    request=dict(cumulative_controls=[.01,.02,.03])
    solver=dict(increment=[.001,-.002,.003],solver=dict(proposal_hard_checks=True))
    expected=np.array(request['cumulative_controls'])+.5*np.array(solver['increment'])
    trial=dict(factor=.5,controls=expected.tolist())
    if fault=='delta_only': trial['controls']=(.5*np.array(solver['increment'])).tolist()
    if fault=='extra': trial['controls'].append(0.)
    if fault=='matrix': trial['controls']=[trial['controls']]
    if fault=='nan': trial['controls'][0]=float('nan')
    if fault=='factor': trial['factor']=True
    if fault=='failed': solver['solver']['proposal_hard_checks']=False
    if fault is None: np.testing.assert_array_equal(cumulative_controls(request,solver,trial),expected)
    else:
        with pytest.raises((ValueError,AssertionError)): cumulative_controls(request,solver,trial)


def fixture(root):
    (root/'current').mkdir();(root/'implementation').mkdir();(root/'trial-0').mkdir()
    save(root/'current/sample-000.json',dict(sample=0))
    save(root/'current-index.json',{'sample-000.json':sha256(root/'current/sample-000.json')})
    (root/'implementation/method.py').write_text('# fixture\n')
    save(root/'request.json',dict(cumulative_controls=[.01,.02,.03],inputs={},
        implementation={'method.py':sha256(root/'implementation/method.py')}))
    save(root/'solver.json',dict(increment=[0.,0.,0.],solver=dict(proposal_hard_checks=True)))
    np.savez(root/'linearization.npz',gaps=np.array([-.01]))
    actors=[]
    for i in range(2):
        path=root/'trial-0'/f'actor-{i}.glb';path.write_bytes(b'fixture'+bytes([i]))
        actors.append(dict(actor=str(i),path=path.name,sha256=sha256(path)))
    trial=dict(factor=.5,controls=[.01,.02,.03],actors=actors,angular_rates=[dict(actor=a['actor']) for a in actors])
    save(root/'trials.json',[trial]);save(root/'trial-0/review.json',trial)
    result=dict(status='complete')
    for name in ['request.json','trials.json','current-index.json','linearization.npz','solver.json']:
        result[name.split('.')[0].replace('-','_')+'_sha256']=sha256(root/name)
    save(root/'result.json',result)
    return trial


@pytest.mark.parametrize('fault',[None,'incomplete','request','matrix','witness','snapshot','clip','review','angular_order','clip_escape'])
def test_completed_replay_requires_bound_inputs_and_exports(tmp_path,fault):
    trial=fixture(tmp_path)
    if fault=='incomplete':
        result=read(tmp_path/'result.json');result['status']='processing';save(tmp_path/'result.json',result)
    if fault=='request':save(tmp_path/'request.json',{})
    if fault=='matrix':np.savez(tmp_path/'linearization.npz',gaps=np.array([0.]))
    if fault=='witness':save(tmp_path/'current/sample-000.json',{})
    if fault=='snapshot':(tmp_path/'implementation/method.py').write_text('changed')
    if fault=='clip':(tmp_path/'trial-0/actor-0.glb').write_bytes(b'changed')
    if fault=='review':save(tmp_path/'trial-0/review.json',{})
    if fault in ['angular_order','clip_escape']:
        if fault=='angular_order':trial['angular_rates'].reverse()
        else:trial['actors'][0]['path']='../actor-0.glb'
        save(tmp_path/'trials.json',[trial]);save(tmp_path/'trial-0/review.json',trial)
        result=read(tmp_path/'result.json');result['trials_sha256']=sha256(tmp_path/'trials.json');save(tmp_path/'result.json',result)
    if fault is None:
        _,_,trials,files=load_continuation(tmp_path)
        assert trials==[trial] and str(tmp_path/'current/sample-000.json') in files
    else:
        with pytest.raises(ValueError):load_continuation(tmp_path)
