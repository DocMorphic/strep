"""Opt-in clean-prediction scene descent, before the unchanged DDIM sampler.

No denoiser gradients, weight updates, vendor edits or automatic clip adoption.
Descent of a declared energy is not constraint, collision or realism approval.
"""
from contextlib import contextmanager
import inspect
import math
import torch


class ScenePredictionGuide:
    def __init__(self, energy, *, step_l2=.05, iterations=1, active_timesteps=None):
        if (not callable(energy) or type(step_l2) not in (int,float)
                or not math.isfinite(step_l2) or not 0<=step_l2<=1
                or type(iterations) is not int or not 1<=iterations<=4):
            raise ValueError('Callable scene energy and bounded explicit descent settings required')
        if active_timesteps is not None and (not isinstance(active_timesteps,tuple)
                or not active_timesteps or len(set(active_timesteps))!=len(active_timesteps)
                or any(type(t) is not int or not 0<=t<=10000 for t in active_timesteps)):
            raise ValueError('Distinct explicit base-schedule timesteps required')
        self.energy=energy;self.step_l2=float(step_l2);self.iterations=iterations
        self.active_timesteps=active_timesteps;self.records=[];self._installed=False

    def project(self,prediction,valid,observed,timesteps):
        if len(self.records)>=2048:raise ValueError('Complete guidance record budget exhausted')
        if (not isinstance(prediction,torch.Tensor) or prediction.ndim!=3
                or prediction.dtype not in (torch.float32,torch.float64)
                or prediction.numel()>1000000 or not prediction.numel()
                or not torch.isfinite(prediction).all()):
            raise ValueError('Finite bounded floating clean prediction required')
        if (not isinstance(valid,torch.Tensor) or valid.shape!=prediction.shape[:2]
                or valid.dtype!=torch.bool or valid.device!=prediction.device):
            raise ValueError('Complete Boolean valid-frame mask required')
        if observed is not None and (not isinstance(observed,torch.Tensor)
                or observed.shape!=prediction.shape or observed.device!=prediction.device
                or not torch.all((observed==0)|(observed==1))):
            raise ValueError('Complete binary observed-channel mask required')
        if (not isinstance(timesteps,torch.Tensor) or timesteps.shape!=(len(prediction),)
                or timesteps.dtype not in (torch.int32,torch.int64)
                or timesteps.device!=prediction.device or torch.any(timesteps<0)
                or torch.any(timesteps>10000) or not torch.all(timesteps==timesteps[0])):
            raise ValueError('A shared explicit base-schedule timestep required')
        stamp=int(timesteps[0]);record=dict(base_timestep=stamp,accepted_steps=0,trials=[],
            quality_approved=False,release_approved=False)
        if self.step_l2==0 or (self.active_timesteps is not None and stamp not in self.active_timesteps):
            record['reason']='disabled' if self.step_l2==0 else 'outside_declared_schedule'
            self.records.append(record);return prediction
        # The vendor calls its denoiser under inference_mode. Clone outside that
        # mode so geometry autograd can save tensors without touching base graphs.
        with torch.inference_mode(False),torch.enable_grad():
            base=prediction.detach().clone();current=base.clone()
            free=valid.detach().clone()[...,None].expand_as(base).clone()
            if observed is not None:free &= ~observed.detach().clone().bool()
            record['free_channels']=int(free.sum());radius=self.step_l2*self.iterations
            def loss(value):
                result=self.energy(value)
                if (not isinstance(result,torch.Tensor) or result.ndim!=0 or result.device!=value.device
                        or result.dtype!=value.dtype or not torch.isfinite(result) or result<0):
                    raise ValueError('Finite nonnegative scalar scene energy on the prediction device/dtype required')
                return result
            initial=loss(current);record['before_energy']=float(initial.detach())
            for iteration in range(self.iterations):
                variable=current.detach().requires_grad_(True);value=loss(variable)
                derivative=None if not value.requires_grad else torch.autograd.grad(value,variable,allow_unused=True)[0]
                if derivative is None:record['reason']='no_connected_gradient';break
                if not torch.isfinite(derivative).all():raise ValueError('Nonfinite scene gradient')
                derivative=torch.where(free,derivative,0)
                norm=torch.linalg.vector_norm(derivative)
                if norm==0:record['reason']='no_free_gradient';break
                direction=-derivative*(self.step_l2/norm)
                accepted=False
                for fraction in (1.,.5,.25):
                    proposal=torch.where(free,current+fraction*direction,base)
                    delta=float(torch.linalg.vector_norm(proposal-base))
                    candidate=loss(proposal);after=float(candidate.detach())
                    okay=after<float(value.detach()) and delta<=radius and torch.equal(proposal[~free],base[~free])
                    record['trials'].append(dict(iteration=iteration,fraction=fraction,energy=after,delta_l2=delta,accepted=bool(okay)))
                    if okay:current=proposal.detach();record['accepted_steps']+=1;accepted=True;break
                if not accepted:record['reason']='no_decreasing_bounded_proposal';break
            record.update(after_energy=float(loss(current).detach()),delta_l2=float(torch.linalg.vector_norm(current-base)))
            assert torch.equal(current[~free],base[~free]) and record['after_energy']<=record['before_energy'] and record['delta_l2']<=radius
            result=current.detach()
        self.records.append(record);return result


@contextmanager
def scene_guided_denoiser(model,guide):
    """Install only on the caller's CFG wrapper; always remove the hook.

    The complete CFG prediction is adjusted once, not each internal CFG branch.
    Protected values are prediction values, not proof of observed-target accuracy.
    The caller pins the vendor/model/scene and independently validates exports.
    """
    denoiser=getattr(model,'denoiser',None)
    if not isinstance(denoiser,torch.nn.Module) or not isinstance(guide,ScenePredictionGuide) or guide._installed:
        raise ValueError('Caller-owned denoiser and uninstalled scene guide required')
    signature=inspect.signature(denoiser.forward)
    if not {'x_pad_mask','motion_mask','timesteps'}<=set(signature.parameters):
        raise ValueError('Pinned CFG forward mask/timestep interface required')
    if getattr(denoiser,'_strep_scene_guidance',False):raise ValueError('Scene guidance already installed on this denoiser')
    def hook(module,args,kwargs,output):
        bound=signature.bind(*args,**kwargs);bound.apply_defaults();inputs=bound.arguments
        return guide.project(output,inputs['x_pad_mask'],inputs['motion_mask'],inputs['timesteps'])
    handle=denoiser.register_forward_hook(hook,with_kwargs=True)
    guide._installed=True;denoiser._strep_scene_guidance=True
    try:yield guide
    finally:
        handle.remove();guide._installed=False;del denoiser._strep_scene_guidance
