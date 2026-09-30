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
