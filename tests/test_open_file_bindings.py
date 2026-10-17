import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from open_file_bindings import OpenFileBindings


def fixture(tmp_path,payload=b'original'):
    path=tmp_path/'input';path.write_bytes(payload)
    return path,{str(path):hashlib.sha256(payload).hexdigest()}


@pytest.mark.parametrize('payload',[b'',b'a',b'large'*65536],ids=['empty','one-byte','many-chunks'])
def test_complete_fresh_hashes_and_bounded_chunks(tmp_path,payload):
    path,pins=fixture(tmp_path,payload)
    with OpenFileBindings(pins,buffer_bytes=19) as reader:
        for _ in range(2):
            report=reader.verify();assert report['files']==1 and report['bytes_hashed']==len(payload)
            assert report['complete_fresh_hashes'] and not report['content_cache'] and not report['digest_cache']
    with pytest.raises(ValueError,match='closed'):reader.verify()


def test_same_size_change_with_restored_timestamp_is_not_cached(tmp_path):
    path,pins=fixture(tmp_path)
    with OpenFileBindings(pins) as reader:
        before=path.stat();path.write_bytes(b'mutated!');os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        with pytest.raises(ValueError,match='SHA256'):reader.verify()


@pytest.mark.parametrize('payload',[b'x',b'original plus bytes'])
def test_size_changes_rejected(tmp_path,payload):
    path,pins=fixture(tmp_path)
    with OpenFileBindings(pins) as reader:
        path.write_bytes(payload)
        with pytest.raises(ValueError,match='size'):reader.verify()


def test_replacement_is_rejected_or_prevented_by_os_sharing(tmp_path):
    path,pins=fixture(tmp_path);replacement=tmp_path/'replacement';replacement.write_bytes(b'original')
    with OpenFileBindings(pins) as reader:
        try:os.replace(replacement,path)
        except PermissionError:
            assert os.name=='nt' and replacement.exists() and path.read_bytes()==b'original';reader.verify()
        else:
            with pytest.raises(ValueError,match='identity'):reader.verify()
    path.write_bytes(b'after close')


def test_wrong_binding_and_partial_open_failure_close_handles(tmp_path):
    path,pins=fixture(tmp_path)
    with pytest.raises(ValueError,match='SHA256'):OpenFileBindings({str(path):'0'*64})
    with pytest.raises(FileNotFoundError):OpenFileBindings({**pins,str(tmp_path/'missing'):'0'*64})
    path.unlink();assert not path.exists()


@pytest.mark.parametrize('kwargs',[dict(maximum_files=0),dict(maximum_files=True),dict(maximum_files=4097),dict(buffer_bytes=0),dict(buffer_bytes=True),dict(buffer_bytes=1024**2+1)])
def test_explicit_limits(tmp_path,kwargs):
    path,pins=fixture(tmp_path)
    with pytest.raises(ValueError):OpenFileBindings(pins,**kwargs)


@pytest.mark.parametrize('bindings',[{}, {'relative':'0'*64}, {'/absolute':'G'*64}, {'/absolute':'0'*63}])
def test_invalid_binding_maps(bindings):
    with pytest.raises(ValueError):OpenFileBindings(bindings)


def test_open_count_checked_before_any_open(tmp_path,monkeypatch):
    path,pins=fixture(tmp_path);pins[str(tmp_path/'other')]='0'*64
    monkeypatch.setattr(Path,'open',lambda *args,**kwargs:pytest.fail('opened before count admission'))
    with pytest.raises(ValueError,match='bounded'):OpenFileBindings(pins,maximum_files=1)


def test_directory_rejected_before_open(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'open',lambda *args,**kwargs:pytest.fail('opened a nonregular input'))
    with pytest.raises(ValueError,match='regular'):OpenFileBindings({str(tmp_path):'0'*64})


def test_callers_cannot_replace_the_bound_digest(tmp_path):
    path,pins=fixture(tmp_path)
    with OpenFileBindings(pins) as reader:
        pins[str(path)]=hashlib.sha256(b'mutated!').hexdigest();reader.verify()
        path.write_bytes(b'mutated!')
        with pytest.raises(ValueError,match='SHA256'):reader.verify()
