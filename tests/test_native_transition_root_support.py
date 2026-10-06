"""Root-only repair, protected conflicts and unchanged authored conditions."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_transition_root_support as fit
import native_rig_transition as transition
from native_transition_curve import localize,compose
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from rig_asset import RigAsset
from gltf_tools import write_glb
from strep import read,save,sha256
from test_native_rig_transition import fixture
from test_native_rig_transfer import fixture as rig_fixture


def request(source,first=.25):
    source=Path(source).resolve();r=read(source/'result.json');rig=RigAsset.load(source/'character.glb');reader=NativeSupportSampler(rig.document,rig.binary,r['animation_index'])
    times=reader.channels[0][2].astype(float);window=[float(times[abs(times-t).argmin()]) for t in (first,.9)]
    return dict(schema=fit.SCHEMA,source=dict(folder=str(source),result_sha256=sha256(source/'result.json')),label='root support correction',window_s=window,
        maximum_root_translation_change_m=.08,maximum_joint_displacement_m=.08,maximum_pose_vertex_queries=1000000)


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('root-support');patch=pytest.MonkeyPatch();patch.setattr(action_worker_lock,'ROOT',root)
    path,_=fixture(root/'assets',moving=True);source=root/'transition';transition.run(path,source)
    recipe=request(source);path=root/'root-recipe.json';save(path,recipe);out=root/'fit';r=fit.run(path,out)
    yield root,source,recipe,path,out,r
    patch.undo()


def test_repairs_support_and_floor_preserving_all_original_clips_paths_and_source_limits(study):
    _,source,recipe,_,out,r=study;old=read(source/'result.json');assert not old['checks']['supports'] and not old['checks']['floor']
    assert r['all_declared_samples_pass'] is True and fit.verify(out)==r
    assert r['maximum_root_translation_change_m']<.08 and r['maximum_joint_displacement_m']<.08 and r['maximum_rotation_matrix_change']==0
    assert r['supports'][0]['maximum_position_error_m']<1e-10 and r['supports'][0]['maximum_slip_m_s']<1e-10 and r['floor_maximum_penetration_m']==0
    before=RigAsset.load(source/'character.glb');after=RigAsset.load(out/'character.glb')
    assert after.document['animations'][:-1]==before.document['animations'] and after.binary[:len(before.binary)]==before.binary
    assert r['animation_index']==4 and len(after.document['animations'])==5
    assert all(r[n] is False for n in transition.FALSE_FLAGS) and r['original_selected'] is True
    problem=fit.Problem(recipe,out.parent)
    native=NativeSupportSampler(after.document,after.binary,r['animation_index'])
    for t in problem.probes[(problem.probes<=problem.first)|(problem.probes>=problem.last)]:
        np.testing.assert_array_equal(native.sample(float(t)),problem.reader.sample(float(t)))
    motion=read(out/'root-motion.json');assert motion['animation_index']==r['animation_index'] and motion['node']==problem.root
    assert motion['times_s']==problem.times.tolist()
    np.testing.assert_array_equal(motion['positions_m'],[native.sample(float(t))[problem.root,:3,3] for t in problem.times])


def test_partial_eight_slot_weights_under_an_animated_parent_match_independent_skin_displacement(tmp_path):
    source,_=rig_fixture(tmp_path,'affine',animated=True);rig=RigAsset.load(source)
    root=next(i for i,n in enumerate(rig.document['nodes']) if n['name']=='affine_LeftForeArm');hips=next(i for i,n in enumerate(rig.document['nodes']) if n['name']=='affine_Hips')
    p=rig.primitives[0];p['joints']=np.pad(p['joints'],((0,0),(0,4)));p['weights']=np.pad(p['weights'],((0,0),(0,4)))
    p['joints'][0]=[rig.joints.index(root),rig.joints.index(hips),0,0,rig.joints.index(root),rig.joints.index(hips),0,0]
    p['weights'][0]=[.2,.3,0,0,.15,.35,0,0]
    skin=NativeSupportSkin(rig);fractions=fit.root_fractions(rig,skin,root)
    assert fractions[0]==float(p['weights'][0,[0,4]].astype(float).sum()) and 0 in fractions and 1 in fractions
    reader=NativeSupportSampler(rig.document,rig.binary,0);delta=np.array([.012,-.004,.007])
    for t in (.173725,.83725,1.4321):
        world=reader.sample(t);local=localize(world[None],rig.parents);local[0,root,:3,3]+=delta
        moved=compose(local,rig.parents)[0];actual=rig.vertices(moved)-rig.vertices(world)
        expected=fractions[:,None]*(world[rig.parents[root],:3,:3]@delta)
        np.testing.assert_allclose(actual,expected,atol=1e-14,rtol=0)


@pytest.mark.parametrize('mode',['frozen-bridge','small-root','small-displacement'])
def test_necessary_conflicts_never_export_a_candidate_or_increase_bounds(study,tmp_path,mode):
    _,source,recipe,_,_,_=study;p=copy.deepcopy(recipe)
    if mode=='frozen-bridge':p['window_s']=read(source/'result.json')['bridge_interval_s']
    elif mode=='small-root':p['maximum_root_translation_change_m']=.001
    else:p['maximum_joint_displacement_m']=.001
    path=tmp_path/'recipe.json';save(path,p);out=tmp_path/'failed';r=fit.run(path,out)
    assert r['necessary_conflicts'] and r['candidate_available'] is False and r['all_declared_samples_pass'] is False
    assert not (out/'character.glb').exists() and not (out/'root-motion.json').exists()
    assert r['files_sha256']=={} and fit.verify(out)==r and read(out/'pipeline.json')['status']=='complete'


def test_existing_angular_corner_at_edit_window_remains_failed_without_rotational_permissions(study,tmp_path):
    _,source,_,_,_,_=study;p=request(source,first=.2);path=tmp_path/'recipe.json';save(path,p);out=tmp_path/'corner';r=fit.run(path,out)
    assert r['candidate_available'] and r['checks']['supports'] and r['checks']['floor']
    assert r['checks']['angular_boundaries'] is False and r['all_declared_samples_pass'] is False and not r['quality_approved']
    assert max(x['angular_jump_degrees_s'] for x in r['boundaries'])>24


@pytest.mark.parametrize('fault',['schema','binding','label','window-bool','window-nonnative','window-reversed','root-bool','root-large','displacement-bool','population-bool','population-small','extra'])
def test_bad_or_unbounded_requests_reject_before_output(study,tmp_path,fault):
    _,_,recipe,_,_,_=study;p=copy.deepcopy(recipe)
    if fault=='schema':p['schema']='old'
    elif fault=='binding':p['source']['result_sha256']='f'*64
    elif fault=='label':p['label']=''
    elif fault=='window-bool':p['window_s'][0]=True
    elif fault=='window-nonnative':p['window_s'][0]=.253725
    elif fault=='window-reversed':p['window_s']=p['window_s'][::-1]
    elif fault=='root-bool':p['maximum_root_translation_change_m']=True
    elif fault=='root-large':p['maximum_root_translation_change_m']=.221
    elif fault=='displacement-bool':p['maximum_joint_displacement_m']=False
    elif fault=='population-bool':p['maximum_pose_vertex_queries']=True
    elif fault=='population-small':p['maximum_pose_vertex_queries']=1
    else:p['rotate_legs']=True
    path=tmp_path/'bad.json';save(path,p);out=tmp_path/'out'
    with pytest.raises(ValueError):fit.run(path,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['approval','typed-flag','support','root-motion','new-label','snapshot','method'])
def test_rehashed_result_sidecar_payload_or_snapshot_cannot_forge_approval(study,fault):
    _,_,_,_,out,_=study;modified={p:p.read_bytes() for p in (out/'result.json',out/'completion.json')}
    def edit(name,fn):
        p=out/name;modified.setdefault(p,p.read_bytes());v=read(p);fn(v);save(p,v)
    try:
        if fault=='approval':edit('result.json',lambda v:v.update(quality_approved=True))
        elif fault=='typed-flag':edit('result.json',lambda v:v.update(original_selected=1))
        elif fault=='support':edit('result.json',lambda v:v['supports'][0].update(samples=1))
        elif fault=='root-motion':edit('root-motion.json',lambda v:v['positions_m'][0].__setitem__(0,99.))
        elif fault=='new-label':
            p=out/'character.glb';modified[p]=p.read_bytes();rig=RigAsset.load(p);doc=copy.deepcopy(rig.document);doc['animations'][-1]['name']='forged label';write_glb(p,doc,rig.binary)
        else:
            p=out/('source.glb' if fault=='snapshot' else 'implementation/native_transition_root_support.py');modified[p]=p.read_bytes();p.write_bytes(p.read_bytes()+b'changed')
        r=read(out/'result.json');r['files_sha256']={n:sha256(out/n) for n in r['files_sha256']};save(out/'result.json',r)
        save(out/'completion.json',dict(result_sha256=sha256(out/'result.json')))
        with pytest.raises(ValueError):fit.verify(out)
    finally:
        for p,data in modified.items():p.write_bytes(data)


def test_mutually_inconsistent_patches_are_a_failed_projection_not_an_automatic_feasibility_claim(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path);path,recipe=fixture(tmp_path/'assets',moving=True)
    second=copy.deepcopy(recipe['supports'][0]);second['id']='conflicting point';second['points_m'][0][2]+=.03;recipe['supports'].append(second);save(path,recipe)
    source=tmp_path/'transition';transition.run(path,source);p=request(source);rp=tmp_path/'root.json';save(rp,p);out=tmp_path/'out';r=fit.run(rp,out)
    assert not r['necessary_conflicts'] and r['candidate_available'] is True
    assert not r['checks']['supports'] and not r['all_declared_samples_pass'] and not r['quality_approved']
    assert r['checks']['root_translation'] and r['checks']['joint_displacement']
