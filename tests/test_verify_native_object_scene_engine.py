"""Read-only replay rejects forged summaries and incomplete recorded populations.

Producer execution uses explicit small mocked engine fixtures. These tests are
not Godot, GPU, human review or release evidence.
"""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read, save, sha256
from native_object_scene_engine import run as combine
from verify_native_object_scene_engine import run, geometry_reductions
from test_native_object_scene_engine import producers
from test_native_scene_geometry import closed_fixture, policy, evaluate
from native_scene_contacts import SceneContacts


def bundle(tmp_path, monkeypatch):
    path, pp, actors, objects = producers(tmp_path, monkeypatch)
    combined = tmp_path/'combined'; combine(path,pp,actors,objects,combined)
    return path,pp,actors,objects,combined


def test_replay_matches_all_observations_retains_default_failure_and_is_read_only(tmp_path, monkeypatch):
    args=bundle(tmp_path,monkeypatch); combined=args[-1]
    before={p:sha256(p) for p in tmp_path.rglob('*') if p.is_file()}
    result=run(*args,tmp_path/'verification')
    assert result['all_replayed_observations_exact'] and result['recorded_sampled_conditions_pass']
    assert result['geometry_reductions']['passed'] and not result['geometry_reductions']['geometry_queries_rerun']
    assert not read(combined/'result.json')['contacts_pass']['default-import']
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert not result['gpu_render_checked'] and not result['physics_verified'] and not result['real_time_playback_verified']
    assert before=={p:sha256(p) for p in before}
    with pytest.raises(ValueError,match='Fresh'):run(*args,tmp_path/'verification')


@pytest.mark.parametrize('fault',['pending','receipt','missing-receipt','skin-array','contact-array','extra-array',
    'skin-summary','object-summary','contact-report','triangle-array','witness-array','geometry-summary',
    'missing-object','missing-clock','combined-decision','source-binding'])
def test_changed_or_forged_combined_results_fail(tmp_path, monkeypatch, fault):
    args=bundle(tmp_path,monkeypatch); combined=args[-1]; result=read(combined/'result.json')
    if fault=='pending':save(combined/'pipeline.json',dict(status='processing'))
    elif fault=='receipt':(combined/'observations.npz').write_bytes(b'changed')
    elif fault=='missing-receipt':result['files_sha256'].pop('observations.npz')
    elif fault in ('skin-array','contact-array','extra-array'):
        with np.load(combined/'observations.npz') as z:arrays={n:z[n] for n in z.files}
        if fault=='extra-array':arrays['unrequested']=np.zeros(1)
        else:
            key=next(n for n in arrays if n.endswith('_skin_errors_m')) if fault=='skin-array' else next(n for n in arrays if n.startswith('native-authoring_'))
            arrays[key]=arrays[key].copy();arrays[key].flat[0]+=.01
        np.savez_compressed(combined/'observations.npz',**arrays)
    elif fault=='skin-summary':next(iter(result['skin_errors'].values()))['maximum_position_error_m']+=.01
    elif fault=='object-summary':next(iter(result['object_pose_reports']['native-authoring'].values()))['maximum_position_error_m']+=.01
    elif fault=='contact-report':
        report=read(combined/'native-authoring-contacts.json');report['loaded_skin_weights_normalized']=True;save(combined/'native-authoring-contacts.json',report)
    elif fault in ('triangle-array','witness-array'):
        with np.load(combined/'geometry-observations.npz') as z:arrays={n:z[n] for n in z.files}
        suffix='_depth_upper_m' if fault=='triangle-array' else '_witness_world_m'
        key=next(n for n in arrays if n.endswith(suffix));arrays[key]=arrays[key].copy()
        if fault=='triangle-array':arrays[key].flat[0]+=.01
        else:
            report=read(combined/'geometry.json');peak=report['samples'][0]['actor_objects'][0]['peak_lower_face'];arrays[key][peak,0]+=.01
        np.savez_compressed(combined/'geometry-observations.npz',**arrays)
    elif fault in ('geometry-summary','missing-object','missing-clock'):
        report=read(combined/'geometry.json')
        if fault=='geometry-summary':report['samples'][0]['actor_objects'][0]['maximum_depth_upper_m']+=.01
        elif fault=='missing-object':report['samples'][0]['actor_objects'].pop()
        else:report['times_s'].pop()
        save(combined/'geometry.json',report)
    elif fault=='combined-decision':result['all_sampled_conditions_pass']=False
    elif fault=='source-binding':result['source_bindings_sha256']={}
    # Update non-receipt hashes deliberately: replay must reject more than stale receipts.
    if fault not in ('receipt','missing-receipt'):
        result['files_sha256']={n:sha256(combined/n) for n in result['files_sha256']}
    save(combined/'result.json',result)
    with pytest.raises(ValueError):run(*args,tmp_path/'verification')


def geometry_bundle(tmp_path):
    _,path,spec=closed_fixture(tmp_path)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m']=[5.,0.,0.]
    spec['objects']['item']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
        keyframes=[dict(time_s=0.,translation_m=[10.,0.,0.],rotation_xyzw=[0,0,0,1])])
    save(path,spec);p=policy(path,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.)))
    report,arrays=evaluate(path,spec,p);np.savez_compressed(tmp_path/'geometry.npz',**arrays)
    return SceneContacts(spec,tmp_path),p,sha256(path),np.asarray(report['times_s']),report,tmp_path/'geometry.npz'


def test_complete_partner_and_plane_reductions_include_all_populations(tmp_path):
    scene,p,digest,times,report,path=geometry_bundle(tmp_path)
    with np.load(path) as saved:result=geometry_reductions(scene,p,digest,times,report,saved)
    assert result['passed'] and result['actor_object_observations']==6
    assert not result['geometry_queries_rerun']


def test_explicit_geometry_clock_is_preserved_with_additional_engine_times(tmp_path):
    scene,p,digest,times,report,path=geometry_bundle(tmp_path)
    with np.load(path) as saved:
        result=geometry_reductions(scene,p,digest,np.unique(np.r_[times,.5,1.5]),report,saved)
        assert result['samples']==len(times)
        with pytest.raises(ValueError,match='missing from engine'):
            geometry_reductions(scene,p,digest,times[:-1],report,saved)


def test_failed_geometry_remains_a_valid_recorded_failure(tmp_path):
    _,path,spec=closed_fixture(tmp_path);scene=SceneContacts(spec,tmp_path)
    center=scene.actors['A']['rig'].vertices(scene.actors['A']['sampler'].sample(1.)).mean(axis=0)
    spec['objects']['item']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
        keyframes=[dict(time_s=0.,translation_m=center.tolist(),rotation_xyzw=[0,0,0,1])])
    save(path,spec);p=policy(path);report,arrays=evaluate(path,spec,p)
    assert not report['sampled_conditions_pass'];np.savez_compressed(tmp_path/'geometry.npz',**arrays)
    with np.load(tmp_path/'geometry.npz') as saved:
        result=geometry_reductions(SceneContacts(spec,tmp_path),p,sha256(path),np.asarray(report['times_s']),report,saved)
    assert not result['passed'] and not result['geometry_queries_rerun']


@pytest.mark.parametrize('fault',['partner-population','partner-decision','partner-depth','plane-population','plane-decision',
                                  'containment','degenerate','extra-triangle-array','missing-triangle-array'])
def test_complete_geometry_reductions_reject_missing_or_inconsistent_evidence(tmp_path,fault):
    scene,p,digest,times,report,path=geometry_bundle(tmp_path);sample=report['samples'][0]
    if fault=='partner-population':sample['actor_pairs'].pop()
    elif fault=='partner-decision':sample['actor_pairs'][0]['passed']=False
    elif fault=='partner-depth':sample['actor_pairs'][0]['vertex_containment'][0]['max_depth_m']=float('nan')
    elif fault=='plane-population':sample['world_planes'].pop()
    elif fault=='plane-decision':sample['world_planes'][0]['passed']=False
    elif fault=='containment':sample['actor_objects'][0]['containment']['status']='inside'
    elif fault=='degenerate':sample['degenerate_faces']['A']=[99999]
    else:
        with np.load(path) as z:arrays={n:z[n] for n in z.files}
        if fault=='extra-triangle-array':arrays['unrequested']=np.zeros(1)
        else:arrays.pop(next(n for n in arrays if n.endswith('_depth_lower_m')))
        np.savez_compressed(path,**arrays)
    with np.load(path) as saved:
        with pytest.raises((ValueError,KeyError)):geometry_reductions(scene,p,digest,times,report,saved)
