from pathlib import Path
import sys
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sampled_articulated_track import SampledArticulatedTrack


def track(*,root=True):
    local=torch.eye(3,dtype=torch.float64).repeat(7,4,1,1)
    roots=torch.arange(21,dtype=torch.float64).reshape(7,3)/100
    basis=torch.tensor([[0.,0.],[.25,0.],[.5,.25],[.4,.4],[.25,.5],[0.,.25],[0.,0.]],dtype=torch.float64)
    fixed=torch.tensor([True,False,False,False,False,False,True])
    options=dict(maximum_root_translation_m=.02,root_basis=torch.full((7,2),.5,dtype=torch.float64),root_fixed_frames=torch.zeros(7,dtype=torch.bool)) if root else {}
    return SampledArticulatedTrack(local,roots,basis,[1,3],torch.tensor([.1,.08],dtype=torch.float64),fixed_frames=fixed,**options)


@pytest.mark.parametrize('frames',[[0],[6],[3],[5,1,4],[0,1,2,3,4,5,6]])
@pytest.mark.parametrize('root',[False,True])
def test_original_frame_values_order_and_permissions_match_full_evaluation(frames,root):
    t=track(root=root);c=torch.linspace(-.15,.2,t.size,dtype=torch.float64)
    local,roots=t(c);selected,p=t.at_frames(c,frames)
    torch.testing.assert_close(selected,local[frames],rtol=0,atol=1e-13)
    assert torch.equal(p,roots[frames])
    for i,f in enumerate(frames):
        assert torch.equal(selected[i,[0,2]],t._local[f,[0,2]])
        if f in (0,6):assert torch.equal(selected[i],t._local[f])


def test_sampled_control_jacobian_matches_complete_original_control_columns():
    t=track();c=torch.linspace(-.1,.1,t.size,dtype=torch.float64,requires_grad=True);frames=[1,3,5]
    def packed(x,sampled):
        r,p=t.at_frames(x,frames) if sampled else (t(x)[0][frames],t(x)[1][frames])
        return torch.cat([r.flatten(),p.flatten()])
    a=torch.autograd.functional.jacobian(lambda x:packed(x,True),c)
    b=torch.autograd.functional.jacobian(lambda x:packed(x,False),c)
    assert a.shape==b.shape and a.shape[1]==t.size
    torch.testing.assert_close(a,b,rtol=1e-10,atol=1e-12)
    assert torch.count_nonzero(a[:,-3:])>0


def test_violation_at_an_unrequested_frame_is_not_hidden():
    t=track(root=False);c=torch.full((t.size,),1.9,dtype=torch.float64)
    # Frame0 is fixed, but another original frame exceeds its budget.
    with pytest.raises(ValueError):t.at_frames(c,[0])


@pytest.mark.parametrize('frames',[[],[0,0],[-1],[7],[True],[1.0],[[1]],torch.tensor([1])])
def test_invalid_or_duplicated_clock_selection_rejected(frames):
    t=track()
    with pytest.raises(ValueError):t.at_frames(torch.zeros(t.size,dtype=torch.float64),frames)


def test_inherited_full_path_is_unchanged_and_outputs_do_not_mutate_source():
    t=track();c=torch.zeros(t.size,dtype=torch.float64);before=t(c)
    r,p=t.at_frames(c,[0,3]);r[:]=9;p[:]=9
    after=t(c)
    assert all(torch.equal(a,b) for a,b in zip(before,after))
