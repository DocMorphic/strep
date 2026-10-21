import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import strep


@pytest.mark.parametrize('code',[5,32,33])
def test_transient_windows_read_handle_preserves_old_json_until_atomic_replace(tmp_path,monkeypatch,code):
    path=tmp_path/'progress.json';strep.save(path,dict(completed=120))
    original=Path.replace;calls=[];delays=[]
    def replace(source,target):
        calls.append(1)
        assert strep.read(path)==dict(completed=120)
        if len(calls)<3:
            error=PermissionError('transient handle');error.winerror=code;raise error
        return original(source,target)
    monkeypatch.setattr(Path,'replace',replace);monkeypatch.setattr(strep.time,'sleep',delays.append)
    strep.save(path,dict(completed=121))
    assert strep.read(path)==dict(completed=121) and delays==[.05,.1]
    assert not path.with_suffix('.json.tmp').exists()


@pytest.mark.parametrize('code,expected_calls',[ (5,6),(None,1),(123,1)])
def test_permanent_denial_is_bounded_and_retains_previous_and_pending_json(tmp_path,monkeypatch,code,expected_calls):
    path=tmp_path/'progress.json';strep.save(path,dict(completed=120));calls=[]
    def replace(source,target):
        calls.append(1);error=PermissionError('denied')
        if code is not None:error.winerror=code
        raise error
    monkeypatch.setattr(Path,'replace',replace);monkeypatch.setattr(strep.time,'sleep',lambda _:None)
    with pytest.raises(PermissionError):strep.save(path,dict(completed=121))
    assert len(calls)==expected_calls
    assert strep.read(path)==dict(completed=120)
    assert strep.read(path.with_suffix('.json.tmp'))==dict(completed=121)


@pytest.mark.parametrize('data',[
    {'unicode':'caf\u00e9 \U0001f44b','escaped':'\n\t"\\','nested':[None,True,False,{},[]]},
    {'numbers':[0,-0.0,1e-250,1e250,1.2345678901234567],7:'integer key'},
    [{'iteration':i,'directions':[[.25,-.5,1.0]]*3,'accepted':i%2==0} for i in range(40)],
])
def test_streamed_json_preserves_previous_bytes_and_final_newline(tmp_path,data):
    path=tmp_path/'actual.json';expected=tmp_path/'expected.json'
    expected.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    strep.save(path,data)
    assert path.read_bytes()==expected.read_bytes()
    assert not path.with_suffix('.json.tmp').exists()


@pytest.mark.parametrize('invalid',[float('nan'),float('inf'),float('-inf'),object()])
def test_serialization_failure_never_publishes_partial_json(tmp_path,invalid):
    path=tmp_path/'progress.json';strep.save(path,{'completed':120});original=path.read_bytes()
    with pytest.raises((TypeError,ValueError)):
        strep.save(path,{'large_prefix':list(range(1000)),'invalid_tail':invalid})
    assert path.read_bytes()==original
    # A later successful attempt replaces the pending partial file completely.
    strep.save(path,{'completed':121})
    assert strep.read(path)=={'completed':121}


def test_mid_write_io_failure_preserves_published_report(tmp_path,monkeypatch):
    path=tmp_path/'progress.json';strep.save(path,{'completed':120});original=path.read_bytes()
    def fail(data,stream,**kwargs):
        stream.write('{"unfinished":');raise OSError('simulated disk write failure')
    monkeypatch.setattr(strep.json,'dump',fail)
    with pytest.raises(OSError,match='disk write failure'):strep.save(path,{'completed':121})
    assert path.read_bytes()==original
