"""Authored native-key speed constraints and fresh serialized-output checks."""
import copy
import numpy as np
from scipy.optimize import lsq_linear
from scipy.spatial.transform import Rotation,Slerp
from native_rotation_speed_preflight import SpeedPreflightSceneProblem
from native_scene_fit import SceneProblem,optimize
from native_support_feasibility import merit
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from temporal_rotation_bounds import numeric


def serialized_rates(quaternions,clock):
    """Separate quaternion arithmetic, without SciPy's relative-angle decoder."""
    q=numeric(quaternions,'serialized quaternions');t=numeric(clock,'native clock')
    if q.ndim!=2 or q.shape[1]!=4 or not 2<=len(q)<=20000 or t.shape!=(len(q),) or t[0]<0 or np.any(np.diff(t)<=0):
        raise ValueError('Complete bounded XYZW keys and increasing native clock required')
    lengths=np.linalg.norm(q,axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths==0):raise ValueError('Nonzero representable quaternion lengths required')
    q=q/lengths[:,None];a,b=q[:-1],q[1:]
    vector=a[:,3,None]*b[:,:3]-b[:,3,None]*a[:,:3]-np.cross(a[:,:3],b[:,:3])
    scalar=np.sum(a*b,axis=1)
    angle=2*np.rad2deg(np.arctan2(np.linalg.norm(vector,axis=1),abs(scalar)))
    with np.errstate(over='raise',divide='raise',invalid='raise'):
        try:return angle/np.diff(t)
        except FloatingPointError as error:raise ValueError('Representable serialized speeds required') from error


class SpeedLimitedSceneProblem(SpeedPreflightSceneProblem):
    """All original scene constraints plus authored local-key rotation speeds."""
    def __init__(self,scene,edits,*,rotation_speed_limits):
        super().__init__(scene,edits,rotation_speed_limits=rotation_speed_limits)
        self.speed_tracks=[]
        for report in self.speed_preflight['tracks']:
            name,node=report['actor'],report['node']
            channel=next(c for c in scene.actors[name]['sampler'].channels if c[:2]==(node,'rotation'))
            self.speed_tracks.append(dict(actor=name,node=node,clock=channel[2].copy(),source=channel[3].copy(),
                limit=float(rotation_speed_limits[name,node])))

    def speed_rows(self,value):
        values={name:self.edits.values(name,value) for name in self.edits.actors};rows=[]
        for track in self.speed_tracks:
            q=values.get(track['actor'],{}).get((track['node'],'rotation'),track['source'])
            r=Rotation.from_quat(q)
            rates=np.rad2deg((r[:-1].inv()*r[1:]).magnitude())/np.diff(track['clock'].astype(float))
            rows.append((rates-track['limit'])/max(track['limit'],1.))
        return np.concatenate(rows)

    def model(self,value):
        return np.r_[SceneProblem.model(self,value),self.speed_rows(value)]

    def audit_outputs(self,files):
        if not isinstance(files,dict) or set(files)!=set(self.edits.actors):
            raise ValueError('One fresh exported file for every edited actor required')
        readers={};edit_audits={}
        for name,path in files.items():
            index=self.scene.actors[name]['animation_index']
            edit_audits[name]=self.edits.audit(name,path,index)
            rig=RigAsset.load(path);readers[name]=NativeSupportSampler(rig.document,rig.binary,index)
        reports=[];rows=[]
        for track in self.speed_tracks:
            name,node=track['actor'],track['node']
            reader=readers.get(name,self.scene.actors[name]['sampler'])
            channels=[c for c in reader.channels if c[:2]==(node,'rotation')]
            if len(channels)!=1 or channels[0][4]!='LINEAR' or not np.array_equal(channels[0][2],track['clock']):
                raise ValueError('Serialized native channel/clock changed')
            rates=serialized_rates(channels[0][3],channels[0][2]);failed=rates>track['limit']
            peak=int(np.argmax(rates));rows.append((rates-track['limit'])/max(track['limit'],1.))
            reports.append(dict(actor=name,node=node,limit_degrees_per_second=track['limit'],
                rates_degrees_per_second=rates.tolist(),native_times_s=track['clock'].astype(float).tolist(),
                neighbor_comparisons=len(rates),failed_neighbors=int(failed.sum()),maximum_speed_degrees_per_second=float(rates[peak]),
                maximum_interval=peak,passed=not bool(failed.any())))
        return np.concatenate(rows),dict(schema='strep-native-rotation-speed-output-v1',tracks=reports,edit_audits=edit_audits,
            passed=all(t['passed'] for t in reports) and all(a['passed'] for a in edit_audits.values()),
            all_selected_native_neighbors_checked=True,speed_acceptance_allowance_degrees_per_second=0.,
            continuous_time_verified=False,quality_approved=False,release_approved=False,
            scope='Fresh serialized local rotation keys, independently normalized quaternion relative-angle arithmetic, every selected native neighbor and unchanged clock, plus original edit/static/frozen-key audit. Limits are authored; these sampled checks do not establish instantaneous interpolation speeds, anatomy, full geometry, forces, engine fidelity or quality.')

    def decoded(self,files,value):
        original,worlds=SceneProblem.decoded(self,files,value)
        speed,report=self.audit_outputs(files)
        # A failed payload/edit audit is an export contract violation, not a
        # residual that optimization may trade against a contact improvement.
        if not all(a['passed'] for a in report['edit_audits'].values()):
            raise ValueError('Serialized output exceeds original native edit permissions')
        self.last_speed_output_audit=report
        return np.r_[original,speed],worlds


def speed_seed(problem):
    """Bounded control proposal following shortest arcs between frozen keys.

    This is guidance, not a contact-feasible or speed-feasible certificate. The
    serialized complete scene residual must accept it before it becomes a start.
    """
    if not isinstance(problem,SpeedLimitedSceneProblem):raise ValueError('Speed-limited scene problem required')
    value=problem.initial.copy();reports=[]
    for track in problem.speed_tracks:
        actor=problem.edits.actors.get(track['actor'])
        entry=None if actor is None else next((e for e in actor['tracks'] if (e['node'],e['path'])==(track['node'],'rotation')),None)
        if entry is None:continue
        clock=track['clock'].astype(float);source=Rotation.from_quat(track['source'])
        frozen=np.ones(len(clock),bool);frozen[entry['ids']]=False;anchors=np.flatnonzero(frozen)
        if len(anchors)<2:
            anchor=int(anchors[0]) if len(anchors) else 0
            target=Rotation.from_quat(np.tile(source[anchor].as_quat(),(len(entry['ids']),1)))
        else:
            times=np.clip(clock[entry['ids']],clock[anchors[0]],clock[anchors[-1]])
            target=Slerp(clock[anchors],source[anchors])(times)
        wanted=(source[entry['ids']].inv()*target).as_rotvec()/entry['unit']
        controls=np.column_stack([lsq_linear(entry['weights'],wanted[:,axis],bounds=(-1.,1.),
            tol=1e-10,max_iter=100).x for axis in range(3)])
        peak=float(np.linalg.norm(entry['weights']@controls,axis=1).max(initial=0))
        if peak>1:controls/=peak
        value[entry['controls']]=controls
        reports.append(dict(actor=track['actor'],node=track['node'],frozen_anchors=anchors.tolist(),
            radial_rescaling=peak if peak>1 else 1.,guidance='Shortest rotation arcs between frozen keys; nearest anchor outside them; constant source anchor if fewer than two'))
    return value,dict(tracks=reports,quality_approved=False,feasibility_claimed=False)


def optimize_speed_limited(problem,evaluate,*,iterations=8,trust=.02):
    """Try a fully decoded smoothing seed, then the existing bounded optimizer."""
    if type(iterations) is not int or not 1<=iterations<=16 or type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=1:
        raise ValueError('Choose 1-16 iterations and finite normalized trust in (0,1]')
    original=problem.initial.copy();before=evaluate(original,'speed-original');seed,proposal=speed_seed(problem)
    candidate=evaluate(seed,'speed-seed');a,b=merit(before),merit(candidate)
    improved=b[0]<a[0]-1e-12 or abs(b[0]-a[0])<=1e-12 and b[1]<a[1]-1e-15
    accepted=bool(np.max(candidate)<=0 and improved)
    local=copy.copy(problem);local.initial=seed.copy() if accepted else original
    value,fit=optimize(local,evaluate,iterations,trust)
    fit.update(seed_accepted=bool(accepted),seed_before_merit=list(a),seed_after_merit=list(b),seed_proposal=proposal,
        complete_decoded_scene_acceptance=True,speed_seed_is_guidance_only=True)
    return value,fit
