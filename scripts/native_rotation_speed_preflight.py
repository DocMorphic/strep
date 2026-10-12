"""Necessary speed checks against actual native scene edit permissions."""
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from temporal_rotation_bounds import assess, numeric

# Match the existing exported-rotation audit rather than silently tightening it.
SERIALIZATION_ALLOWANCE_DEGREES = .0001


def assess_scene(edits, limits):
    """Return complete per-track bounds and a JSON-compatible diagnostic."""
    from native_rotation_storage_repair import StorageAdjustedEdits
    if isinstance(edits,StorageAdjustedEdits):
        if hasattr(edits,'check_continuation'):edits.check_continuation()
        edits=edits.base  # Original permissions/source, never corrected keys as a new epoch.
    if not isinstance(edits, SceneEdits):
        raise ValueError('Validated native scene edits required')
    if not isinstance(limits, dict) or not limits or len(limits)>64:
        raise ValueError('Explicit speed limits for 1-64 actor/joint tracks required')
    bounds = {}; reports = []
    for key, limit in limits.items():
        if not isinstance(key,tuple) or len(key)!=2:
            raise ValueError('Speed limit key must be (actor, joint node)')
        name,node = key
        if not isinstance(name,str) or name not in edits.scene.actors or type(node) is not int:
            raise ValueError('Known actor and integer joint node required')
        actor = edits.scene.actors[name]
        if node not in actor['rig'].joints:
            raise ValueError('Speed limit must select a skin joint')
        channels = [c for c in actor['sampler'].channels if c[:2]==(node,'rotation')]
        if len(channels)!=1 or channels[0][4]!='LINEAR':
            raise ValueError('One existing LINEAR rotation channel required')
        _,_,clock,source,_ = channels[0]
        quaternions = numeric(source,'native quaternions')
        norms = np.linalg.norm(quaternions,axis=1)
        if quaternions.shape!=(len(clock),4) or np.any(norms==0):
            raise ValueError('Complete nonzero native XYZW quaternions required')
        # glTF decoding normalizes quaternions; record that interpretation.
        rotations = Rotation.from_quat(quaternions/norms[:,None]).as_matrix()
        caps = np.zeros((len(clock),1))
        state = edits.actors.get(name)
        entry = None if state is None else next((e for e in state['tracks'] if (e['node'],e['path'])==(node,'rotation')),None)
        if entry is not None:
            caps[entry['ids'],0] = entry['maximum'] + SERIALIZATION_ALLOWANCE_DEGREES
        lower,report = assess(rotations[:,None],clock,caps,
            speed_limits_degrees_per_second=numeric([limit],'authored speed limit'))
        bounds[key] = lower[:,0]
        report.update(actor=name,node=node,native_times_s=np.asarray(clock,float).tolist(),
            permitted_edit_caps_degrees=caps[:,0].tolist(),
            quaternion_normalization_max_length_change=float(np.max(abs(norms-1))),
            serialization_allowance_degrees=SERIALIZATION_ALLOWANCE_DEGREES,
            frozen_keys_have_zero_allowance=True)
        reports.append(report)
    return bounds,dict(schema='strep-native-rotation-speed-preflight-v1',tracks=reports,
        speed_limits_proven_incompatible=any(r['speed_limits_proven_incompatible'] for r in reports),
        source_changed=False,quality_approved=False,release_approved=False,
        scope='Every native neighboring key of the selected LINEAR rotation tracks, including protected keys and boundaries. Bounds use the existing final audit norm caps plus its serialization allowance. This is a preflight rejection only; non-exclusion neither enforces the requested speed on a fitted output nor proves a globally feasible trajectory, contact, dynamics or continuous-time quality.')


class IncompatibleRotationSpeed(ValueError):
    def __init__(self,report):
        self.report = report
        super().__init__('Authored rotation speed limits conflict with permitted native edits; scene fitting not initialized')


class SpeedPreflightSceneProblem(SceneProblem):
    """Opt-in preflight before the existing expensive scene populations build."""
    def __init__(self,scene,edits,*,rotation_speed_limits):
        if scene is not edits.scene:
            raise ValueError('Speed preflight and fitting must use the same scene')
        self.speed_lower_bounds,self.speed_preflight = assess_scene(edits,rotation_speed_limits)
        if self.speed_preflight['speed_limits_proven_incompatible']:
            raise IncompatibleRotationSpeed(self.speed_preflight)
        super().__init__(scene,edits)
