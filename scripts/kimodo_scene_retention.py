"""Optional per-metric retention around the existing scene-energy proposal."""
import torch
from kimodo_scene_guidance import ScenePredictionGuide
from scene_metric_retention import compare_metrics,snapshot_metrics


class MetricRetainedSceneGuide(ScenePredictionGuide):
    def __init__(self,energy,metrics,**settings):
        if not callable(metrics):raise ValueError('Complete explicit scene/motion metric evaluator required')
        super().__init__(energy,**settings);self.metrics=metrics

    def project(self,prediction,valid,observed,timesteps):
        proposed=super().project(prediction,valid,observed,timesteps);record=self.records[-1]
        record['energy_proposal_accepted_steps']=record['accepted_steps']
        if not record['accepted_steps']:
            record['metric_retention']='no_energy_proposal';return prediction
        with torch.inference_mode(False),torch.no_grad():
            base=prediction.detach().clone();delta=proposed.detach().clone()-base
            free=valid.detach().clone()[...,None].expand_as(base).clone()
            if observed is not None:free &= ~observed.detach().clone().bool()
            baseline=snapshot_metrics(self.metrics(base));trials=[];chosen=None;fraction=None
            for scale in (1.,.5,.25):
                candidate=torch.where(free,base+scale*delta,base)
                loss=self.energy(candidate)
                if not isinstance(loss,torch.Tensor) or loss.ndim!=0 or loss.dtype!=base.dtype or loss.device!=base.device or not torch.isfinite(loss) or loss<0:raise ValueError('Finite nonnegative retained scene energy required')
                comparison=compare_metrics(baseline,self.metrics(candidate))
                okay=bool(comparison['all_metrics_nonregressing'] and float(loss)<record['before_energy'])
                trials.append(dict(fraction=scale,energy=float(loss),metrics=comparison,accepted=okay))
                if okay:chosen=candidate.detach();fraction=scale;break
            record['energy_trials']=record.pop('trials');record['metric_trials']=trials;record['retained_fraction']=fraction
            if chosen is None:
                record.update(metric_retention='rejected',accepted_steps=0,after_energy=record['before_energy'],delta_l2=0.)
                return prediction
            record.update(metric_retention='accepted',after_energy=trials[-1]['energy'],delta_l2=float(torch.linalg.vector_norm(chosen-base)))
            return chosen
