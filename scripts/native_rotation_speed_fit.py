"""Authored native-key speed constraints and fresh serialized-output checks."""
import numpy as np
from scipy.spatial.transform import Rotation
from native_rotation_speed_preflight import SpeedPreflightSceneProblem
from native_scene_fit import SceneProblem
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
