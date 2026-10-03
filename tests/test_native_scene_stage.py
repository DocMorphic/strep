"""Common placement, fixed planes and immutable native motion for scene proposals."""
import copy
import json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture, policy
from native_scene_contacts import SceneContacts
from native_scene_geometry import evaluate
from native_scene_stage import run, translated
from strep import read,save,sha256


def prepared(tmp_path,space='world'):
    source,path,spec=closed_fixture(tmp_path)
    spec['contacts'][0]['limits']=dict(position_m=100.,relative_speed_m_s=100.)
    if space=='actor':
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['actors']['B']['placement']['translation_m']=[3.,0.,0.]
        spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    if space=='object':
        spec['objects']['ball']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
            keyframes=[dict(time_s=0.,translation_m=[10.,0.,0.],rotation_xyzw=[0,0,0,1]),
                dict(time_s=2.,translation_m=[10.,.1,0.],rotation_xyzw=[0,0,0,1])])
        spec['contacts'][0]['target']=dict(space='object',object='ball',points_m=[[.1,0.,0.]])
    save(path,spec);p=tmp_path/'policy.json';save(p,policy(path,planes={'floor':dict(normal_world=[0.,1.,0.],offset_m=0.)}))
    controls=tmp_path/'control.json';save(controls,dict(schema='strep-native-scene-stage-v1',contacts_sha256=sha256(path),policy_sha256=sha256(p),translation_m=[.01,.02,.03],maximum_translation_m=.05))
    return source,path,p,controls,spec


@pytest.mark.parametrize('space',['world','object','actor'])
def test_common_translation_preserves_all_contacts_and_native_clips(tmp_path,space):
    source,path,p,c,spec=prepared(tmp_path,space);digest=sha256(source)
    result=run(path,p,c,tmp_path/'job');proposal=read(tmp_path/'job/proposal/contacts.json')
    scene=SceneContacts(proposal,tmp_path/'job/proposal');original=SceneContacts(spec,tmp_path)
    before,ba=original.evaluate();after,aa=scene.evaluate()
    assert result['maximum_contact_residual_difference_m']<2e-12 and before['passed']==after['passed']
    np.testing.assert_allclose(aa['contact_0_effector_world_m']-ba['contact_0_effector_world_m'],np.broadcast_to([.01,.02,.03],aa['contact_0_effector_world_m'].shape),atol=2e-12,rtol=0)
    np.testing.assert_allclose(aa['contact_0_target_world_m']-ba['contact_0_target_world_m'],np.broadcast_to([.01,.02,.03],aa['contact_0_target_world_m'].shape),atol=2e-12,rtol=0)
    assert read(tmp_path/'job/proposal/policy.json')['planes']==read(p)['planes']
    assert proposal['duration_s']==spec['duration_s']
    for name,actor in proposal['actors'].items():
        assert sha256(actor['glb'])==digest and actor['sha256']==digest
        assert actor['placement']['rotation_xyzw']==spec['actors'][name]['placement']['rotation_xyzw']
        assert actor['animation_index']==spec['actors'][name]['animation_index']
    if space=='object':assert proposal['contacts'][0]['target']['points_m']==[[.1,0.,0.]]
    assert sha256(source)==digest
    assert result['source_scene_retained'] and not result['proposal_selected']
    assert not result['clips_edited'] and not result['world_planes_edited']
    assert not any(result[k] for k in ['engine_playback_verified','quality_approved','training_admitted','release_approved'])


def test_explicit_placement_can_repair_fixed_plane_without_moving_plane_or_relaxing_limits(tmp_path):
    source,path,p,c,spec=prepared(tmp_path)
    scene=SceneContacts(spec,tmp_path);minimum=min(scene.actor_points('A',np.arange(8),[t])[:,:,1].min() for t in [0.,1.,2.])
    original=read(p);original['planes']['floor']['offset_m']=float(minimum+.01);save(p,original)
    control=read(c);control.update(policy_sha256=sha256(p),translation_m=[0.,.015,0.],maximum_translation_m=.02);save(c,control)
    before,_=evaluate(scene,original,sha256(path));assert not before['sampled_conditions_pass']
    result=run(path,p,c,tmp_path/'job');assert result['sampled_geometry_conditions_pass']
    derived=read(tmp_path/'job/proposal/policy.json')
    assert {k:v for k,v in derived.items() if k!='contacts_sha256'}=={k:v for k,v in original.items() if k!='contacts_sha256'}
    assert not result['quality_approved']


@pytest.mark.parametrize('fault',['contacts','policy','bound','exceeds','nan','bool','fields'])
def test_invalid_or_unbound_controls_fail_before_output(tmp_path,fault):
    source,path,p,c,spec=prepared(tmp_path);v=read(c)
    if fault=='contacts':v['contacts_sha256']='0'*64
    if fault=='policy':v['policy_sha256']='0'*64
    if fault=='bound':v['maximum_translation_m']=.2
    if fault=='exceeds':v['maximum_translation_m']=.01
    if fault=='nan':v['translation_m'][1]=float('nan')
    if fault=='bool':v['maximum_translation_m']=True
    if fault=='fields':v['move_plane']=True
    if fault=='nan':c.write_text(json.dumps(v),encoding='utf-8')
    else:save(c,v)
    out=tmp_path/'job'
    with pytest.raises(ValueError):run(path,p,c,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['source','archive'])
def test_mutation_during_geometry_rejects_completed_proposal(tmp_path,monkeypatch,fault):
    import native_scene_stage as stage
    source,path,p,c,spec=prepared(tmp_path);audit=stage.geometry_audit;out=tmp_path/'job'
    def changed(*args,**kwargs):
        result=audit(*args,**kwargs)
        f=p if fault=='source' else out/'implementation/native_scene_stage.py'
        f.write_bytes(f.read_bytes()+b'\n');return result
    monkeypatch.setattr(stage,'geometry_audit',changed)
    with pytest.raises(ValueError):run(path,p,c,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()


def test_translation_does_not_mutate_authored_spec(tmp_path):
    source,path,p,c,spec=prepared(tmp_path,'object');original=copy.deepcopy(spec)
    derived=translated(spec,[0,.02,0]);assert spec==original and derived!=spec
    assert derived['contacts']==spec['contacts']
    assert derived['objects']['ball']['geometry']==spec['objects']['ball']['geometry']
