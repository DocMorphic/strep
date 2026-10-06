"""Generated bridge permissions, preserved libraries and unapproved scene proposals."""
from pathlib import Path
import sys,copy
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import native_transition_scene_fit as correction
import native_scene_transition as assembly
import action_worker_lock as locks
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from rig_asset import RigAsset
from strep import read,save,sha256
from test_native_rig_transfer import fixture as rig_fixture
from test_native_transfer_surface_calibration import closed_skin
from test_native_scene_transition import fixture as scene_fixture


def fixture(root,*,floor=None,meeting=True):
    asset,profile=rig_fixture(root/'closed','test',animated=False);closed_skin(asset,profile)
    path,recipe=scene_fixture(root/'input',asset=asset);original=assembly.Problem(recipe,path.parent)
    rig=RigAsset.load(original.actors['A']['folder']/'character.glb');skin=NativeSupportSkin(rig)
    # Names select generated fixture parts, never anatomical mappings in product code.
    arm=next(i for i,n in enumerate(rig.document['nodes']) if n['name'].endswith('_LeftArm'))
    hand=next(i for i,n in enumerate(rig.document['nodes']) if n['name'].endswith('_LeftHand'))
    index=original.actors['A']['result']['animation_index'];reader=NativeSupportSampler(rig.document,rig.binary,index)
    clock=next(c[2] for c in reader.channels if c[:2]==(arm,'rotation'));lo,hi=np.searchsorted(clock,[original.start,original.end]);mid=(original.start+original.end)/2
    guards=[[original.start,float(clock[lo+1])],[float(clock[hi-1]),original.end]]
    actors={n:dict(window_s=[original.start,original.end],protected_s=[],knots_s=[original.start,mid,original.end],
        tracks=[dict(node=arm,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.03) for n in original.spec['actors']}
    spec=copy.deepcopy(original.spec)
    for n,a in spec['actors'].items():a['glb']=str(original.actors[n]['folder']/'character.glb')
    guarded=copy.deepcopy(actors)
    for a in guarded.values():a['protected_s']+=guards
    edits=SceneEdits(dict(schema='strep-native-scene-edit-v1',contacts_sha256='draft',actors=guarded),SceneContacts(spec,root),'draft',rotation_storage_policy='source-scale')
    desired=edits.initial.copy()
    for a in edits.actors.values():desired[a['tracks'][0]['controls'][0,2]]=-.006
    world=edits.worlds('A',desired,[mid])[0];vertices=rig.vertices(world)
    ids=np.flatnonzero(np.any((skin.nodes==hand)&(skin.weights>0),axis=1));positive=ids[vertices[ids,2]>np.mean(vertices[ids,2])]
    selected=int(positive[np.argmin(vertices[positive,0])]);ref=skin.vertex_references[[selected]].tolist()
    flip=Rotation.from_euler('y',180,degrees=True);point=vertices[selected];position=point-flip.apply(point)
    for binding in recipe['sources']:
        source=Path(binding['scene']['path']);s=read(source);s['contacts']=[c for c in s['contacts'] if c['id']=='ground']
        s['actors']['B']['placement']=dict(translation_m=position.tolist(),rotation_xyzw=flip.as_quat().tolist());save(source,s);binding['scene']['sha256']=sha256(source)
    if meeting:recipe['bridge']['contacts'].append(dict(id='partner-touch',actor='A',vertices=ref,reduction='individual',target=dict(space='actor',actor='B',vertices=ref,reduction='individual'),
        mode='touch',interval_s=[mid,mid],limits=dict(position_m=.00002)))
    recipe['floor']=floor
    save(path,recipe);out=root/'assembly';assembly.run(path,out)
    request=dict(schema=correction.SCHEMA,source=dict(folder=str(out),result_sha256=sha256(out/'result.json')),label='Generated coupled bridge correction',actors=actors,
        geometry=dict(clock=dict(mode='explicit',times_s=read(out/'roots.json')['times_s']),limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={}),iterations=2,maximum_pose_vertex_queries=1000000)
    rp=root/'correction.json';save(rp,request);return rp,request,desired


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('bridge-scene-fit');patch=pytest.MonkeyPatch();patch.setattr(locks,'ROOT',root)
    path,request,desired=fixture(root);problem=correction.Problem(request,root)
    yield root,path,request,desired,problem
    patch.undo()


def test_articulated_variants_keep_all_original_clips_binary_and_protected_source_phases(study,tmp_path):
    _,_,_,desired,p=study;x=desired*.25
    for name,a in p.scene.actors.items():
        out=tmp_path/(name+'.glb');index=p.append(name,x,out);rig=RigAsset.load(out)
        assert index==len(a['rig'].document['animations']) and rig.document['animations'][:-1]==a['rig'].document['animations']
        assert rig.binary[:len(a['rig'].binary)]==a['rig'].binary
        before=a['sampler'];after=NativeSupportSampler(rig.document,rig.binary,index)
        assert len(before.channels)==len(after.channels)
        for old,new in zip(before.channels,after.channels):
            assert old[:2]==new[:2] and old[4]==new[4];np.testing.assert_array_equal(old[2],new[2])
            frozen=(old[2]<=p.guards[name][0][1])|(old[2]>=p.guards[name][-1][0]);np.testing.assert_array_equal(old[3][frozen],new[3][frozen])
        for time in [0.,p.original.start,p.original.end,p.scene.duration]:np.testing.assert_array_equal(before.sample(time),after.sample(time))
        assert any(not np.array_equal(old[3],new[3]) for old,new in zip(before.channels,after.channels))
    assert np.max(p.motion.constraints(x)[:p.motion.protected_rows])<=0


def test_context_actor_appends_unchanged_clip_without_becoming_an_edit_control(study,tmp_path):
    root,_,request,_,_=study;r=copy.deepcopy(request);del r['actors']['B'];p=correction.Problem(r,root)
    out=tmp_path/'B.glb';index=p.append('B',p.edits.initial,out);rig=RigAsset.load(out)
    assert rig.document['animations'][:-1]==p.scene.actors['B']['rig'].document['animations']
    for a,b in zip(p.scene.actors['B']['sampler'].channels,NativeSupportSampler(rig.document,rig.binary,index).channels):np.testing.assert_array_equal(a[3],b[3])


def test_preflight_matches_every_source_contact_and_geometry_clock(study):
    _,_,request,_,p=study
    unit=sum(2*len(a['rig'].parents)+len(a['skin'].nodes) for a in p.scene.actors.values())+2*len(p.scene.objects)
    np.testing.assert_array_equal(correction.motion_clock(p.scene,unit,request['maximum_pose_vertex_queries']),p.motion.times)
    assert p.population==len(p.times)*unit
    assert np.isin(p.motion.times,p.times).all() and np.isin(p.original.times,p.times).all()


def test_small_budget_rejects_before_full_solver_pose_allocation(study,monkeypatch):
    root,_,request,_,_=study;r=copy.deepcopy(request);r['maximum_pose_vertex_queries']=1
    def forbidden(*args):raise AssertionError('Full solver allocated before query-budget preflight')
    monkeypatch.setattr(correction.fitting,'SceneProblem',forbidden)
    with pytest.raises(ValueError,match='budget'):correction.Problem(r,root)


@pytest.mark.parametrize('fault',['missing-actor','extra-actor','short-poses','nan-pose','duplicate-clock','partial-clock'])
def test_shared_floor_rejects_missing_or_nonfinite_full_clip_populations(fault):
    rig=SimpleNamespace(parents=[-1],vertices=lambda w:np.array([[0.,-.01,0.]]))
    scene=SimpleNamespace(duration=1.,actors={'A':dict(rig=rig,placement=(np.zeros(3),np.eye(3)))})
    times=np.array([0.,.5,1.]);worlds={'A':np.tile(np.eye(4),(3,1,1,1))};floor=dict(height_m=0.,maximum_penetration_m=.001)
    assert correction.shared_floor(scene,worlds,floor,times)['passed'] is False
    if fault=='missing-actor':worlds={}
    elif fault=='extra-actor':worlds['B']=worlds['A'].copy()
    elif fault=='short-poses':worlds['A']=worlds['A'][:-1]
    elif fault=='nan-pose':worlds['A'][0,0,0,0]=np.nan
    elif fault=='duplicate-clock':times[1]=0.
    else:times[-1]=.9
    with pytest.raises(ValueError):correction.shared_floor(scene,worlds,floor,times)


def test_inherited_world_floor_keeps_protected_source_penetration_failed_without_a_new_plane(tmp_path,monkeypatch):
    monkeypatch.setattr(locks,'ROOT',tmp_path)
    _,request,_=fixture(tmp_path,floor=dict(height_m=.236,maximum_penetration_m=.0001),meeting=False)
    p=correction.Problem(request,tmp_path);out=tmp_path/'candidate';out.mkdir();(out/'actors').mkdir();spec=copy.deepcopy(p.spec)
    for i,(name,a) in enumerate(spec['actors'].items()):
        path=out/'actors'/(str(i)+'.glb');index=p.append(name,p.edits.initial,path);a.update(glb='actors/'+str(i)+'.glb',sha256=sha256(path),animation_index=index)
    save(out/'scene.json',spec);_,_,_,_,_,_,geometry,checks,_=p.audit(out,p.edits.initial)
    floor=geometry['inherited_shared_floor'];assert floor['full_clip'] and floor['peak']['time_s']==0 and floor['maximum_penetration_m']>floor['limit_m']
    assert checks['native_motion_and_contacts'] is True and checks['actor_transition_conditions'] is True and checks['inherited_shared_floor'] is False
    assert request['geometry']['planes']=={} and p.parent['checks']['floor'] is False


@pytest.mark.parametrize('fault',['binding','iterations-bool','iterations-excess','extra','phase-window','track-missing','maximum-bool','protected-all','query-budget','geometry-clock'])
def test_invalid_or_excess_permissions_reject_before_creating_output(study,tmp_path,fault):
    root,_,request,_,_=study;r=copy.deepcopy(request)
    if fault=='binding':r['source']['result_sha256']='0'*64
    elif fault=='iterations-bool':r['iterations']=True
    elif fault=='iterations-excess':r['iterations']=17
    elif fault=='extra':r['approve_motion']=True
    elif fault=='phase-window':r['actors']['A']['window_s'][0]=0.
    elif fault=='track-missing':r['actors']['A']['tracks'][0]['node']=1000
    elif fault=='maximum-bool':r['actors']['A']['tracks'][0]['maximum_change']=True
    elif fault=='protected-all':r['actors']['A']['protected_s']=[r['actors']['A']['window_s']]
    elif fault=='query-budget':r['maximum_pose_vertex_queries']=1
    else:r['geometry']['clock']['times_s']=[0.,0.,1.]
    path=tmp_path/'request.json';save(path,r);out=tmp_path/'output'
    with pytest.raises(ValueError):correction.run(path,out)
    assert not out.exists()


def test_complete_proposals_replay_without_claiming_engine_or_resetting_marker_confirmation(study,tmp_path):
    root,path,_,_,_=study;out=tmp_path/'correction';r=correction.run(path,out)
    before={p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()}
    assert correction.verify(out)==r
    assert before=={p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()}
    assert r['root_observations_are_native_only'] is True and r['engine_playback_verified'] is False and r['original_selected'] is True
    assert not r['quality_approved'] and not r['training_admitted'] and not r['release_approved']
    assert read(out/'game-tracks-request.json')==read(Path(read(out/'recipe.json')['source']['folder'])/'game-tracks-request.json')
    assert all(not e['runtime_dispatch_allowed'] for e in read(out/'tracks/events.json')['events'])
    with np.load(out/'tracks/root-observations.npz',allow_pickle=False) as a:assert all('imported' not in n for n in a.files)
    # Rehashed decision booleans and dropped populations cannot approve a variant.
    for kind in ['approval','native-only-integer','files','markers']:
        old_result=(out/'result.json').read_bytes();old_completion=(out/'completion.json').read_bytes();old_events=(out/'tracks/events.json').read_bytes()
        try:
            forged=read(out/'result.json')
            if kind=='approval':forged['quality_approved']=True
            elif kind=='native-only-integer':forged['root_observations_are_native_only']=1
            elif kind=='files':forged['files_sha256'].pop('tracks/root-observations.npz')
            else:
                events=read(out/'tracks/events.json');events['events'][-1]['runtime_dispatch_allowed']=True;save(out/'tracks/events.json',events);forged['files_sha256']['tracks/events.json']=sha256(out/'tracks/events.json')
            save(out/'result.json',forged);save(out/'completion.json',dict(result_sha256=sha256(out/'result.json')))
            with pytest.raises(ValueError):correction.verify(out)
        finally:
            (out/'result.json').write_bytes(old_result);(out/'completion.json').write_bytes(old_completion);(out/'tracks/events.json').write_bytes(old_events)
