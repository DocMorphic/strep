"""Reusable complete scene model centered on verified stored actor clips.

Only proposal curves change. Original caps, references, contacts, placements,
object trajectories and geometry policy remain the acceptance contract.
"""
import copy,hashlib,json
import numpy as np
from native_scene_fit import SceneProblem
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import policy_for
from native_scene_norms import rows
from native_pair_surface_model import model as pair_model, METHODS as PAIR_METHODS
from rig_asset import RigAsset

METHODS=tuple(dict.fromkeys(PAIR_METHODS+('native_scene_fit.py','native_rotation_storage_repair.py',
    'native_stored_curve_proxy.py','native_stored_pair_model.py')))


def centered_problem(problem,value,files,guide_scene,policy,digest,*,source_policy):
    if not isinstance(problem,SceneProblem) or not isinstance(problem.edits,StorageAdjustedEdits):
        raise ValueError('Explicit scene problem and storage-adjusted authoring contract required')
    problem.scene.check_inputs();guide_scene.check_inputs()
    original_digest=problem.edits.request['permissions']['contacts_sha256']
    original_times,_,_=policy_for(source_policy,problem.scene,original_digest)
    times,_,_=policy_for(policy,guide_scene,digest)
    if ({k:v for k,v in source_policy.items() if k!='contacts_sha256'}
            !={k:v for k,v in policy.items() if k!='contacts_sha256'}
            or not np.array_equal(times,original_times)):
        raise ValueError('Original complete geometry clock, limits and planes must be preserved')
    if not np.isin(times,problem.times).all():
        raise ValueError('Include every geometry time in the original problem before centering')
    if (problem.scene.duration!=guide_scene.duration or set(problem.scene.actors)!=set(guide_scene.actors)
            or set(problem.scene.objects)!=set(guide_scene.objects)):
        raise ValueError('Guide must preserve complete source scene participants and duration')
    for name,source in problem.scene.objects.items():
        target=guide_scene.objects[name]
        if source['geometry']!=target['geometry'] or any(not np.array_equal(source[k],target[k])
                for k in ('times','positions','rotations')):
            raise ValueError('Guide must preserve original object geometry and trajectory')
    if len(problem.scene.rows)!=len(guide_scene.rows) or any(
            a['authored']!=b['authored'] or not np.array_equal(a['ids'],b['ids'])
            or not np.array_equal(a['target_ids'],b['target_ids'])
            for a,b in zip(problem.scene.rows,guide_scene.rows)):
        raise ValueError('Guide must preserve every original contact condition and reference')
    proxy=StoredCurveProxy(problem.edits,value,files)
    for name,source in problem.scene.actors.items():
        target=guide_scene.actors[name]
        expected=RigAsset.load(proxy.files[name]) if name in proxy.files else source['rig']
        if (target['animation_index']!=source['animation_index']
                or any(not np.array_equal(a,b) for a,b in zip(source['placement'],target['placement']))
                or expected.document!=target['rig'].document or expected.binary!=target['rig'].binary):
            raise ValueError('Guide actor must match its exact stored anchor, source placement and animation')
    residual,decoded=problem.decoded(proxy.files,value)
    for name,actor in problem.scene.actors.items():
        if name not in proxy.files:
            actual=np.array([actor['sampler'].sample(float(t)) for t in problem.times])
            if not np.array_equal(actual,decoded[name]):
                raise ValueError('Unedited actor playback must match its actual source clip; '
                    'reference worlds cannot replace frozen playback')
    centered=copy.copy(problem);centered.edits=proxy
    smooth=centered.worlds(value,quantized=False)
    errors={name:float(abs(smooth[name]-decoded[name]).max()) for name in decoded}
    for name in decoded:np.testing.assert_allclose(smooth[name],decoded[name],atol=2e-12,rtol=0)
    a,b=rows(problem,value,decoded),rows(centered,value,decoded)
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(a,key),getattr(b,key))
    contract=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    report=dict(schema='strep-native-stored-pair-centering-v1',editor_binding=proxy.editor_binding,
        anchor_sha256=proxy.hashes,source_policy_contract_sha256=contract(source_policy),
        guide_policy_contract_sha256=contract(policy),native_samples=len(problem.times),geometry_samples=len(times),
        maximum_centered_world_difference=errors,decoded_native_failures=int((residual>0).sum()),
        centered_native_failures=int((centered.constraints(value,smooth)>0).sum()),
        original_scene_and_acceptance_preserved=True,quality_approved=False,release_approved=False,
        scope='Verified stored-anchor proposal centering; no correction or native/geometry quality approval.')
    return centered,decoded,report


def model(problem,value,files,guide_scene,policy,digest,trust,*,source_policy,step=.001,
          maximum_rows=400000,maximum_nonzeros=60000000,clearance=0.,difference_scheme='central'):
    centered,decoded,centering=centered_problem(problem,value,files,guide_scene,policy,digest,
        source_policy=source_policy)
    native,jac,guides,gaps,surface,report=pair_model(centered,value,guide_scene,policy,digest,trust,
        step=step,maximum_rows=maximum_rows,maximum_nonzeros=maximum_nonzeros,decoded_worlds=decoded,
        clearance=clearance,difference_scheme=difference_scheme)
    report=dict(report,stored_pair_centering=centering,derivative_proxy='verified-stored-anchor',
        original_scene_and_acceptance_preserved=True)
    return centered,native,jac,guides,gaps,surface,report
