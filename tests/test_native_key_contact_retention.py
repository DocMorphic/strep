"""Contact completion must survive decoded retention even at zero soft merit."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_key_interval_restoration import retain,evaluate,build_problem,run,SCHEMA
from native_scene_contacts import SceneContacts
from strep import save,read,sha256
from test_native_key_interval_restoration import geometry,observed
from test_native_affine_key_pose import affine_setup


def test_completing_contact_prefix_counts_as_progress_at_equal_zero_soft_merit():
    before=observed(geometry((.004,.002)),rate=-.1,prefix=False)
    after=observed(geometry((.004,.002)),rate=-.1,prefix=True)
    assert before['record']['score']==after['record']['score']==[0.,0.,0]
    assert retain(before,after)


def test_passing_unchanged_clip_does_not_invent_contact_progress():
    before=observed(geometry((.004,.002)),rate=-.1,prefix=True)
    assert not retain(before,copy.deepcopy(before))


@pytest.mark.parametrize('fault',['contact','new-floor','worse-floor','rate','face'])
def test_contact_completion_never_excuses_another_failed_or_worsened_condition(fault):
    before=observed(geometry((.004,.002)),rate=-.1,prefix=False)
    after=observed(geometry((.004,.002)),rate=-.1,prefix=True)
    if fault=='contact':after['record']['decoded_prefix_pass']=False
    elif fault=='new-floor':after=observed(geometry((.006,.002)),rate=-.1,prefix=True)
    elif fault=='worse-floor':
        before=observed(geometry((.007,.002)),rate=-.1,prefix=False)
        after=observed(geometry((.0071,.002)),rate=-.1,prefix=True)
    elif fault=='rate':after=observed(geometry((.004,.002)),rate=.01,prefix=True)
    else:
        report=geometry((.004,.002));report['samples'][0]['degenerate_faces']['A']=[1]
        after=observed(report,rate=-.1,prefix=True)
    assert not retain(before,after)


def test_real_native_contact_only_repair_exports_is_retained_and_replays(tmp_path,monkeypatch):
    from native_key_contact_initializer import encode
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    from audit_native_key_restoration import run as replay
    import native_key_interval_restoration as restoration
    _,scene,contacts,policy,authoring=affine_setup(tmp_path)
    actor=scene.actors['A'];channel=next(c for c in actor['sampler'].channels if c[:2]==(3,'rotation'))
    clock=channel[2];controls=np.zeros((len(clock),1,3));controls[:,:,2]=.01
    candidate=tmp_path/'known-contact-pose.glb'
    index=encode(actor['rig'],actor['animation_index'],[3],[channel],controls,[30.],candidate)
    spec=read(contacts);measurement=copy.deepcopy(spec);measurement['actors']['A'].update(glb=str(candidate),sha256=sha256(candidate),animation_index=index)
    measured=SceneContacts(measurement,tmp_path);row=measured.rows[0]
    target=measured.actor_points('A',row['ids'],np.array([1.])).mean(1)[0]
    spec['contacts'][0].update(reduction='centroid',target=dict(space='world',points_m=[target.tolist()]),limits=dict(position_m=.0001))
    save(contacts,spec);policy['contacts_sha256']=authoring['contacts_sha256']=sha256(contacts)
    authoring.update(boundary_keys=dict(start='edit',end='edit'),acknowledge_changed_boundary_compatibility=True,frozen_times_s=[])
    paths=dict(contacts=contacts,geometry=tmp_path/'geometry.json',request=tmp_path/'authoring.json',controls=tmp_path/'controls.npz')
    save(paths['geometry'],policy);save(paths['request'],authoring)
    np.savez_compressed(paths['controls'],times_s=clock,controls=np.zeros_like(controls))
    recipe=dict(schema=SCHEMA,seed={k:dict(path=str(p),sha256=sha256(p)) for k,p in paths.items()},active_keys=list(range(len(clock))),
        iterations=1,trust=.02,difference_step=.001,backoffs=1,maximum_seconds=60.)
    declaration=tmp_path/'recipe.json';save(declaration,recipe)
    problem=build_problem(recipe,declaration,tmp_path/'reference-seed')
    before=evaluate(problem,problem.initial,tmp_path/'before');other=controls[problem.active].ravel()
    after=evaluate(problem,other,tmp_path/'after')
    assert not before['record']['decoded_prefix_pass'] and after['record']['sampled_conditions_pass']
    assert before['record']['score']==after['record']['score']==[0.,0.,0]
    assert retain(before,after)
    # Supply a known feasible proposal; acceptance, native export, complete
    # geometry/rate observations and replay execute their real implementations.
    monkeypatch.setattr(restoration,'direction',lambda *a,**kw:(other-problem.initial,dict(status='KnownFixtureProposal')))
    output=tmp_path/'job';result=run(declaration,output)
    assert result['sampled_conditions_pass'] and result['history'][0]['accepted_fraction']==1.
    assert not result['quality_approved'] and not result['release_approved']
    proof=replay(output,tmp_path/'replay',sha256(output/'result.json'),sha256(output/'request.json'))
    assert proof['retention_history_replayed'] and proof['sampled_conditions_pass'] and not proof['optimizer_executed']
