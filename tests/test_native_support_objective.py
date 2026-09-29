from pathlib import Path
import sys
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_objective import FixedPatchSupport


def source():
    a=np.zeros((8,3,3));a[:,:,1]=[.001,.008,.05]
    a[:,:,0]=np.arange(8)[:,None]*.001
    return a


def numpy_measure(ref,candidate):
    height=ref[:,:,1].min(1)
    mask=(height[:-1]<.03)&(height[1:]<.03)&(np.linalg.norm(np.diff(ref.mean(1)[:,[0,2]],axis=0),axis=1)*30<.35)
    slides=[];gaps=[]
    for f in np.flatnonzero(mask):
        patch=ref[f,:,1]<height[f]+.01
        slides.append(np.linalg.norm((candidate[f+1,patch]-candidate[f,patch])[:,[0,2]],axis=1).mean()*30)
        gaps.append(max(0,float(candidate[f,patch,1].min())))
    return np.percentile(slides,95),np.percentile(gaps,95)


def test_matches_independent_fixed_reference_patch_percentiles():
    ref=source();candidate=ref.copy();candidate[:,:,0]+=np.arange(8)[:,None]**2*.001
    candidate[:,:,1]+=np.arange(8)[:,None]*.001
    group=FixedPatchSupport(ref,.02);group.loss(torch.tensor(candidate))
    np.testing.assert_allclose(group.peaks,numpy_measure(ref,candidate),rtol=0,atol=1e-15)
    assert group.last[0]>0


def test_source_passes_with_finite_gradients_and_reference_is_frozen():
    ref=source();group=FixedPatchSupport(ref,.02);ref[:]=5
    candidate=torch.tensor(source(),requires_grad=True);loss=group.loss(candidate)
    assert loss==0 and torch.isfinite(torch.autograd.grad(loss,candidate)[0]).all()


def test_unselected_high_patch_vertex_does_not_change_measurement():
    ref=source();candidate=ref.copy();candidate[:,2,:]=100
    group=FixedPatchSupport(ref,.02)
    assert group.loss(torch.tensor(candidate))==0


def test_gap_and_hand_slide_allowance_are_distinct():
    ref=source();candidate=ref.copy();candidate[:,:,0]+=np.arange(8)[:,None]*.0015
    assert FixedPatchSupport(ref,.02).loss(torch.tensor(candidate))>0
    assert FixedPatchSupport(ref,.08).loss(torch.tensor(candidate))==0
    candidate[:,:,1]+=.016
    assert FixedPatchSupport(ref,.08).loss(torch.tensor(candidate))>0


def test_fewer_than_three_support_intervals_do_not_gain_constraints():
    ref=source()[:3];group=FixedPatchSupport(ref,.02);candidate=ref.copy();candidate[:,:,1]+=1
    assert not group.enabled and group.loss(torch.tensor(candidate))==0


def test_gradients_and_multiplier_updates():
    ref=source();group=FixedPatchSupport(ref,.02)
    candidate=ref.copy();candidate[:,:,0]+=np.arange(8)[:,None]**2*.001;candidate[:,:,1]+=np.arange(8)[:,None]*.007
    variable=torch.tensor(candidate,requires_grad=True)
    assert torch.autograd.gradcheck(group.loss,(variable,),atol=1e-4)
    group.loss(variable);group.advance_stage(4)
    assert (group.multiplier>0).all() and group.penalty==40


def test_no_support_is_finite_and_disabled():
    ref=source();ref[:,:,1]+=1;group=FixedPatchSupport(ref,.02)
    assert not group.enabled and group.loss(torch.tensor(ref))==0 and group.record()['limits'] is None


def test_invalid_inputs_and_update_rejected():
    for ref in [source()[:1],source()*float('nan'),np.zeros((8,0,3))]:
        with pytest.raises(ValueError):FixedPatchSupport(ref,.02)
    with pytest.raises(ValueError):FixedPatchSupport(source(),0)
    group=FixedPatchSupport(source(),.02)
    with pytest.raises(ValueError):group.advance_stage(4)
    with pytest.raises(ValueError):group.loss(torch.tensor(source()).float())
    with pytest.raises(ValueError):group.advance_stage(float('nan'))
