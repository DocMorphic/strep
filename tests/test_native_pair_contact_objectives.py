"""Authored contacts are objectives without replacing original hard protection."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_key_guides import inputs,make_inputs
from native_pair_key_guides import PairKeyGuides
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset


@pytest.fixture(scope='module')
def separated(tmp_path_factory):return make_inputs(tmp_path_factory.mktemp('contact-objective'),partner_offset_m=.05)


def test_contact_only_mode_is_explicit_and_retains_all_original_bounds(separated):
    models,_=separated
    with pytest.raises(ValueError):PairKeyGuides(models,[])
    pair=PairKeyGuides(models,[],fit_contacts=True);native,contact=pair.norms(pair.initial,pair.source_worlds)
    assert pair.size==sum(pair.sizes) and pair.guide_gaps(pair.initial,pair.source_worlds).shape==(0,)
    assert np.all(native.residual()<=0) and np.any(contact.residual()>0)
    np.testing.assert_array_equal(pair.contact_caps,contact.caps)
    assert np.all(pair.protected_contact_caps>=contact.caps) and np.any(pair.protected_contact_caps>contact.caps)


def test_opt_in_appends_authored_norms_and_jacobian_without_changing_default_prefix(separated):
    models,guides=separated;old=PairKeyGuides(models,guides);pair=PairKeyGuides(models,guides,fit_contacts=True)
    a,ja,ia=old.linearize(old.initial,old.source_worlds,.1);b,jb,ib=pair.linearize(pair.initial,pair.source_worlds,.1)
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(b,key)[:len(a.caps)],getattr(a,key))
    np.testing.assert_array_equal(jb[:a.vectors.size].toarray(),ja.toarray());assert ib['hard_rows']==ia['hard_rows']
    native,contact=pair.norms(pair.initial,pair.source_worlds);n=len(native.caps);c=len(contact.caps)
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(b,key)[-c:],getattr(contact,key))
    np.testing.assert_array_equal(jb[-3*c:].toarray(),ja[3*n:3*(n+c)].toarray())
    assert np.all(b.residual()[n:n+c]<=0) and np.any(b.residual()[-c:]>0)
    assert ib['contact_objective_rows']==c and ia['contact_objective_rows']==0


def test_contact_only_complete_clock_floor_and_native_prefix_is_retained(separated):
    models,_=separated;pair=PairKeyGuides(models,[],fit_contacts=True);rows,jac,meta=pair.linearize(pair.initial,pair.source_worlds,.1)
    n=meta['native_rows'];c=meta['contact_rows'];f=meta['floor_rows']
    assert meta['guide_rows']==0 and meta['hard_rows']==n+c+f and len(rows.caps)==n+2*c+f
    assert f==len(pair.times)*2 and jac.shape==(rows.vectors.size,pair.size)
    assert np.all(rows.residual()[:meta['hard_rows']]<=0) and np.any(rows.residual()[meta['hard_rows']:] >0)
    assert jac[-3*c:,:pair.sizes[0]].nnz and jac[-3*c:,pair.sizes[0]:].nnz


def test_contact_objectives_use_both_serialized_characters(separated,tmp_path):
    models,_=separated;pair=PairKeyGuides(models,[],fit_contacts=True);value=pair.initial.copy();value[:]=np.tile([.005,-.004,.003],4)
    actual={}
    for i,name in enumerate(pair.names):
        path=tmp_path/f'{name}.glb';index=models[name].export(value[pair.offsets[i]:pair.offsets[i+1]],path)
        rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,index);actual[name]=np.array([sampler.sample(float(t)) for t in pair.times])
    predicted=pair.norms(value,pair.worlds(value));observed=pair.norms(value,actual)
    # Rate operations amplify roundoff; use the existing native preview/export
    # agreement budget. Actual acceptance still checks decoded original caps.
    for i,(a,b) in enumerate(zip(predicted,observed)):
        np.testing.assert_allclose(a.vectors,b.vectors,atol=1e-9 if i==0 else 1e-12,rtol=0)
        np.testing.assert_array_equal(a.caps,b.caps)


@pytest.mark.parametrize('choice',[None,1,'true'])
def test_implicit_or_ambiguous_contact_objective_choice_rejects(inputs,choice):
    models,guides=inputs
    with pytest.raises(ValueError,match='boolean'):PairKeyGuides(models,guides,fit_contacts=choice)


def test_missing_authored_contacts_cannot_create_passing_evidence(tmp_path):
    models,guides=make_inputs(tmp_path,contacts_enabled=False)
    with pytest.raises(ValueError,match='Authored contacts required'):PairKeyGuides(models,guides,fit_contacts=True)
