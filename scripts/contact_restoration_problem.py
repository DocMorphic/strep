"""The unchanged frozen motion objective, with separate optional witness rows."""
from pathlib import Path
import numpy as np
from strep import read,sha256
from load_contact_trial import load
from projected_temporal_surface import ProjectedTemporalSurface
from paired_palm_region import contact_records,CorrespondenceEvaluator
from frame_capped_restoration import frame_caps,row_budgets
from screen_path_guard import SCREEN


class FrozenContactProblem:
    def __init__(self,proof):
        proof=Path(proof);preq=read(proof/'request.json');done=read(proof/'completion.json')
        source=Path(preq['source'])
        if (preq['source_request_sha256']!=sha256(source/'request.json') or preq['initial_sha256']!=sha256(source/'initial-parameters.json')
            or done['results_sha256']!=sha256(proof/'results.json') or done['initial_history_sha256']!=sha256(proof/'initial-history.json')):
            raise ValueError('Frozen contact proof changed')
        self.recipe,self.fitter,self.faces,self.initial=load(source)
        self.source=source;self.frames=self.recipe['frames'];self.surfaces=[];self.depths=[];counts=[]
        rows=read(proof/'results.json')['rows'];history=read(proof/'initial-history.json')
        if [r['frame'] for r in rows]!=self.frames or [r['frame'] for r in history['window']]!=self.frames:
            raise ValueError('Frozen contact clock differs')
        if not np.array_equal(self.initial,history['parameters']):raise ValueError('Frozen initializer differs')
        for row,witness in zip(rows,history['window']):
            path=proof/'surfaces'/row['correspondences_file']
            if sha256(path)!=row['correspondences_sha256']:raise ValueError('Frozen correspondence changed')
            saved=read(path)
            if saved['frame']!=row['frame'] or saved['diagnostics']!=witness['collision']:raise ValueError('Frozen diagnostics differ')
            surface=ProjectedTemporalSurface(self.fitter,row['frame'],saved['records'])
            if surface.count!=row['constraints']:raise ValueError('Frozen row count differs')
            self.surfaces.append(surface);counts.append(surface.count);self.depths.append(max(c['max_depth_m'] for c in saved['diagnostics']))
        self.budgets=row_budgets(self.depths,counts,.001,SCREEN['max_sample_penetration_m'])
        self.caps=frame_caps(self.depths,SCREEN['max_sample_penetration_m']);self.count=len(self.budgets)
        if self.count!=done['constraints']:raise ValueError('Frozen population differs')
        self.lower=np.maximum(-self.fitter.bounds,self.initial-np.radians(5))
        self.upper=np.minimum(self.fitter.bounds,self.initial+np.radians(5))
        contact,_=contact_records(self.fitter.base.actors,self.fitter.event,self.fitter.event_map@self.initial,self.faces)
        self.contact=CorrespondenceEvaluator(self.fitter.base,contact);self.cache=None;self.cached=None

    def core(self,value):
        if self.cache is None or not np.array_equal(value,self.cache):
            pairs=[s.clearance(value) for s in self.surfaces]
            self.cached=(np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs]));self.cache=value.copy()
        return self.cached

    def inequalities(self,value,cuts=()):
        pairs=[self.core(value),*[surface.clearance(value) for surface,cap in cuts],self.fitter.step_pair(value)]
        return np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs])

    def objective(self,value):
        fitter=self.fitter;event=fitter.event_map@value
        r,j=fitter.base.objective_pair(event);cr,cj=self.contact.contact(event)
        residual=np.r_[r,cr,(value-self.initial)*.1]
        jac=np.vstack([j@fitter.event_map,cj@fitter.event_map,np.eye(len(value))*.1])
        g,dg=self.core(value)
        # Newly added rows remain inequalities only: never silently reweight
        # the motion objective by duplicating collision residuals.
        residual=np.r_[residual,np.minimum(g,0)*100]
        jac=np.vstack([jac,dg*(g<0)[:,None]*100])
        return .5*float(residual@residual),jac.T@residual

    def augmented_budgets(self,cuts):
        return np.concatenate([self.budgets,*[np.full(s.count,cap+.001) for s,cap in cuts]])
