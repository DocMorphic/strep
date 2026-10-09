import sys
from pathlib import Path
import copy
import json
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_proposal_archive import ProposalArchive,load_record
from strep import read,sha256
from protected_inequality_step import fit
from native_observation_archive import ObservationArchive


def record():
    return dict(iteration=1,retained=False,controls=[.1,.2],jacobian=[[1.,0.],[0.,2.]],
        rows=[0,1],mask=[True,False],cuts=[dict(ids=[0],plane=[[1.,2.]],bound=[.03])],
        empty=[],mixed=[True,1,1.5,None,'text'],note='Complete report',quality_approved=False)


def test_complete_nested_records_roundtrip_exactly_without_retaining_prior_arrays(tmp_path):
    store=ProposalArchive(tmp_path);source=record();original=copy.deepcopy(source);ref=store('start',source)
    restored,bindings=load_record(tmp_path,ref)
    assert source==original==restored and len(bindings)==3 and 'jacobian' not in ref
    assert [type(v) for v in restored['mixed']]==[bool,int,float,type(None),str]
    assert all(sha256(Path(path))==digest for path,digest in bindings.items())
    source['jacobian'][0][0]=100
    assert load_record(tmp_path,ref)[0]==original
    with pytest.raises(ValueError):store('start',original)


@pytest.mark.parametrize('target',['metadata','archive','receipt'])
@pytest.mark.parametrize('array_values',[False,True])
def test_changed_payload_or_receipt_rejected(tmp_path,target,array_values):
    ref=ProposalArchive(tmp_path)('start',record());path=tmp_path/ref['metadata']
    if target=='archive':path=path.with_suffix('.npz')
    if target=='receipt':path=Path(str(path.with_suffix('.npz'))+'.receipt.json')
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError):load_record(tmp_path,ref,array_values=array_values)


@pytest.mark.parametrize('damage',['schema','escape','kind','iteration','missing-array','duplicate-array','extra-array'])
@pytest.mark.parametrize('array_values',[False,True])
def test_invalid_archive_identity_or_array_population_rejected(tmp_path,damage,array_values):
    ref=ProposalArchive(tmp_path)('start',record());metadata=tmp_path/ref['metadata']
    if damage=='schema':ref['archive_schema']='unknown'
    if damage=='escape':ref['metadata']='../outside.json'
    if damage=='kind':ref['kind']='unknown'
    if damage=='iteration':ref['iteration']=2
    if damage in ['missing-array','duplicate-array','extra-array']:
        doc=read(metadata);items=doc['tree']['items']
        if damage=='missing-array':items['controls']['name']='absent'
        if damage=='duplicate-array':items['jacobian']=copy.deepcopy(items['controls'])
        if damage=='extra-array':del items['controls']
        metadata.write_text(json.dumps(doc),encoding='utf-8');ref['metadata_sha256']=sha256(metadata)
    with pytest.raises((ValueError,KeyError)):load_record(tmp_path,ref,array_values=array_values)


@pytest.mark.parametrize('array_values',[False,True])
def test_legacy_inline_record_is_not_rewritten(tmp_path,array_values):
    source=record();restored,bindings=load_record(tmp_path,source,array_values=array_values)
    assert restored is source and not bindings


@pytest.mark.parametrize('priority',['merit','worst-first'])
@pytest.mark.parametrize('array_values',[False,True])
def test_streamed_solver_preserves_exact_controls_trials_and_recorded_population(tmp_path,priority,array_values):
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    def vectors(x):return dict(offsets=np.array([[x[0],x[1],0.]]),jacobian=np.array([[[1.,0.],[0.,1.],[0.,0.]]]),
        limits=np.array([.1]),scales=np.array([.1]),rows=np.array([1]),distance=np.array([True]))
    options=dict(iterations=1,trust=.1,proposal='nonlinear',proposal_start='geometry-descent',vectorize=vectors,proposal_tangent_guard=True,proposal_priority=priority)
    x,inline=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],**options)
    y,streamed=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],record_store=ProposalArchive(tmp_path),**options)
    np.testing.assert_array_equal(x,y)
    assert inline['trials']==streamed['trials'] and inline['final_slacks']==streamed['final_slacks']
    for kind in ['proposal_starts','proposal_linearizations']:
        for original,ref in zip(inline[kind],streamed[kind]):
            restored,_=load_record(tmp_path,ref,array_values=array_values)
            for key in original:
                if key!='seconds':assert_same_tree(original[key],restored[key])
    assert not streamed['quality_approved']


def test_invalid_record_store_rejected_before_measurement():
    def forbidden(x):raise AssertionError('Invalid transport reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],record_store=True)


def test_correction_attempts_have_distinct_bound_identity(tmp_path):
    store=ProposalArchive(tmp_path);source=record()
    first=store('correction',dict(source,attempt=1));second=store('correction',dict(source,attempt=2))
    assert first['metadata']!=second['metadata'] and load_record(tmp_path,second)[0]['attempt']==2
    changed=dict(first,attempt=2)
    with pytest.raises(ValueError,match='identity'):load_record(tmp_path,changed)


@pytest.mark.parametrize('attempt',[None,False,0,-1,1.5])
def test_invalid_correction_attempt_rejected_before_writing(tmp_path,attempt):
    store=ProposalArchive(tmp_path)
    with pytest.raises(ValueError):store('correction',dict(record(),attempt=attempt))
    assert not list((tmp_path/'proposals').iterdir())


def assert_same_tree(original,restored):
    if isinstance(restored,np.ndarray):
        expected=np.asarray(original)
        assert restored.dtype==expected.dtype and restored.shape==expected.shape
        assert restored.tobytes()==expected.tobytes() and not restored.flags.writeable
    elif isinstance(original,dict):
        assert original.keys()==restored.keys()
        for key in original:assert_same_tree(original[key],restored[key])
    elif isinstance(original,list):
        assert isinstance(restored,list) and len(original)==len(restored)
        for a,b in zip(original,restored):assert_same_tree(a,b)
    else:
        assert type(original) is type(restored) and original==restored


def test_array_mode_preserves_nested_types_float_bits_and_detached_archive_data(tmp_path):
    source=record();source.update(ragged=[[1.,2.],[3.]],wide=[-(2**63),2**63-1],
        exact=[-0.,0.,float(np.nextafter(0.,1.)),float(np.nextafter(1.,2.))])
    ref=ProposalArchive(tmp_path)('start',source)
    restored,bindings=load_record(tmp_path,ref,array_values=True)
    assert_same_tree(source,restored)
    assert isinstance(restored['jacobian'],np.ndarray) and isinstance(restored['ragged'],list)
    assert restored['jacobian'].flags.owndata and restored['jacobian'].base is None
    with pytest.raises(ValueError):restored['jacobian'][0,0]=100
    # Read-only is consumer discipline, not a security boundary: the loaded
    # allocation is detached even if a caller explicitly makes it writable.
    restored['jacobian'].setflags(write=True);restored['jacobian'][0,0]=100
    assert load_record(tmp_path,ref)[0]==source
    again,again_bindings=load_record(tmp_path,ref,array_values=True)
    assert_same_tree(source,again)
    assert bindings==again_bindings and all(sha256(Path(p))==h for p,h in bindings.items())


@pytest.mark.parametrize('mode',[None,0,1,'arrays',np.bool_(True)])
@pytest.mark.parametrize('archived',[False,True])
def test_invalid_mode_rejected_before_any_archive_access(tmp_path,mode,archived):
    source={'archive_schema':'unreadable'} if archived else record()
    with pytest.raises(ValueError,match='Boolean'):load_record(tmp_path,source,array_values=mode)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('array_values',[False,True])
@pytest.mark.parametrize('payload',[np.array(1.),np.array([1+2j]),np.array([float('nan')]),np.array([float('inf')])])
def test_resealed_non_json_numeric_payload_rejected(tmp_path,array_values,payload):
    ref=ProposalArchive(tmp_path)('start',record());metadata=tmp_path/ref['metadata'];path=metadata.with_suffix('.npz')
    receipt=Path(str(path)+'.receipt.json');doc=read(metadata)
    name=doc['tree']['items']['controls']['name']
    with np.load(path,allow_pickle=False) as saved:arrays={key:saved[key] for key in saved.files}
    arrays[name]=payload;path.unlink();receipt.unlink()
    with ObservationArchive(path) as archive:
        for key,value in arrays.items():archive[key]=value
    ref.update(archive_sha256=sha256(path),receipt_sha256=sha256(receipt))
    with pytest.raises(ValueError,match='JSON'):load_record(tmp_path,ref,array_values=array_values)


@pytest.mark.parametrize('array_values',[False,True])
def test_change_during_verified_load_rejected(tmp_path,monkeypatch,array_values):
    import pose_proposal_archive as module
    ref=ProposalArchive(tmp_path)('start',record());metadata=tmp_path/ref['metadata'];verify=module.verify
    def changing(path):
        result=verify(path)
        metadata.write_bytes(metadata.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(module,'verify',changing)
    with pytest.raises(ValueError,match='during replay'):load_record(tmp_path,ref,array_values=array_values)
