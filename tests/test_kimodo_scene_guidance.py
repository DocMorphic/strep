"""CPU tensor tests; no vendor checkout, model, GPU, asset or download."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from kimodo_scene_guidance import ScenePredictionGuide,scene_guided_denoiser
from kimodo_skin_scene_energy import SkinSceneEnergy
from linear_skin_operator import LinearSkinOperator


def inputs():
    x=torch.arange(12,dtype=torch.float64).reshape(1,3,4)/10
    return x,torch.tensor([[True,True,False]]),torch.zeros_like(x,dtype=torch.bool),torch.tensor([2])


def test_disabled_is_exact_passthrough_without_energy_or_rng_use():
    x,valid,mask,t=inputs();calls=[];state=torch.get_rng_state().clone()
    guide=ScenePredictionGuide(lambda _:calls.append(1),step_l2=0)
    assert guide.project(x,valid,mask,t) is x and not calls and torch.equal(state,torch.get_rng_state())


def test_schedule_is_base_timestep_and_outside_passes_through():
    x,v,m,t=inputs();guide=ScenePredictionGuide(lambda q:q.square().sum(),active_timesteps=(0,))
    assert guide.project(x,v,m,t) is x and guide.records[-1]['reason']=='outside_declared_schedule'


def test_free_descent_preserves_observed_and_padding_bits_and_source():
    x,v,m,t=inputs();m[0,0,1]=True;x[0,0,1]=-0.;old=x.clone();guide=ScenePredictionGuide(lambda q:(q-2).square().sum(),iterations=2)
    y=guide.project(x,v,m,t);protected=m|~v[...,None]
    assert torch.equal(y[protected].view(torch.int64),old[protected].view(torch.int64)) and torch.equal(x,old)
    assert ((y-2)**2).sum()<((x-2)**2).sum() and not y.requires_grad and guide.records[-1]['delta_l2']<=.1


def test_inference_tensor_can_enter_geometry_autograd():
    with torch.inference_mode():
        x,v,m,t=inputs();guide=ScenePredictionGuide(lambda q:q.square().sum());y=guide.project(x,v,m,t)
    assert y.square().sum()<x.square().sum() and guide.records[-1]['accepted_steps']>0


def test_disconnected_and_fully_protected_inputs_report_no_change():
    x,v,m,t=inputs();guide=ScenePredictionGuide(lambda q:q.new_tensor(1.))
    assert torch.equal(guide.project(x,v,m,t),x) and guide.records[-1]['reason']=='no_connected_gradient'
    guide=ScenePredictionGuide(lambda q:q.square().sum());m[:]=True
    assert torch.equal(guide.project(x,v,m,t),x) and guide.records[-1]['reason']=='no_free_gradient'


def test_non_decreasing_callback_cannot_keep_a_wrong_gradient():
    x,v,m,t=inputs()
    # Positive value with a deliberately wrong straight-through derivative.
    def bad(q):return 10-q.square().sum()+2*(q.square().sum()-q.square().sum().detach())
    guide=ScenePredictionGuide(bad);assert torch.equal(guide.project(x,v,m,t),x)
    assert len(guide.records[-1]['trials'])==3 and not any(r['accepted'] for r in guide.records[-1]['trials'])


@pytest.mark.parametrize('fault',['nan','negative','vector','detached_nan_gradient','bad_valid','bad_observed','bad_timestep'])
def test_invalid_energy_masks_and_timing_reject(fault):
    x,v,m,t=inputs();energy=lambda q:q.square().sum()
    if fault=='nan':energy=lambda q:q.sum()*float('nan')
    if fault=='negative':energy=lambda q:q.sum()*0-1
    if fault=='vector':energy=lambda q:q.sum(0)
    if fault=='detached_nan_gradient':energy=lambda q:torch.sqrt(q[0,0,0]).square()
    if fault=='bad_valid':v=v.float()
    if fault=='bad_observed':m=m.float()+.1
    if fault=='bad_timestep':t=t.float()
    with pytest.raises(ValueError):ScenePredictionGuide(energy).project(x,v,m,t)


class FakeCFG(torch.nn.Module):
    def __init__(self):super().__init__();self.weight=torch.nn.Parameter(torch.tensor(1.));self.calls=0
    def forward(self,cfg_weight,x,x_pad_mask,text_feat,text_feat_pad_mask,timesteps,first_heading_angle=None,motion_mask=None,observed_motion=None,cfg_type=None):
        self.calls+=1;return x*self.weight


def test_hook_applies_after_one_cfg_call_and_restores_on_exception():
    denoiser=FakeCFG();model=SimpleNamespace(denoiser=denoiser);guide=ScenePredictionGuide(lambda q:q.square().sum())
    x,v,m,t=inputs();old=denoiser.weight.detach().clone()
    with pytest.raises(RuntimeError,match='owned failure'):
        with scene_guided_denoiser(model,guide):
            with torch.inference_mode():out=denoiser(2,x,v,None,None,t,motion_mask=m)
            assert out.square().sum()<x.square().sum() and denoiser.calls==1
            with pytest.raises(ValueError):
                with scene_guided_denoiser(model,guide):pass
            raise RuntimeError('owned failure')
    assert not denoiser._forward_hooks and not guide._installed and torch.equal(old,denoiser.weight) and denoiser.weight.grad is None
    assert torch.equal(denoiser(2,x,v,None,None,t),x)


def skin():
    ids=torch.tensor([[0,1],[0,1]])
    weights=torch.tensor([[.25,.75],[.6,.4]],dtype=torch.float64)
    bind=torch.tensor([[[0.,0.,0.],[.2,0.,0.]],[[.5,0.,0.],[.5,0.,0.]]],dtype=torch.float64)
    return LinearSkinOperator(ids,weights,bind,2)


def decode(features):
    p=features[...,:6].reshape(1,-1,2,3)
    r=torch.eye(3,dtype=features.dtype).expand(1,features.shape[1],2,3,3)
    return dict(global_rot_mats=r,posed_joints=p)


@pytest.mark.parametrize('chunk',[1,2,4])
def test_complete_skin_floor_energy_and_gradients_match_gathered_reference(chunk):
    op=skin();x=torch.tensor([[[0.,-.2,0.,0.,-.1,0.]]*5],dtype=torch.float64,requires_grad=True)
    energy=SkinSceneEnergy(decode,op,planes=[(torch.tensor([0.,1.,0.],dtype=x.dtype),0.)],frame_chunk=chunk)
    actual=energy(x);ga=torch.autograd.grad(actual,x)[0]
    point=x.detach().clone().requires_grad_(True);p=point[...,:6].reshape(5,2,3)
    vertices=torch.stack([.25*p[:,0]+.75*(p[:,1]+point.new_tensor([.2,0,0])),.6*(p[:,0]+point.new_tensor([.5,0,0]))+.4*(p[:,1]+point.new_tensor([.5,0,0]))],1)
    expected=torch.relu(-vertices[...,1]).square().mean();gb=torch.autograd.grad(expected,point)[0]
    torch.testing.assert_close(actual,expected);torch.testing.assert_close(ga,gb)
    assert torch.count_nonzero(ga[:, -1])>0


def test_convex_box_and_contact_terms_include_every_vertex_frame_and_target():
    op=skin();x=torch.zeros((1,3,6),dtype=torch.float64,requires_grad=True)
    normals=torch.cat([torch.eye(3,dtype=x.dtype),-torch.eye(3,dtype=x.dtype)]).expand(3,6,3).clone()
    offsets=torch.ones((3,6),dtype=x.dtype);target=torch.zeros((3,1,3),dtype=x.dtype);target[-1,0,0]=.9
    energy=SkinSceneEnergy(decode,op,convex_objects=[(normals,offsets)],contacts=[(torch.tensor([1]),target)],frame_chunk=2)
    expected=((.85**2+.5**2)/2)+(.5**2+.5**2+.4**2)/3
    assert float(energy(x))==pytest.approx(expected)
    derivative=torch.autograd.grad(energy(x),x)[0];assert torch.isfinite(derivative).all() and torch.count_nonzero(derivative[:, -1])>0
    target[:]=100;assert float(energy(x))==pytest.approx(expected)


@pytest.mark.parametrize('fault',['empty','nonunit','wrong_clock','grad_target','vertex'])
def test_invalid_scene_terms_cannot_silently_lose_constraints(fault):
    op=skin();normal=torch.tensor([0.,1.,0.],dtype=torch.float64);kwargs={}
    if fault=='nonunit':kwargs['planes']=[(normal*2,0.)]
    elif fault in ('wrong_clock','grad_target','vertex'):
        target=torch.zeros((2,1,3),dtype=torch.float64,requires_grad=fault=='grad_target')
        kwargs['contacts']=[(torch.tensor([2 if fault=='vertex' else 0]),target)]
    with pytest.raises(ValueError):
        obj=SkinSceneEnergy(decode,op,**kwargs)
        if fault=='wrong_clock':obj(torch.zeros((1,3,6),dtype=torch.float64))
