"""Complete legacy-condition equivalence, saved files and bounded skin batches."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_scene_fit.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts'),str(root/'tests')]
from native_scene_world_rows import SceneWorldRows
from native_scene_fit import SceneProblem
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from test_native_scene_fit import prepare
from test_native_scene_contacts import object_target
from strep import save,sha256


def fixture(tmp_path,rotation=False,space='world',centroid=False):
    source,spec,contacts,permissions,path,scene,edits=prepare(tmp_path,rotation=rotation)
    row=spec['contacts'][0]
    if space=='object':object_target(spec,scene.actors['A']['sampler'],scene.actors['A']['rig'])
    elif space=='actor':
        spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m'][1]+=.003
        row['target']=dict(space='actor',actor='B',vertices=row['vertices'].copy(),reduction='individual')
    if centroid:
        row['vertices']=[[6,0,0],[6,0,1]];row['reduction']='centroid'
        if space=='actor':row['target'].update(vertices=[[6,0,0],[6,0,1]],reduction='centroid')
    save(contacts,spec);permissions['contacts_sha256']=sha256(contacts)
    scene=SceneContacts(spec,tmp_path);edits=SceneEdits(permissions,scene,sha256(contacts));legacy=SceneProblem(scene,edits)
    caps={name:actor['displacement'] for name,actor in edits.actors.items()}
    return scene,edits,legacy,caps


def retained(problem,values):
    parts=[];cursor=0
    for name,actor in problem.edits.actors.items():
        cursor+=sum(len(track['ids']) for track in actor['tracks'])
        count=len(problem.uniform)*len(problem.scene.actors[name]['rig'].joints)+sum(cap.size for cap in problem.caps[name].caps)
        parts.append(values[cursor:cursor+count]);cursor+=count
    parts.append(values[cursor:]);return np.concatenate(parts)


@pytest.mark.parametrize('rotation',[False,True])
@pytest.mark.parametrize('space',['world','object','actor'])
@pytest.mark.parametrize('centroid',[False,True])
def test_every_original_world_contact_rate_row_and_clock_matches_bytewise(tmp_path,rotation,space,centroid):
    scene,edits,legacy,caps=fixture(tmp_path,rotation,space,centroid);oracle=SceneWorldRows(scene,caps)
    np.testing.assert_array_equal(oracle.times,legacy.times)
    for fraction in [0.,.013,-.019]:
        value=edits.initial+fraction;worlds=legacy.worlds(value)
        expected=retained(legacy,legacy.constraints(value,worlds));actual=oracle.violations(worlds)
        assert actual.tobytes()==expected.tobytes()
    assert oracle.report['rows']==len(actual) and oracle.report['optimization_variables']==0
    assert not oracle.report['native_parameter_conditions_included'] and not oracle.report['surface_geometry_included']
    assert oracle.layout[0][0]=='displacement' and oracle.layout[-1][-1]==len(actual)
    assert any(kind=='contact_speed' for kind,*other in oracle.layout)


def test_one_frame_skin_batches_preserve_all_vertices_and_hold_clock_rows(tmp_path):
    scene,edits,legacy,caps=fixture(tmp_path,True,'actor',True)
    needed=max(len(actor['rig'].document['nodes'])*16*8+2*actor['skin'].nodes.shape[1]*12*8 for actor in scene.actors.values())
    oracle=SceneWorldRows(scene,caps,maximum_skin_bytes=needed);value=edits.initial+.013
    expected=retained(legacy,legacy.constraints(value));actual=oracle.violations(legacy.worlds(value))
    np.testing.assert_allclose(actual,expected,atol=2e-12,rtol=0)
    assert len(actual)==len(expected)


def test_saved_native_files_match_legacy_decoded_world_conditions(tmp_path):
    scene,edits,legacy,caps=fixture(tmp_path,True,'object');oracle=SceneWorldRows(scene,caps)
    value=edits.initial+.013;target=tmp_path/'candidate.glb';edits.export('A',value,target)
    old,worlds=legacy.decoded({'A':target},value)
    actual,report=oracle.evaluate_files({'A':dict(path=str(target),sha256=sha256(target),animation_index=0)})
    np.testing.assert_array_equal(actual,retained(legacy,old))
    assert report['world_conditions_pass']==bool(np.all(actual<=0)) and not report['quality_approved'] and report['original_selected']


def test_source_and_caps_snapshotted_and_outputs_cannot_mutate_the_oracle(tmp_path):
    scene,edits,legacy,caps=fixture(tmp_path);oracle=SceneWorldRows(scene,caps);worlds=oracle.source_worlds();before=oracle.violations(worlds)
    scene.rows[0]['authored']['limits']['position_m']=999;scene.actors['A']['placement']=(np.array([99.,0,0]),np.eye(3));caps['A']=9.
    times=oracle.times;times[:]=0;report=oracle.report;report['edited_actors'].clear()
    np.testing.assert_array_equal(before,oracle.violations(worlds))
    worlds['A'][:]=0;assert np.any(oracle.source_worlds()['A']) and oracle.report['edited_actors']==['A']


@pytest.mark.parametrize('fault',['missing','extra','shape','nan','bool','unmodified'])
def test_complete_matching_world_populations_required(tmp_path,fault):
    scene,edits,legacy,caps=fixture(tmp_path,False,'actor');oracle=SceneWorldRows(scene,caps);worlds=oracle.source_worlds()
    if fault=='missing':worlds.pop('B')
    elif fault=='extra':worlds['extra']=worlds['A']
    elif fault=='shape':worlds['A']=worlds['A'][:-1]
    elif fault=='nan':worlds['A'][0,0,0,0]=np.nan
    elif fault=='bool':worlds['A']=np.zeros(worlds['A'].shape,dtype=bool)
    else:worlds['B'][:,:,1,3]+=.001
    with pytest.raises(ValueError):oracle.violations(worlds)


@pytest.mark.parametrize('fault',['empty','unknown','zero','bool','shape','times','world_bytes','rows','skin_bytes'])
def test_caps_and_complete_resource_budgets_reject_without_truncation(tmp_path,fault):
    scene,edits,legacy,caps=fixture(tmp_path);settings={}
    if fault=='empty':caps={}
    elif fault=='unknown':caps={'B':.01}
    elif fault=='zero':caps['A']=0.
    elif fault=='bool':caps['A']=True
    elif fault=='shape':caps['A']=[.01]
    elif fault=='times':settings['maximum_times']=1
    elif fault=='world_bytes':settings['maximum_world_bytes']=1
    elif fault=='rows':settings['maximum_rows']=1
    else:settings['maximum_skin_bytes']=1
    with pytest.raises(ValueError):SceneWorldRows(scene,caps,**settings)


def test_changed_source_file_rejected_before_reusing_sampled_worlds(tmp_path):
    scene,edits,legacy,caps=fixture(tmp_path);oracle=SceneWorldRows(scene,caps);worlds=oracle.source_worlds()
    path=Path(next(iter(scene.inputs)));path.write_bytes(path.read_bytes()+b'x')
    for operation in [lambda:oracle.source_worlds(),lambda:oracle.violations(worlds)]:
        with pytest.raises(ValueError):operation()


@pytest.mark.parametrize('fault',['digest','index','missing','extra','static'])
def test_candidate_bindings_and_static_rig_payload_preserved(tmp_path,fault):
    from gltf_tools import write_glb
    from rig_asset import RigAsset
    scene,edits,legacy,caps=fixture(tmp_path);oracle=SceneWorldRows(scene,caps);target=tmp_path/'candidate.glb';edits.export('A',edits.initial,target)
    entry=dict(path=str(target),sha256=sha256(target),animation_index=0);files={'A':entry}
    if fault=='digest':entry['sha256']='0'*64
    elif fault=='index':entry['animation_index']=True
    elif fault=='missing':files={}
    elif fault=='extra':entry['skip_checks']=True
    else:
        rig=RigAsset.load(target);rig.document['nodes'][0]['name']='different-static-node';write_glb(target,rig.document,rig.binary);entry['sha256']=sha256(target)
    with pytest.raises(ValueError):oracle.evaluate_files(files)


def test_appended_candidate_index_is_sampled_instead_of_the_original_animation(tmp_path):
    from native_key_contact_initializer import encode
    from native_support_clock import NativeSupportSampler
    from rig_asset import RigAsset
    scene,edits,legacy,caps=fixture(tmp_path,True);oracle=SceneWorldRows(scene,caps);actor=scene.actors['A']
    channel=next(c for c in actor['sampler'].channels if c[:2]==(3,'rotation'));controls=np.zeros((len(channel[2]),1,3));controls[len(controls)//2,0,0]=.15
    path=tmp_path/'appended.glb';index=encode(actor['rig'],actor['animation_index'],[3],[channel],controls,[5.],path);assert index!=actor['animation_index']
    rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,index)
    worlds=oracle.source_worlds();worlds['A']=np.array([sampler.sample(float(t)) for t in oracle.times])
    actual,report=oracle.evaluate_files({'A':dict(path=str(path),sha256=sha256(path),animation_index=index)})
    np.testing.assert_array_equal(actual,oracle.violations(worlds))
    original,_=oracle.evaluate_files({'A':dict(path=str(path),sha256=sha256(path),animation_index=actor['animation_index'])})
    assert np.abs(actual-original).max()>1e-6


def test_unequal_joint_caps_keep_legacy_joint_major_displacement_order(tmp_path):
    scene,edits,legacy,caps=fixture(tmp_path);joints=scene.actors['A']['rig'].joints
    limits=np.linspace(.01,.03,len(joints));oracle=SceneWorldRows(scene,{'A':limits});original=oracle.source_worlds();worlds=oracle.source_worlds()
    worlds['A'][:,:,1,3]+=.004
    actual=oracle.violations(worlds);uniform=np.arange(int(np.floor(scene.duration*120))+1)/120;ids=np.searchsorted(oracle.times,uniform)
    expected=[]
    for index,joint in enumerate(joints):
        for frame in ids:
            distance=np.linalg.norm(worlds['A'][frame,joint,:3,3]-original['A'][frame,joint,:3,3])
            expected.append((distance-limits[index])/limits[index])
    first,last=oracle.layout[0][-2:];np.testing.assert_array_equal(actual[first:last],expected)
