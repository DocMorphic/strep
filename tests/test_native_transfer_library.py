"""Independent generated rigs; actual CPU transfer, no model/engine doubles."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_transfer_library as library
from gltf_tools import append_accessor,write_glb,local_matrix
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from retarget_rig import resolve_profile
from strep import read,save,sha256
from test_native_rig_transfer import pair


def fixture(root,assets=None):
    if assets is None:a,ap,b,bp=pair(root)
    else:
        import shutil
        root.mkdir(parents=True,exist_ok=True)
        a,ap,b,bp=[root/n for n in ('source.glb','source-profile.json','target.glb','target-profile.json')]
        for old,new in zip(assets,(a,ap,b,bp)):shutil.copyfile(old,new)
    rig=RigAsset.load(a);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    mapping,_=resolve_profile(rig,read(ap));root_node=mapping['Hips'];arm=mapping['LeftArm']
    for node in (root_node,arm):
        entry=doc['nodes'][node];local=local_matrix(entry);entry.pop('matrix',None)
        entry.update(translation=local[:3,3].tolist(),rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),scale=[1,1,1])
    duration=float(np.float32(.23333333));times=[0.,.073725,duration]
    base=np.array(doc['nodes'][root_node]['translation']);rotation=Rotation.from_quat(doc['nodes'][arm]['rotation'])
    for index in range(2):
        animation=dict(name=['arbitrary gesture','arbitrary recovery'][index],channels=[],samplers=[])
        position=np.array([base,base+[.1,.02,-.03],base+[.2,.02,-.06]]) if index==0 else np.array([base+[.2,.02,-.06],base+[.2,.02,-.06],base+[.3,0.,-.09]])
        angles=[0.,10.,15.] if index==0 else [15.,22.,5.]
        q=(Rotation.from_euler('z',angles,degrees=True)*rotation).as_quat()
        for node,path,values,kind in [(root_node,'translation',position,'VEC3'),(arm,'rotation',q,'VEC4')]:
            ti=append_accessor(doc,binary,np.array(times),'SCALAR');vi=append_accessor(doc,binary,values,kind)
            animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
            animation['samplers'].append(dict(input=ti,output=vi,interpolation='LINEAR'))
        doc['animations'].append(animation)
    write_glb(a,doc,binary);profile=read(ap);profile['character_sha256']=sha256(a);save(ap,profile)
    # One explicit shared correction, not a guessed anatomical profile.
    if assets is None:
        profile=read(bp);profile['axis_alignment_xyzw']={'LeftHand':Rotation.from_euler('z',9,degrees=True).as_quat().tolist()};save(bp,profile)
    def bound(p):return dict(path=p.name,sha256=sha256(p))
    recipe=dict(schema=library.SCHEMA,target=dict(glb=bound(b),profile=bound(bp)),rate=60,maximum_planned_pose_transforms=1000000,
        clips=[dict(id=name,glb=bound(a),profile=bound(ap),animation_index=i+1) for i,name in enumerate(['gesture','recovery'])],
        boundaries=[dict(**{'from':'gesture','to':'recovery'},limits=dict(position_m=1e-4,rotation_degrees=.001,linear_speed_jump_m_s=.01,angular_speed_jump_degrees_s=.1))])
    path=root/'recipe.json';save(path,recipe);return path,recipe


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('library');patch=pytest.MonkeyPatch();patch.setattr(action_worker_lock,'ROOT',root)
    path,recipe=fixture(root);folder=root/'library';library.run(path,folder)
    yield root,path,recipe,folder
    patch.undo()


def test_one_library_preserves_original_clips_raw_payload_and_all_varied_selections(study):
    root,path,recipe,folder=study;r=library.verify(folder);cat=read(folder/'catalog.json')
    original=RigAsset.load(root/recipe['target']['glb']['path']);output=RigAsset.load(folder/'character.glb')
    assert output.binary[:len(original.binary)]==original.binary
    assert output.document['animations'][:1]==original.document['animations'] and len(output.document['animations'])==3
    assert [(x['id'],x['animation_index'],x['source_animation_index']) for x in cat['clips']]==[('gesture',1,1),('recovery',2,2)]
    assert all(x['duration_s']==float(np.float32(.23333333)) for x in cat['clips'])
    assert all(r[k] is False and cat[k] is False for k in library.FALSE_FLAGS)
    assert read(folder/'target-profile.json')['character_sha256']==sha256(folder/'character.glb')
    assert read(folder/'target-profile.json')['axis_alignment_xyzw']==read(folder/'input/target-profile.json')['axis_alignment_xyzw']
    edit=read(folder/'edit-profile.json')
    assert edit['character_sha256']==sha256(folder/'character.glb') and edit['axis_alignment_xyzw']=={} and edit['world_offset_m']==[0,0,0]
    a=NativeSupportSampler(output.document,output.binary,1);b=NativeSupportSampler(output.document,output.binary,2)
    assert not np.allclose(a.sample(.1),b.sample(.1))
    boundary=cat['boundary_checks'][0];assert boundary['checks']['position_m'] and boundary['checks']['rotation_degrees']
    assert not boundary['checks']['linear_speed_jump_m_s'] and cat['all_declared_boundary_samples_pass'] is False


@pytest.mark.parametrize('fault',['hash','index-boolean','rate-boolean','budget-boolean','budget','duplicate-id','unknown-field','nonadjacent','boundary-boolean','different-reference','different-profile-per-clip'])
def test_incompatible_or_unbounded_recipe_rejects_before_output(study,tmp_path,fault):
    root,_,recipe,_=study;p=copy.deepcopy(recipe)
    if fault=='hash':p['target']['profile']['sha256']='f'*64
    elif fault=='index-boolean':p['clips'][1]['animation_index']=True
    elif fault=='rate-boolean':p['rate']=True
    elif fault=='budget-boolean':p['maximum_planned_pose_transforms']=True
    elif fault=='budget':p['maximum_planned_pose_transforms']=1
    elif fault=='duplicate-id':p['clips'][1]['id']='gesture'
    elif fault=='unknown-field':p['approve']=True
    elif fault=='nonadjacent':p['boundaries'][0]['to']='gesture'
    elif fault=='boundary-boolean':p['boundaries'][0]['limits']['position_m']=True
    elif fault=='different-profile-per-clip':p['clips'][1]['target_profile']=p['target']['profile']
    elif fault=='different-reference':
        source=RigAsset.load(root/p['clips'][1]['glb']['path']);doc=copy.deepcopy(source.document)
        hips=next(n for n in doc['nodes'] if n['name']=='source_Hips');hips['translation'][1]+=.02
        glb=tmp_path/'changed.glb';write_glb(glb,doc,source.binary);profile=read(root/p['clips'][1]['profile']['path']);profile['character_sha256']=sha256(glb)
        pp=tmp_path/'changed-profile.json';save(pp,profile);p['clips'][1]['glb']=dict(path=str(glb),sha256=sha256(glb));p['clips'][1]['profile']=dict(path=str(pp),sha256=sha256(pp))
    recipe_path=tmp_path/'bad-recipe.json'
    for section in [p['target']]+p['clips']:
        for key in ('glb','profile'):section[key]['path']=str((root/section[key]['path']).resolve())
    save(recipe_path,p);out=tmp_path/'out'
    with pytest.raises(ValueError):library.run(recipe_path,out)
    assert not out.exists()


def test_no_declared_seam_is_unknown_and_never_an_empty_success(study):
    _,_,recipe,folder=study;p=copy.deepcopy(recipe);p['boundaries']=[]
    cat=library.catalog(p,read(folder/'prepared.json')['plan'],folder)
    assert cat['boundary_checks_requested'] is False and cat['all_declared_boundary_samples_pass'] is None


def test_stationary_source_boundaries_pass_pose_and_rate_checks_with_one_shared_profile(study,tmp_path):
    root,_,recipe,_=study;p=copy.deepcopy(recipe);target=(root/p['target']['glb']['path']).resolve()
    sp=read(root/p['target']['profile']['path']);sp.pop('axis_alignment_xyzw',None);sp_path=tmp_path/'source-profile.json';save(sp_path,sp)
    for section in [p['target']]:
        for key in ('glb','profile'):section[key]['path']=str((root/section[key]['path']).resolve())
    for clip in p['clips']:
        clip.update(glb=dict(path=str(target),sha256=sha256(target)),profile=dict(path=str(sp_path),sha256=sha256(sp_path)),animation_index=0)
    p['boundaries'][0]['limits']=dict(position_m=1e-6,rotation_degrees=1e-5,linear_speed_jump_m_s=1e-5,angular_speed_jump_degrees_s=1e-5)
    path=tmp_path/'recipe.json';save(path,p);out=tmp_path/'constant-library';library.run(path,out)
    cat=read(out/'catalog.json');assert cat['all_declared_boundary_samples_pass'] is True
    assert all(cat[k] is False for k in library.FALSE_FLAGS)


@pytest.mark.parametrize('fault',['catalog-index','catalog-boundary','catalog-approval','profile-axes','edit-profile-axes','library-bytes','stage-axes','array','drop-original','drop-snapshot','method'])
def test_rehashed_mutations_cannot_fake_library_reference_or_seam_evidence(study,fault):
    _,_,_,folder=study;mutated={p:p.read_bytes() for p in [folder/'result.json',folder/'completion.json']}
    def edit(path,fn):
        path=folder/path;mutated.setdefault(path,path.read_bytes());value=read(path);fn(value);save(path,value)
    try:
        if fault=='catalog-index':edit('catalog.json',lambda r:r['clips'][1].update(animation_index=1))
        elif fault=='catalog-boundary':edit('catalog.json',lambda r:r.update(all_declared_boundary_samples_pass=True))
        elif fault=='catalog-approval':edit('catalog.json',lambda r:r.update(quality_approved=True))
        elif fault=='profile-axes':edit('target-profile.json',lambda r:r.update(axis_alignment_xyzw={}))
        elif fault=='edit-profile-axes':edit('edit-profile.json',lambda r:r.update(axis_alignment_xyzw={'LeftHand':[0,0,1,0]}))
        elif fault=='library-bytes':
            path=folder/'character.glb';mutated[path]=path.read_bytes();path.write_bytes(path.read_bytes()+b'changed')
        elif fault=='stage-axes':
            edit('stages/recovery/target-profile.json',lambda r:r.update(axis_alignment_xyzw={}))
            edit('stages/recovery/report.json',lambda r:r['input_snapshots_sha256'].update({'target-profile.json':sha256(folder/'stages/recovery/target-profile.json')}))
        elif fault=='array':
            path=folder/'stages/gesture/target-transforms.npz';mutated[path]=path.read_bytes()
            with np.load(path,allow_pickle=False) as z:arrays={n:z[n].copy() for n in z.files}
            arrays['global_matrices'][0,0,0,3]+=.01;np.savez_compressed(path,**arrays)
            edit('stages/gesture/report.json',lambda r:r.update(transforms_sha256=sha256(path)))
        elif fault=='drop-original':edit('prepared.json',lambda r:r['original_inputs_sha256'].pop(r['plan']['target']))
        elif fault=='drop-snapshot':edit('prepared.json',lambda r:r['snapshots_sha256'].pop('input/target.glb'))
        else:
            path=folder/'implementation/native_transfer_library.py';mutated[path]=path.read_bytes();path.write_bytes(b'changed method')
        r=read(folder/'result.json');r['prepared_sha256']=sha256(folder/'prepared.json');r['catalog_sha256']=sha256(folder/'catalog.json')
        r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']};r['stage_reports_sha256']={n:sha256(folder/'stages'/n/'report.json') for n in r['stage_reports_sha256']}
        save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        with pytest.raises(ValueError):library.verify(folder)
    finally:
        for path,data in mutated.items():path.write_bytes(data)


def test_failed_stage_keeps_prior_outputs_and_never_finishes_a_library(study,tmp_path,monkeypatch):
    root,_,recipe,_=study;p=copy.deepcopy(recipe)
    for section in [p['target']]+p['clips']:
        for key in ('glb','profile'):section[key]['path']=str((root/section[key]['path']).resolve())
    path=tmp_path/'recipe.json';save(path,p);original=library.transfer.export;calls=0
    def fail(*args,**kw):
        nonlocal calls
        calls+=1
        if calls==2:raise ValueError('second fixture clip failed')
        return original(*args,**kw)
    monkeypatch.setattr(library.transfer,'export',fail);out=tmp_path/'failed'
    with pytest.raises(ValueError,match='second fixture'):library.run(path,out)
    assert (out/'stages/gesture/character.glb').exists() and read(out/'pipeline.json')['status']=='failed'
    assert not (out/'catalog.json').exists() and not (out/'result.json').exists()
