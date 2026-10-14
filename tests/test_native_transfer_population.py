"""Complete population accounting, real tiny transfers, and resumable receipts."""
from pathlib import Path
import sys
import copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_transfer_population as population
from strep import save,read,sha256
from test_native_rig_transfer import pair


@pytest.fixture
def protocol(tmp_path):
    a,ap,b,bp=pair(tmp_path/'assets')
    def bound(p):return dict(path=str(p),sha256=sha256(p))
    case=dict(id='arbitrary-action',source=dict(glb=bound(a),profile=bound(ap),animation_index=0),target=dict(glb=bound(b),profile=bound(bp)),metadata=dict(action='arbitrary caller action'))
    value=dict(schema=population.SCHEMA,rate_hz=120,floor=dict(y_m=0.,tolerance_m=.005),scope='Generated software fixture, not anatomical evidence',cases=[case])
    path=tmp_path/'protocol.json';save(path,value);return path,value


def test_actual_generated_transfer_keeps_floor_failure_separate(protocol,tmp_path):
    path,value=protocol;value['floor']['y_m']=100.;save(path,value)
    folder=tmp_path/'study';population.prepare(path,sha256(path),folder);population.run(folder)
    result=read(folder/'result.json');assert result['planned']==result['completed']==1 and result['failed']==0
    row=result['cases'][0];assert row['transfer_fidelity_pass'] and row['samples']>960
    assert row['source_floor_pass'] is False and row['target_floor_pass'] is False and result['target_floor_passes']==0
    assert result['quality_approved'] is False and result['engine_executed'] is False and result['contact_verified'] is False
    population.checked_row(folder,row)
    with pytest.raises(ValueError,match='restarted'):population.run(folder,resume=True)


@pytest.mark.parametrize('fault',['duplicate','missing','changed','boolean-index','unknown-field','nonfinite','empty','rate'])
def test_invalid_complete_protocol_does_not_create_output(protocol,tmp_path,fault):
    path,value=protocol
    if fault=='duplicate':value['cases'].append(copy.deepcopy(value['cases'][0]))
    elif fault=='missing':value['cases'][0]['target'].pop('profile')
    elif fault=='changed':value['cases'][0]['source']['glb']['sha256']='0'*64
    elif fault=='boolean-index':value['cases'][0]['source']['animation_index']=True
    elif fault=='unknown-field':value['approved']=True
    elif fault=='nonfinite':value['floor']['y_m']=True
    elif fault=='empty':value['cases']=[]
    else:value['rate_hz']=30
    save(path,value);folder=tmp_path/'invalid'
    with pytest.raises(ValueError):population.prepare(path,sha256(path),folder)
    assert not folder.exists()


def test_resume_reuses_sealed_failure_without_hiding_pending_case(protocol,tmp_path,monkeypatch):
    path,value=protocol;value['cases'].append(copy.deepcopy(value['cases'][0]));value['cases'][1]['id']='second';save(path,value)
    folder=tmp_path/'study';population.prepare(path,sha256(path),folder);calls=[]
    def reject(*args,**kwargs):calls.append(1);raise ValueError('Retained unsupported fixture')
    monkeypatch.setattr(population.bridge,'export',reject)
    # First case starts; second remains explicitly pending at the phase boundary.
    clocks=iter([0.,0.,2.]);monkeypatch.setattr(population.time,'monotonic',lambda:next(clocks))
    population.run(folder,maximum_seconds=1)
    rows=read(folder/'progress.json')['cases'];assert [r['status'] for r in rows]==['failed','pending']
    assert not (folder/'result.json').exists() and read(folder/'pipeline.json')['status']=='deferred'
    import psutil
    identity=read(folder/'runner.json');identity['pid']=12345;save(folder/'runner.json',identity)
    # No need to query OS for the new worker identity after the resume check.
    # Preserve real self identity while projecting the old worker as absent.
    from types import SimpleNamespace
    monkeypatch.setattr(psutil,'Process',lambda *a:(_ for _ in ()).throw(psutil.NoSuchProcess(12345)) if a else SimpleNamespace(create_time=lambda:1.))
    monkeypatch.setattr(population.time,'monotonic',lambda:0.)
    population.run(folder,resume=True)
    result=read(folder/'result.json');assert result['planned']==result['failed']==2 and len(calls)==2
    assert len(list((folder/'cases/arbitrary-action').glob('attempt-*')))==1
    changed=copy.deepcopy(result['cases'][0]);changed['error']='forged summary'
    with pytest.raises(ValueError,match='summary'):population.checked_row(folder,changed)
    artifact=folder/next(iter(result['cases'][0]['artifacts']));artifact.write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact'):population.checked_row(folder,result['cases'][0])
