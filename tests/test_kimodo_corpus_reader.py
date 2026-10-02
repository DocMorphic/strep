"""Verified reader fixtures contain no real human review or permission claims."""
from pathlib import Path
import sys

import pytest
import torch
from safetensors.torch import load_file,save_file

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import kimodo_training_corpus as producer
from kimodo_corpus_reader import verify_corpus
from strep import read,save,sha256
from test_kimodo_training_corpus import fixture,Rep


@pytest.fixture
def prepared(fixture,monkeypatch):
    f=fixture
    def encode(rep,local,roots,*args):
        clean=torch.full((1,len(roots),369),-2/3)
        clean[0,:,:3]=roots
        return clean,torch.tensor([.25]),{'quality_approved':False,'training_rights_verified':False}
    monkeypatch.setattr(producer,'encode_native_target',encode)
    f.binding={'inputs_sha256':{str(f.evidence):sha256(f.evidence)}}
    f.output=f.root/'corpus'
    producer.prepare(f.submission,f.reservations,f.output,Rep(),f.binding)
    f.manifest=f.output/'manifest.json'
    return f


def verify(f):
    return verify_corpus(f.output,Rep(),expected_manifest_sha256=sha256(f.manifest),
                         expected_codec_binding=f.binding,reservation_path=f.reservations)


def alter(f,change):
    value=read(f.manifest);change(value);save(f.manifest,value)


def test_reader_revalidates_reviews_geometry_contacts_and_separates_splits(prepared):
    f=prepared;verified=verify(f)
    assert verified.manifest_sha256==sha256(f.manifest)
    assert [row.split for row in verified.examples]==['train','development_validation']
    assert [row.frames for row in verified.examples]==[3,3]
    values=verified.read('segment0')
    assert values['clean_features'].shape==(1,3,369) and values['reviewed_foot_contacts'][0,0]
    values['clean_features'].fill_(100)
    assert not torch.equal(verified.read('segment0')['clean_features'],values['clean_features'])
    verified.assert_unchanged()
    with pytest.raises(ValueError,match='verified example'):
        verified.read('unknown')


def test_pinned_manifest_and_expected_codec_are_required(prepared):
    f=prepared
    with pytest.raises(ValueError,match='pinned training snapshot'):
        verify_corpus(f.output,Rep(),expected_manifest_sha256='f'*64,expected_codec_binding=f.binding,reservation_path=f.reservations)
    with pytest.raises(ValueError,match='lowercase'):
        verify_corpus(f.output,Rep(),expected_manifest_sha256='not-a-hash',expected_codec_binding=f.binding,reservation_path=f.reservations)
    with pytest.raises(ValueError,match='expected codec'):
        verify_corpus(f.output,Rep(),expected_manifest_sha256=sha256(f.manifest),expected_codec_binding={'different':True},reservation_path=f.reservations)


@pytest.mark.parametrize('field,value',[('schema','strep-native-correction-corpus-v1'),('quality_approved',True),('release_approved',True),
                                       ('reviewer',{'name':'different'}),('purpose','release evidence'),('rights_status','automatic legal approval')])
def test_old_or_invented_approval_and_review_metadata_rejected(prepared,field,value):
    f=prepared;alter(f,lambda d:d.update({field:value}))
    with pytest.raises(ValueError):verify(f)


def test_artifact_must_not_escape_even_if_external_target_hash_is_valid(prepared):
    f=prepared
    original=f.output/'target-0000.safetensors';outside=f.root/'copied.safetensors';outside.write_bytes(original.read_bytes())
    alter(f,lambda d:d['items'][0].update(target_file='../copied.safetensors'))
    with pytest.raises(ValueError,match='escapes'):
        verify(f)


def test_missing_archived_evidence_cannot_be_invented_or_omitted(prepared):
    f=prepared;alter(f,lambda d:d['archived_evidence'].pop(str(f.evidence)))
    with pytest.raises(ValueError,match='retain every'):
        verify(f)


def test_altered_archive_cannot_hide_behind_unchanged_original(prepared):
    f=prepared;manifest=read(f.manifest);archived=f.output/manifest['archived_evidence'][str(f.evidence)]
    archived.write_bytes(archived.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='Archived'):
        verify(f)


@pytest.mark.parametrize('kind',['geometry','heading','contacts','shape','dtype','nan'])
def test_retaged_target_checksum_cannot_replace_the_reviewed_derivation(prepared,kind):
    f=prepared;target=f.output/'target-0000.safetensors';values=load_file(str(target))
    if kind=='geometry':values['clean_features'][0,0,5]+=1
    elif kind=='heading':values['first_heading']+=1
    elif kind=='contacts':values['reviewed_foot_contacts'].logical_not_()
    elif kind=='shape':values['clean_features']=values['clean_features'][:,:2].contiguous()
    elif kind=='dtype':values['clean_features']=values['clean_features'].double()
    else:values['clean_features'][0,0,0]=float('nan')
    save_file(values,str(target))
    alter(f,lambda d:d['items'][0].update(target_sha256=sha256(target)))
    with pytest.raises(ValueError):verify(f)


@pytest.mark.parametrize('field,value',[('split','train'),('prompt','Different action'),('cleanup_seconds',0),
                                       ('heuristic_vs_reviewed_contact_difference_count',999),('geometry_report',{}),
                                       ('correction_sha256','f'*64)])
def test_prepared_example_metadata_is_bound_to_actual_review_and_codec(prepared,field,value):
    f=prepared;alter(f,lambda d:d['items'][1].update({field:value}))
    with pytest.raises(ValueError):verify(f)


def test_examples_cannot_be_dropped_or_share_a_target_file(prepared):
    f=prepared;original=read(f.manifest)
    alter(f,lambda d:d['items'].pop())
    with pytest.raises(ValueError,match='cover every'):
        verify(f)
    save(f.manifest,original)
    alter(f,lambda d:d['items'][1].update(target_file=d['items'][0]['target_file']))
    with pytest.raises(ValueError,match='share one'):
        verify(f)


def test_read_and_checkpoint_rechecks_detect_postverification_changes(prepared):
    f=prepared;verified=verify(f);target=f.output/'target-0000.safetensors'
    original=target.read_bytes();target.write_bytes(original+b'changed')
    with pytest.raises(ValueError,match='checksum'):
        verified.read('segment0')
    with pytest.raises(ValueError,match='changed'):
        verified.assert_unchanged()
    target.write_bytes(original)
    f.evidence.write_bytes(f.evidence.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='changed'):
        verified.assert_unchanged()
    alter(f,lambda d:d.update(created_at='changed'))
    with pytest.raises(ValueError,match='manifest changed'):
        verified.read('segment0')


def test_alternate_reservation_catalog_is_rejected(prepared):
    f=prepared;other=f.root/'different-reservations.json';other.write_bytes(f.reservations.read_bytes())
    with pytest.raises(ValueError,match='different release reservation'):
        verify_corpus(f.output,Rep(),expected_manifest_sha256=sha256(f.manifest),expected_codec_binding=f.binding,reservation_path=other)
