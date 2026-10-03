"""Exact observation transport and bounded lifetime, never geometry evidence."""
import gc,hashlib,io,json,sys,weakref,zipfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_observation_archive import ObservationArchive,logical_sha256,verify
from strep import read,save,sha256


@pytest.mark.parametrize('value',[
    np.arange(12,dtype=np.float64).reshape(4,3),
    np.asfortranarray(np.arange(12,dtype=np.float32).reshape(4,3)),
    np.arange(24,dtype=np.int64).reshape(6,4)[::-1,::2],
    np.array([1,2,3],dtype='>f8'),
    np.array([True,False],dtype=bool),
    np.array([complex(1,2),complex(-3,4)],dtype='>c16'),
    np.array(3.25,dtype=np.float64),
    np.empty((2,0,3),dtype=np.float64),
    np.array([np.nan,np.inf,-np.inf,-0.],dtype=np.float64),
    np.array([0x7ff0000000000001,0x7ff8000000000042,0x8000000000000000,0x0000000000000001],dtype=np.uint64).view(np.float64),
])
def test_exact_dtype_shape_bytes_and_ordered_population_roundtrip(tmp_path,value):
    path=tmp_path/'observations.npz';before=value.tobytes(order='C')
    with ObservationArchive(path) as store:
        store['times_s']=np.array([0.,.1,2.])
        store['frame_0_A_item_witness_world_m']=value
    result=verify(path)
    assert result['arrays']==2 and result['all_values_exact']
    assert not result['geometry_verified'] and not result['quality_approved'] and not result['release_approved']
    with np.load(path,allow_pickle=False) as saved:
        actual=saved['frame_0_A_item_witness_world_m']
        assert actual.shape==value.shape and actual.dtype==value.dtype and actual.tobytes(order='C')==before
        assert saved.files==['times_s','frame_0_A_item_witness_world_m']
    assert logical_sha256(value)==hashlib.sha256(before).hexdigest()
    assert value.tobytes(order='C')==before
    assert not Path(str(path)+'.partial').exists()
    with pytest.raises(ValueError,match='Fresh'):ObservationArchive(path)


def test_writer_does_not_retain_previous_array_values(tmp_path):
    path=tmp_path/'stream.npz';refs=[]
    with ObservationArchive(path) as store:
        for i in range(128):
            value=np.full((64,3),i,dtype=np.float64);refs.append(weakref.ref(value))
            store[f'frame_{i}_A_item_witness_world_m']=value;del value
        gc.collect();assert all(r() is None for r in refs)
    assert verify(path)['arrays']==128
    with np.load(path) as saved:
        assert all((saved[f'frame_{i}_A_item_witness_world_m']==i).all() for i in range(128))


@pytest.mark.parametrize('fault',['name','duplicate','object','text','metadata','budget'])
def test_write_failures_retain_partial_arrays_without_completing(tmp_path,fault):
    path=tmp_path/'failed.npz'
    with pytest.raises(ValueError):
        with ObservationArchive(path,maximum_array_bytes=32) as store:
            store['times_s']=np.array([0.,1.])
            if fault=='name':store['../escape']=np.zeros(1)
            elif fault=='duplicate':store['times_s']=np.zeros(1)
            elif fault=='object':store['bad']=np.array([{'unsafe':True}],dtype=object)
            elif fault=='text':store['bad']=np.array(['label'])
            elif fault=='metadata':store['bad']=np.array([1.],dtype=np.dtype('f8',metadata={'field':'discarded'}))
            else:store['too_large']=np.zeros(10)
    partial=Path(str(path)+'.partial');receipt=read(Path(str(partial)+'.receipt.json'))
    assert receipt['status']=='failed' and list(receipt['completed_arrays'])==['times_s']
    assert not receipt['quality_approved'] and not receipt['release_approved'] and not path.exists()
    with np.load(partial) as saved:assert np.array_equal(saved['times_s'],[0.,1.])
    with pytest.raises(ValueError,match='Fresh'):ObservationArchive(path)


def test_empty_archive_is_a_retained_failure(tmp_path):
    path=tmp_path/'empty.npz'
    with pytest.raises(ValueError,match='empty'):
        with ObservationArchive(path):pass
    assert read(Path(str(path)+'.partial.receipt.json'))['status']=='failed'


def test_source_mutation_during_write_rejects_and_retains_snapshot(tmp_path,monkeypatch):
    path=tmp_path/'changed.npz';value=np.arange(4,dtype=np.float64);original=np.lib.format.write_array
    def mutate(stream,snapshot,**kwargs):
        original(stream,snapshot,**kwargs);value[0]+=1
    monkeypatch.setattr(np.lib.format,'write_array',mutate)
    with pytest.raises(ValueError,match='changed while writing'):
        with ObservationArchive(path) as store:store['positions']=value
    with np.load(Path(str(path)+'.partial')) as saved:assert np.array_equal(saved['positions'],np.arange(4))
    assert not read(Path(str(path)+'.partial.receipt.json'))['completed_arrays']


def test_a_racing_destination_is_never_overwritten(tmp_path):
    path=tmp_path/'race.npz'
    with pytest.raises(ValueError,match='appeared'):
        with ObservationArchive(path) as store:
            store['positions']=np.arange(4);path.write_bytes(b'preexisting foreign file')
    assert path.read_bytes()==b'preexisting foreign file'
    receipt=read(Path(str(path)+'.partial.receipt.json'))
    assert receipt['retained_path']=='race.npz.partial'
    with np.load(tmp_path/receipt['retained_path']) as saved:assert np.array_equal(saved['positions'],np.arange(4))


def test_publication_race_after_the_existence_check_is_not_overwritten(tmp_path,monkeypatch):
    import native_observation_archive as archive
    path=tmp_path/'race.npz';original=archive.os.link
    def race(source,destination):
        Path(destination).write_bytes(b'foreign racing file');return original(source,destination)
    monkeypatch.setattr(archive.os,'link',race)
    with pytest.raises(FileExistsError):
        with ObservationArchive(path) as store:store['positions']=np.arange(4)
    assert path.read_bytes()==b'foreign racing file'
    assert read(Path(str(path)+'.partial.receipt.json'))['retained_path']=='race.npz.partial'


def test_existing_receipt_is_never_overwritten(tmp_path):
    path=tmp_path/'race.npz';receipt=Path(str(path)+'.receipt.json')
    with pytest.raises(ValueError,match='appeared'):
        with ObservationArchive(path) as store:
            store['positions']=np.arange(4);receipt.write_bytes(b'foreign receipt')
    assert receipt.read_bytes()==b'foreign receipt' and not path.exists()


@pytest.mark.parametrize('change',['shape','dtype'])
def test_source_shape_and_dtype_drift_reject_even_when_bytes_match(tmp_path,monkeypatch,change):
    value=np.arange(4,dtype=np.float64);original=np.lib.format.write_array;path=tmp_path/'changed.npz'
    def mutate(stream,snapshot,**kwargs):
        original(stream,snapshot,**kwargs)
        if change=='shape':value.shape=(2,2)
        else:value.dtype=np.uint64
    monkeypatch.setattr(np.lib.format,'write_array',mutate)
    with pytest.raises(ValueError,match='changed while writing'):
        with ObservationArchive(path) as store:store['positions']=value
    assert read(Path(str(path)+'.partial.receipt.json'))['status']=='failed'


@pytest.mark.parametrize('fault',['archive-hash','dtype','shape','data-hash','total-bytes','missing','scope','array-budget'])
def test_changed_receipts_reject(tmp_path,fault):
    path=tmp_path/'observations.npz'
    with ObservationArchive(path) as store:store['positions']=np.arange(4,dtype=np.float64)
    receipt=Path(str(path)+'.receipt.json');result=read(receipt)
    if fault=='archive-hash':result['archive_sha256']='0'*64
    elif fault=='dtype':result['arrays']['positions']['dtype']='<f4'
    elif fault=='shape':result['arrays']['positions']['shape']=[2,2]
    elif fault=='data-hash':result['arrays']['positions']['logical_sha256']='0'*64
    elif fault=='total-bytes':result['logical_bytes']+=1
    elif fault=='missing':result['arrays']={}
    elif fault=='scope':result['geometry_verified']=True
    else:result['maximum_array_bytes']=2**40
    save(receipt,result)
    with pytest.raises(ValueError):verify(path)


def test_changed_values_reject_even_with_updated_container_hash(tmp_path):
    path=tmp_path/'observations.npz'
    with ObservationArchive(path) as store:store['positions']=np.arange(4,dtype=np.float64)
    np.savez_compressed(path,positions=np.arange(4,dtype=np.float64)+.01)
    receipt=Path(str(path)+'.receipt.json');result=read(receipt);result['archive_sha256']=sha256(path);save(receipt,result)
    with pytest.raises(ValueError,match='data differs'):verify(path)


@pytest.mark.parametrize('fault',['huge-header','object-header','duplicate-entry','truncated-payload'])
def test_header_and_population_checks_run_before_array_allocation(tmp_path,monkeypatch,fault):
    path=tmp_path/'unsafe.npz'
    with ObservationArchive(path) as store:store['positions']=np.zeros(1,dtype=np.float64)
    stream=io.BytesIO()
    if fault=='huge-header':
        np.lib.format.write_array_header_1_0(stream,dict(shape=(10**12,),fortran_order=False,descr='<f8'))
    elif fault=='object-header':np.lib.format.write_array(stream,np.array([1],dtype=object),allow_pickle=True)
    else:np.lib.format.write_array(stream,np.zeros(1,dtype=np.float64),allow_pickle=False)
    payload=stream.getvalue()
    if fault=='truncated-payload':payload=payload[:-1]
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('positions.npy',payload)
        if fault=='duplicate-entry':
            with pytest.warns(UserWarning):z.writestr('positions.npy',payload)
    receipt=Path(str(path)+'.receipt.json');result=read(receipt);result['archive_sha256']=sha256(path);save(receipt,result)
    def forbidden(*args,**kwargs):raise AssertionError('Unsafe array must not allocate/load')
    monkeypatch.setattr(np,'load',forbidden)
    with pytest.raises(ValueError):verify(path)


def test_context_error_after_manual_finish_retains_failure_and_refuses_promotion(tmp_path):
    path=tmp_path/'late-error.npz'
    with pytest.raises(RuntimeError,match='caller failure'):
        with ObservationArchive(path) as store:
            store['positions']=np.zeros(1);store.finish();raise RuntimeError('caller failure')
    assert path.exists() and read(Path(str(path)+'.partial.receipt.json'))['status']=='failed'
    with pytest.raises(ValueError,match='Failed archive'):verify(path)
