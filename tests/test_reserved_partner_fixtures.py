"""Neutral synthetic package tests; no motion, engine or anatomical approval."""
import copy
from pathlib import Path
import shutil
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reserved_partner_fixtures as fixtures
from gltf_tools import append_accessor, write_glb, global_matrices
from strep import read, save, sha256


def synthetic_reservations(tmp_path):
    root=tmp_path/'inputs';root.mkdir()
    roles=list(fixtures.PARENTS);node_of={r:i for i,r in enumerate(roles)}
    nodes=[dict(name=f'joint-{i}',translation=[0,.1 if i==0 else .02,0]) for i in range(len(roles))]
    for r,p in fixtures.PARENTS.items():
        if p is not None:nodes[node_of[p]].setdefault('children',[]).append(node_of[r])
    nodes.append(dict(mesh=0,skin=0))
    doc=dict(asset=dict(version='2.0'),buffers=[{}],bufferViews=[],accessors=[],nodes=nodes,
        meshes=[dict(primitives=[])],skins=[dict(joints=list(range(len(roles))),skeleton=0)],
        scenes=[dict(nodes=[0,len(roles)])],scene=0)
    binary=bytearray();joints=np.zeros((3,4),dtype='<u2')
    doc['bufferViews'].append(dict(buffer=0,byteOffset=0,byteLength=joints.nbytes));binary.extend(joints.tobytes())
    doc['accessors'].append(dict(bufferView=0,componentType=5123,count=3,type='VEC4'))
    position=append_accessor(doc,binary,[[-.1,-.01,-.05],[.1,.3,-.05],[0,.3,.05]],'VEC3')
    weight=append_accessor(doc,binary,[[1,0,0,0]]*3,'VEC4')
    doc['meshes'][0]['primitives']=[dict(attributes=dict(POSITION=position,JOINTS_0=0,WEIGHTS_0=weight))]
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,binary,
        np.linalg.inv(global_matrices(doc)[:len(roles)]).transpose(0,2,1),'MAT4')
    rows=[];bound={}
    for i in range(3):
        folder=root/f'rig-{i}';folder.mkdir();write_glb(folder/'character.glb',doc,binary)
        save(folder/'rig-profile.json',dict(schema='strep-rig-profile-v1',reference_pose='default_nodes',
            character_sha256=sha256(folder/'character.glb'),mapping=node_of,world_offset_m=[0,0,0],
            axis_alignment_xyzw={},notes='Synthetic source-only fixture, no anatomical validation.'))
        for name in ['LICENSE.md','provenance.json','packing.json']:
            (folder/name).write_text('Synthetic fixture only.\n',encoding='utf-8')
        for p in folder.iterdir():bound[str(p.resolve())]=sha256(p)
        rows.append(dict(id=f'rig-{i}',character=f'rig-{i}/character.glb',profile=f'rig-{i}/rig-profile.json',
            character_sha256=sha256(folder/'character.glb'),profile_sha256=sha256(folder/'rig-profile.json')))
    save(root/'construction-proof.json',dict(reserved_action_trials=0,quality_approved=False,
        rows=[dict(id=r['id']) for r in rows],inputs=bound))
    pairs=[dict(id=f'pair-{i}',actor_a=f'rig-{i}',actor_b=f'rig-{(i+1)%3}') for i in range(3)]
    rigs=dict(rigs=rows,partner_pairings=pairs,construction_verification='construction-proof.json',
              construction_verification_sha256=sha256(root/'construction-proof.json'))
    save(root/'rig-catalog.json',rigs)
    catalog=dict(schema='strep-reserved-partner-layouts-v1',rig_catalog_sha256=sha256(root/'rig-catalog.json'),
        floor_y_m=0.,minimum_initial_z_clearance_m=.5,pairings=[dict(p,rig_origin_separation_z_m=1.+i*.1) for i,p in enumerate(pairs)],
        use_policy='Synthetic fixture; not release evidence.',anatomical_facing_reviewed=False,
        contact_targets_bound=False,motion_trials_executed=False,release_approved=False)
    save(root/'catalog.json',catalog)
    return root,catalog,rigs


def build(tmp_path):
    root,catalog,rigs=synthetic_reservations(tmp_path)
    out=tmp_path/'bundle'
    result=fixtures.run(root/'catalog.json',root/'rig-catalog.json',out,source_root=root)
    return root,out,result


def test_full_portable_set_replays_without_original_asset_paths(tmp_path):
    root,out,result=build(tmp_path)
    assert len(result['pairings'])==len(result['checks'])==3
    assert all(r['vertices']==dict(A=3,B=3) and r['role_origins']==dict(A=19,B=19) for r in result['checks'])
    before=fixtures.verify(out)
    portable=tmp_path/'moved bundle';shutil.copytree(out,portable)
    shutil.move(str(root),str(tmp_path/'original assets moved'))
    assert fixtures.verify(portable)==before
    assert result['motion_trials_executed']==0 and not result['engine_executed'] and not result['release_approved']


def test_grounding_uses_all_vertices_and_opposing_axes():
    points=np.array([[0,.2,.1],[0,-.3,-.1],[.5,1,.02]])
    original=points.copy()
    a,pa=fixtures.layout(points,actor='A',separation_z_m=1.)
    b,pb=fixtures.layout(points,actor='B',separation_z_m=1.)
    assert a['translation_m']==[0,.3,-.5] and b['translation_m']==[0,.3,.5]
    assert pa[:,1].min()==pb[:,1].min()==0
    assert np.array_equal(pb[:,0],-points[:,0])
    assert np.array_equal(points,original)


@pytest.mark.parametrize('fault',['missing_pair','reordered_pair','reversed_pair','self_pair','unsafe_id',
    'zero_separation','nan_separation','bound_contacts','motion_claim','release_claim','rig_digest','floor'])
def test_catalog_rejects_changed_reservation_or_unearned_scope(tmp_path,fault):
    root,catalog,rigs=synthetic_reservations(tmp_path)
    if fault=='missing_pair':catalog['pairings'].pop()
    if fault=='reordered_pair':catalog['pairings'].reverse()
    if fault=='reversed_pair':catalog['pairings'][0]['actor_a'],catalog['pairings'][0]['actor_b']=catalog['pairings'][0]['actor_b'],catalog['pairings'][0]['actor_a']
    if fault=='self_pair':catalog['pairings'][0]['actor_b']=catalog['pairings'][0]['actor_a']
    if fault=='unsafe_id':catalog['pairings'][0]['id']='../escape'
    if fault=='zero_separation':catalog['pairings'][0]['rig_origin_separation_z_m']=0
    if fault=='nan_separation':catalog['pairings'][0]['rig_origin_separation_z_m']=float('nan')
    if fault=='bound_contacts':catalog['contact_targets_bound']=True
    if fault=='motion_claim':catalog['motion_trials_executed']=True
    if fault=='release_claim':catalog['release_approved']=True
    if fault=='rig_digest':catalog['rig_catalog_sha256']='0'*64
    if fault=='floor':catalog['floor_y_m']=.1
    with pytest.raises(ValueError):fixtures.validate_catalog(catalog,rigs,sha256(root/'rig-catalog.json'))


@pytest.mark.parametrize('fault',['observations','placement','missing_array','missing_attachment','changed_attachment','summary'])
def test_saved_package_mutation_is_rejected(tmp_path,fault):
    root,out,result=build(tmp_path);folder=out/'pairs/pair-0'
    if fault in ('observations','missing_array'):
        with np.load(folder/'observations.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
        if fault=='observations':arrays['A_placed_vertices_m'][0,0]+=.00001
        else:arrays.pop('B_source_role_positions_m')
        np.savez_compressed(folder/'observations.npz',**arrays)
    if fault=='placement':
        scene=read(folder/'scene.json');scene['actors']['A']['placement']['translation_m'][1]+=.01;save(folder/'scene.json',scene)
    if fault=='missing_attachment':(folder/'actors/B/LICENSE.md').unlink()
    if fault=='changed_attachment':(folder/'actors/A/provenance.json').write_text('changed',encoding='utf-8')
    if fault=='summary':
        changed=read(out/'result.json');changed['checks'][0]['initial_z_clearance_m']=999;save(out/'result.json',changed)
    with pytest.raises((ValueError,FileNotFoundError)):fixtures.verify(out)


def test_reducer_rejects_numeric_drift_even_after_rebinding_transport_hash(tmp_path):
    root,out,result=build(tmp_path);folder=out/'pairs/pair-0'
    with np.load(folder/'observations.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
    arrays['B_placed_role_positions_m'][0,0]=.001
    with pytest.raises(ValueError):fixtures.reduce(read(folder/'scene.json'),arrays,minimum_clearance_m=.5)


def test_overlap_never_approves_initial_layout(tmp_path):
    root,catalog,rigs=synthetic_reservations(tmp_path)
    catalog['pairings'][0]['rig_origin_separation_z_m']=.05;save(root/'catalog.json',catalog)
    out=tmp_path/'failed bundle'
    with pytest.raises(ValueError):fixtures.run(root/'catalog.json',root/'rig-catalog.json',out,source_root=root)
    assert read(out/'pipeline.json')['status']=='failed'
    assert not (out/'result.json').exists()


@pytest.mark.parametrize('points,actor,distance',[(np.zeros((0,3)),'A',1),([[0,float('nan'),0]],'A',1),
    ([[0,0,0]],'C',1),([[0,0,0]],'A',0),([[0,0,0]],'A',True)])
def test_bad_layout_inputs_rejected(points,actor,distance):
    with pytest.raises(ValueError):fixtures.layout(points,actor=actor,separation_z_m=distance)


def test_existing_output_is_not_overwritten(tmp_path):
    root,out,result=build(tmp_path)
    with pytest.raises(ValueError):fixtures.run(root/'catalog.json',root/'rig-catalog.json',out,source_root=root)
    assert fixtures.verify(out)==result['checks']


def test_rebound_attachment_hash_still_cannot_change_original_license(tmp_path):
    root,out,result=build(tmp_path);folder=out/'pairs/pair-0'
    path=folder/'actors/A/LICENSE.md';path.write_text('Rebound forged license.',encoding='utf-8')
    scene=read(folder/'scene.json');scene['actors']['A']['files']['LICENSE.md']['sha256']=sha256(path)
    save(folder/'scene.json',scene)
    result['pairings'][0]['scene_sha256']=sha256(folder/'scene.json');save(out/'result.json',result)
    with pytest.raises(ValueError,match='original construction binding'):fixtures.verify(out)


def test_extra_scene_approval_field_is_rejected(tmp_path):
    root,out,result=build(tmp_path);folder=out/'pairs/pair-0'
    scene=read(folder/'scene.json');scene['quality_approved']=True
    with np.load(folder/'observations.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
    with pytest.raises(ValueError,match='explicit neutral scene'):fixtures.reduce(scene,arrays,minimum_clearance_m=.5)
