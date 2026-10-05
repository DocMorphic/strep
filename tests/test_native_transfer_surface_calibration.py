"""Independent closed cube skins: full topology/contacts, no anatomical proof."""
import copy
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import native_transfer_surface_calibration as calibration
import native_transfer_scene as bridge
import native_rig_transfer as transfer
import native_surface_contact as surface
from native_scene_contacts import SceneContacts
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256
from test_native_rig_transfer import fixture
from test_native_transfer_scene import stationary,moving_root


def closed_skin(path,profile):
    rig=RigAsset.load(path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    cube=trimesh.creation.box(extents=[.03]*3)
    positions=np.concatenate([cube.vertices+rig.reference[n,:3,3] for n in rig.joints])
    faces=np.concatenate([cube.faces+8*i for i in range(len(rig.joints))])
    def unsigned(values,kind):
        values=np.asarray(values,dtype='<u2')
        while len(binary)%4:binary.append(0)
        doc['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=values.nbytes));binary.extend(values.tobytes())
        doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1,componentType=5123,count=len(values),type=kind));return len(doc['accessors'])-1
    joints=np.zeros((len(positions),4),int);joints[:,0]=np.repeat(np.arange(len(rig.joints)),8)
    weights=np.zeros_like(joints,dtype=float);weights[:,0]=1
    doc['meshes'][0]['primitives']=[dict(material=0,attributes=dict(POSITION=append_accessor(doc,binary,positions,'VEC3'),
        JOINTS_0=unsigned(joints,'VEC4'),WEIGHTS_0=append_accessor(doc,binary,weights,'VEC4')),indices=unsigned(faces.ravel(),'SCALAR'))]
    write_glb(path,doc,binary);p=read(profile);p['character_sha256']=sha256(path);save(profile,p)


def face_patch(rig,role,axis,sign):
    node=next(i for i,n in enumerate(rig.document['nodes']) if n.get('name','').endswith('_'+role))
    skin=NativeSupportSkin(rig);ids=np.flatnonzero(skin.nodes[:,0]==node);values=rig.primitives[0]['positions'][ids,axis]
    ids=ids[np.isclose(values,values.max() if sign>0 else values.min(),atol=1e-8,rtol=0)]
    positions=rig.primitives[0]['positions'][ids];order=np.lexsort((positions[:,1],positions[:,0]))
    return skin.vertex_references[ids[order]].tolist()


def scene_fixture(folder,*,bad_plane=False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    a,ap=fixture(folder,'actor',axes=23);b,bp=fixture(folder,'replacement',axes=-31,reverse=True,animated=False)
    partner,pp=fixture(folder,'partner',axes=9)
    for path,profile in [(a,ap),(b,bp),(partner,pp)]:
        closed_skin(path,profile)
        if path!=b:stationary(path,profile);moving_root(path,profile)
    target=read(bp);target['axis_alignment_xyzw']=dict(LeftHand=Rotation.from_euler('x',10,degrees=True).as_quat().tolist());save(bp,target)
    ra,rb,rc=[RigAsset.load(p) for p in (a,b,partner)]
    hand=face_patch(ra,'LeftHand',2,-1);other=face_patch(rc,'RightHand',2,1)
    boxhand=face_patch(ra,'RightHand',2,-1);foot=face_patch(ra,'LeftFoot',1,-1)
    def vertices(rig,refs,t=0.):
        skin=NativeSupportSkin(rig);table={tuple(v):i for i,v in enumerate(skin.vertex_references)}
        sampler=NativeSupportSampler(rig.document,rig.binary,0)
        return rig.vertices(sampler.sample(t))[[table[tuple(v)] for v in refs]]
    placement=vertices(ra,hand).mean(0)-vertices(rc,other).mean(0)-[0,0,.001]
    pose=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]);reader=NativeSupportSampler(ra.document,ra.binary,0)
    grip=vertices(ra,boxhand).mean(0);center=grip-[0,0,.026];time=.0853725
    spec=dict(schema='strep-native-scene-contacts-v1',duration_s=reader.duration,actors=dict(
        A=dict(glb=a.name,sha256=sha256(a),animation_index=0,placement=copy.deepcopy(pose)),
        B=dict(glb=partner.name,sha256=sha256(partner),animation_index=0,placement={**pose,'translation_m':placement.tolist()})),
        objects=dict(box=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.05]*3),
            keyframes=[dict(time_s=t,translation_m=(center+np.array([.04,.005,-.015])*t/reader.duration).tolist(),rotation_xyzw=[0,0,0,1]) for t in (0.,reader.duration)])),contacts=[])
    def contact(name,actor,refs,target):
        return dict(id=name,actor=actor,vertices=refs,reduction='centroid',target=target,mode='hold',interval_s=[.02,.18],
            limits=dict(position_m=.005,relative_speed_m_s=.002))
    spec['contacts']=[contact('foot','A',foot,dict(space='world',points_m=(vertices(ra,foot,time).mean(0)+[0,-.001,0])[None].tolist())),
        contact('box-grip','A',boxhand,dict(space='object',object='box',points_m=[[0,0,.025]])),
        contact('partner','A',hand,dict(space='actor',actor='B',vertices=other,reduction='centroid')),
        contact('partner-initiated','B',other,dict(space='actor',actor='A',vertices=hand,reduction='centroid'))]
    spec['contacts'][0].update(mode='touch',interval_s=[time,time],limits=dict(position_m=.005))
    scene=folder/'scene.json';save(scene,spec);candidate=folder/'transfer';transfer.export(a,ap,b,bp,0,candidate,120)
    pairs=[dict(source=l,target=r) for role,axis,sign in [('LeftFoot',1,-1),('LeftHand',2,-1),('RightHand',2,-1)]
        for l,r in zip(face_patch(ra,role,axis,sign),face_patch(rb,role,axis,sign))]
    recipe=folder/'bridge.json';save(recipe,dict(schema=bridge.SCHEMA,contacts=dict(path=scene.name,sha256=sha256(scene)),
        transfers=dict(A=dict(candidate=dict(path=candidate.name,sha256=sha256(candidate/'report.json')),vertex_map=pairs))))
    comparison=folder/'comparison';bridge.run(recipe,comparison);digest=sha256(comparison/'contacts.json')
    sp=folder/'surface-policy.json';save(sp,dict(schema='strep-native-surface-contact-v1',contacts_sha256=digest,
        limits=dict(maximum_opposition_error_degrees=1.,backface_allowance_m=.00005,minimum_normal_area_m2=1e-12,minimum_normal_coherence=.1),
        maximum_actor_pose_queries=20000,contacts={'foot':dict(target_normal=dict(space='world',normals=[[0,1,0]])),
            'box-grip':dict(target_normal=dict(space='object',normals=[[0,0,1]])),
            'partner':dict(target_normal=dict(space='partner-surface')),'partner-initiated':dict(target_normal=dict(space='partner-surface'))}))
    gp=folder/'geometry-policy.json';save(gp,dict(schema='strep-native-scene-geometry-v1',contacts_sha256=digest,
        clock=dict(mode='native-and-frame-populations',times_s=[0.,reader.duration]),
        limits=dict(penetration_m=.0001,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0,1,0],offset_m=.5 if bad_plane else .18))))
    path=folder/'calibration.json';save(path,dict(schema=calibration.SCHEMA,comparison=dict(path=comparison.name,sha256=sha256(comparison/'result.json')),
        surface_policy=dict(path=sp.name,sha256=sha256(sp)),geometry_policy=dict(path=gp.name,sha256=sha256(gp)),
        actors=dict(A=dict(role_rotations_degrees=dict(LeftHand=15),maximum_root_offset_m=0.,maximum_joint_displacement_m=.02)),
        search=dict(evaluations=60,calls=400,seconds=90,starts=1)))
    return path


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('surface-calibration');recipe=scene_fixture(root);out=root/'fit'
    return recipe,out,calibration.run(recipe,out)


def test_surface_guidance_corrects_normals_and_passes_full_declared_mesh_samples(study):
    recipe,out,result=study
    original=out/'comparison';scene=SceneContacts(read(original/'contacts.json'),original)
    before,_=surface.evaluate(scene,read(out/'input-surface_policy.json'),sha256(original/'contacts.json'))
    assert before['point_contacts_pass'] and not before['surface_contacts_pass']
    assert result['sampled_authoring_conditions_pass'] and result['surface_common_clock_pass']
    assert result['surface_contact_samples_pass'] and result['geometry_samples_pass']
    bounds=read(out/'decoded-bounds.json');assert bounds['surface']['maximum_opposition_error_degrees']<=1
    assert all(not any(a['source_rate_failed_rows']) for a in bounds['actors'])
    assert all(result[k] is False for k in ('geometry_verified','surface_orientation_verified','engine_playback_verified',
        'collision_verified','continuous_collision_certified','anatomical_reviewed','quality_approved','release_approved'))
    assert read(out/'contacts.json')['contacts']==read(original/'contacts.json')['contacts']
    assert calibration.verify(out,sha256(out/'result.json'))==result


def test_both_partner_directions_and_every_geometry_population_are_present(study):
    _,out,_=study;mesh=read(out/'geometry-audit.json');surface_report=read(out/'surface-audit.json')
    assert {c['id'] for c in surface_report['contacts']}=={'foot','box-grip','partner','partner-initiated'}
    assert len(mesh['frame_populations'])==12
    assert all(len(s['actor_pairs'])==1 and len(s['actor_objects'])==2 and len(s['world_planes'])==2 for s in mesh['samples'])
    assert all(v['containment_available'] for s in mesh['samples'] for v in s['volumes'].values())
    bound=bridge.transfer_audit.bound_candidate(out/'transfer-A')
    assert transfer.preserves_target(bound[3],bound[7],bound[1]['target_mapping'])


def test_relocated_full_surface_and_geometry_replay(study,tmp_path):
    _,out,result=study;moved=tmp_path/'portable';shutil.copytree(out,moved)
    assert calibration.verify(moved,sha256(out/'result.json'))==result


@pytest.mark.parametrize('fault',['surface-limit','geometry-limit','plane','normal','geometry-array','surface-array','controls','quality','typed','method'])
def test_rehashed_surface_geometry_or_scope_corruption_rejects(study,tmp_path,fault):
    _,source,_=study;out=tmp_path/'changed';shutil.copytree(source,out)
    if fault in ('surface-limit','normal'):
        path=out/'surface-policy.json';value=read(path)
        if fault=='surface-limit':value['limits']['maximum_opposition_error_degrees']=90
        else:value['contacts']['foot']['target_normal']['normals']=[[0,-1,0]]
        save(path,value)
    elif fault in ('geometry-limit','plane'):
        path=out/'geometry-policy.json';value=read(path)
        if fault=='geometry-limit':value['limits']['penetration_m']=.1
        else:value['planes']['floor']['offset_m']=-5
        save(path,value)
    elif fault.endswith('-array'):
        path=out/('geometry-observations.npz' if fault=='geometry-array' else 'surface-observations.npz')
        with np.load(path,allow_pickle=False) as data:arrays={k:data[k].copy() for k in data.files}
        key=next(k for k in arrays if arrays[k].dtype==np.dtype('float64') and arrays[k].size);arrays[key].flat[0]+=.01
        np.savez_compressed(path,**arrays)
    elif fault=='controls':
        path=out/'search.json';value=read(path);value['controls'][0]+=.01;save(path,value)
    elif fault=='method':(out/'implementation/native_transfer_surface_calibration.py').write_text('changed',encoding='utf8')
    result=read(out/'result.json')
    if fault=='quality':result['quality_approved']=True
    elif fault=='typed':result['geometry_samples_pass']=1
    result['files_sha256']=calibration.base.payload_hashes(out);save(out/'result.json',result)
    with pytest.raises(ValueError):calibration.verify(out)


def test_complete_surface_and_geometry_budgets_reject_without_partial_rows(study,monkeypatch):
    _,out,_=study;recipe=read(out/'recipe.json');sp=read(out/'input-surface_policy.json');gp=read(out/'input-geometry_policy.json')
    monkeypatch.setattr(calibration,'GEOMETRY_SCALAR_LIMIT',1)
    with pytest.raises(ValueError,match='no truncation'):calibration.SurfaceProblem(out/'comparison',recipe,sp,gp)
    monkeypatch.setattr(calibration,'GEOMETRY_SCALAR_LIMIT',33554432);sp['maximum_actor_pose_queries']=1
    with pytest.raises(ValueError,match='no partial'):calibration.SurfaceProblem(out/'comparison',recipe,sp,gp)


def test_full_geometry_failure_cannot_be_approved_by_point_and_surface_success(study,tmp_path):
    _,source,_=study;out=tmp_path/'blocked';shutil.copytree(source,out)
    problem=calibration.verified_problem(out);spec=read(out/'contacts.json')
    problem.geometry_policy['planes']['floor']['offset_m']=.5
    comparison,_,_,residual,bounds,_,_,orientation,_,mesh,_=calibration.audits(problem,spec,out)
    result=calibration.outcome('complete',comparison,bounds,residual,orientation,mesh)
    assert result['candidate_contact_samples_pass'] and result['surface_contact_samples_pass']
    assert not result['geometry_samples_pass'] and not result['sampled_authoring_conditions_pass']
