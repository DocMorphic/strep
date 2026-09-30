import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from audit_pair_direction_peak import selected


def fixture(root, windows=False):
    folder=root/'tangentminus';(folder/'trial-0').mkdir(parents=True)
    actors=[]
    for i in range(2):
        clip=folder/'trial-0'/f'actor-{i}.glb';clip.write_bytes(b'fixture'+bytes([i]))
        actors.append(dict(actor=str(i),path=clip.name,sha256=sha256(clip)))
    solver=dict(solver=dict(proposal_hard_checks=True),increment=[.002,0.,0.])
    trial=dict(controls=[.001,0.,0.],factor=.5,actors=actors,
        angular_rates=[dict(actor=a['actor']) for a in actors],reasons=['exported_motion'],preliminary_pass=False)
    save(root/'request.json',dict(inputs={},implementation={},cumulative_controls=[0.,0.,0.]))
    save(folder/'solver.json',solver);save(folder/'trial-0/review.json',trial)
    save(root/'variants.json',[dict(direction='tangentminus',solver=solver['solver'],trials=[trial])])
    artifacts={p.relative_to(root).as_posix():sha256(p) for p in root.rglob('*') if p.is_file()}
    if windows:artifacts={n.replace('/','\\'):d for n,d in artifacts.items()}
    save(root/'result.json',dict(status='complete',artifacts=artifacts))
    return trial


@pytest.mark.parametrize('windows',[True,False])
def test_rejected_trials_remain_available_for_diagnosis(tmp_path,windows):
    expected=fixture(tmp_path,windows);_,trial,_=selected(tmp_path,'tangentminus',0)
    assert trial==expected and trial['reasons']==['exported_motion']


@pytest.mark.parametrize('fault',['incomplete','clip','unbound_clip','solver','review','unbound_request',
    'controls','escape','negative','missing','actor_order'])
def test_peak_diagnostic_requires_bound_complete_controls_and_exports(tmp_path,fault):
    fixture(tmp_path);result=read(tmp_path/'result.json')
    if fault=='incomplete':result['status']='processing'
    if fault=='clip':(tmp_path/'tangentminus/trial-0/actor-0.glb').write_bytes(b'changed')
    if fault=='unbound_clip':result['artifacts'].pop('tangentminus/trial-0/actor-0.glb')
    if fault=='unbound_request':result['artifacts'].pop('request.json')
    if fault in ['solver','review']:(tmp_path/f'tangentminus/{"solver.json" if fault=="solver" else "trial-0/review.json"}').write_text('{}')
    if fault=='escape':result['artifacts']['../escape']='irrelevant'
    if fault in ['controls','actor_order']:
        rows=read(tmp_path/'variants.json');trial=rows[0]['trials'][0]
        if fault=='controls':trial['controls'][0]=.1
        else:trial['angular_rates'].reverse()
        save(tmp_path/'variants.json',rows);save(tmp_path/'tangentminus/trial-0/review.json',trial)
        for name in ['variants.json','tangentminus/trial-0/review.json']:result['artifacts'][name]=sha256(tmp_path/name)
    save(tmp_path/'result.json',result)
    with pytest.raises((ValueError,AssertionError)):
        selected(tmp_path,'other' if fault=='missing' else 'tangentminus',-1 if fault=='negative' else 0)
