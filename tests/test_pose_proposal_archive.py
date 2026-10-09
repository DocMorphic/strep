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
def test_changed_payload_or_receipt_rejected(tmp_path,target):
    ref=ProposalArchive(tmp_path)('start',record());path=tmp_path/ref['metadata']
    if target=='archive':path=path.with_suffix('.npz')
    if target=='receipt':path=Path(str(path.with_suffix('.npz'))+'.receipt.json')
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError):load_record(tmp_path,ref)


@pytest.mark.parametrize('damage',['schema','escape','kind','iteration','missing-array','duplicate-array','extra-array'])
def test_invalid_archive_identity_or_array_population_rejected(tmp_path,damage):
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
    with pytest.raises((ValueError,KeyError)):load_record(tmp_path,ref)


def test_legacy_inline_record_is_not_rewritten(tmp_path):
    source=record();restored,bindings=load_record(tmp_path,source)
    assert restored is source and not bindings


@pytest.mark.parametrize('priority',['merit','worst-first'])
def test_streamed_solver_preserves_exact_controls_trials_and_recorded_population(tmp_path,priority):
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
            restored,_=load_record(tmp_path,ref)
            for key in original:
                if key!='seconds':assert original[key]==restored[key]
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
