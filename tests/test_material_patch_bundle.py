"""Portable explicit region authoring and animation/storage-only rig transfer."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_rig_material_patch import fixture
from rig_asset import RigAsset, array
from gltf_tools import append_accessor, write_glb
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from strep import read, save, sha256
import material_patch_bundle as bundles
from rig_material_identity import descriptor, digest


def author(tmp_path, *, two=True):
    a,b = fixture(tmp_path/'source')
    selector = dict(include_children=True,minimum_weight=1.,minimum_twice_area_m2=1e-12,
                    maximum_faces=512,maximum_vertices=256)
    rows = [dict(id='left-surface',role='LeftHand',face_references=[[6,0,0]],selector=selector)]
    if two: rows.append(dict(id='right-surface',role='RightHand',face_references=[[6,1,0]],selector=copy.deepcopy(selector)))
    value = dict(schema=bundles.SELECTION_SCHEMA,source=bundles.source_binding(a,b),patches=rows)
    selection = tmp_path/'selection.json'; save(selection,value)
    out = tmp_path/'authored'; result = bundles.create(a,b,selection,out)
    return a,b,selection,out,result


def target_from(source, profile, folder, mutation=None):
    folder.mkdir(); rig = RigAsset.load(source); doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    times = append_accessor(doc,binary,[0,.25,.5,.75,1], 'SCALAR')
    values = append_accessor(doc,binary,[[0,0,v] for v in [0,.25,.5,.75,1]],'VEC3')
    doc['animations'] = [dict(name='edited animation',samplers=[dict(input=times,output=values,interpolation='LINEAR')],
        channels=[dict(sampler=0,target=dict(node=1,path='translation'))])]
    if mutation is not None: mutation(doc,binary)
    a,b = folder/'character.glb',folder/'rig-profile.json'; write_glb(a,doc,binary)
    value = read(profile); value['character_sha256'] = sha256(a); save(b,value)
    return a,b


def move(parent, a, b, output):
    return bundles.transfer(parent,a,b,output,character_sha256=sha256(a),profile_sha256=sha256(b))


def test_complete_multiple_patch_bundle_replays_after_original_inputs_move(tmp_path):
    a,b,selection,out,result = author(tmp_path)
    assert result['selected_geometry_patches'] == 2 and result['transfer_depth'] == 0
    assert [r['id'] for r in result['patches']] == ['left-surface','right-surface']
    assert all(r['faces'] == 1 and r['vertices'] == 3 for r in result['patches'])
    before = bundles.files(out); moved = tmp_path/'portable'; shutil.move(str(out),str(moved))
    shutil.move(str(a.parent),str(tmp_path/'source unavailable')); selection.unlink()
    assert bundles.verify(moved,expected_result_sha256=sha256(moved/'result.json')) == result
    assert bundles.files(moved) == before


def test_added_animation_preserves_every_patch_and_pins_new_source_bytes(tmp_path):
    a,b,_,out,previous = author(tmp_path); target,profile = target_from(a,b,tmp_path/'target')
    transferred = tmp_path/'transferred'; result = move(out,target,profile,transferred)
    assert result['transfer_depth'] == 1 and result['selected_geometry_patches'] == 2
    proof = read(transferred/'transfer.json')
    assert proof['complete_static_identity_equal'] and proof['raw_weights_preserved']
    assert not any(proof[k] for k in ('animations_compared','materials_textures_compared','anatomy_verified','quality_approved','release_approved'))
    assert sha256(a) != sha256(target)
    for left,right in zip(previous['patches'],result['patches']):
        original = read(out/left['path']); changed = read(transferred/right['path'])
        assert changed['source']['character_sha256'] == sha256(target)
        original['source'] = changed['source']; assert original == changed
    shutil.move(str(out),str(tmp_path/'parent unavailable')); shutil.move(str(target.parent),str(tmp_path/'target unavailable'))
    assert bundles.verify(transferred) == result


def scene_for(path, patch):
    pose = dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])
    actor = dict(glb=str(path),sha256=sha256(path),animation_index=0,placement=pose)
    row = dict(id='touch',actor='A',vertices=patch['vertices'],reduction='individual',
        target=dict(space='actor',actor='B',vertices=patch['vertices'],reduction='individual'),
        mode='touch',interval_s=[.5,.5],limits=dict(position_m=0))
    spec = dict(schema='strep-native-scene-contacts-v1',duration_s=1.,actors=dict(A=actor,B=copy.deepcopy(actor)),objects={},contacts=[row])
    return spec,SceneContacts(spec,path.parent)


def test_actual_native_edit_export_transfers_and_native_reader_samples_skin_points(tmp_path):
    a,b,_,out,_ = author(tmp_path,two=False); target,profile = target_from(a,b,tmp_path/'animated')
    stage = tmp_path/'animated-patches'; move(out,target,profile,stage)
    patch = read(stage/'patches/left-surface.json'); _,scene = scene_for(target,patch)
    permissions = dict(schema='strep-native-scene-edit-v1',contacts_sha256='3'*64,actors=dict(A=dict(
        window_s=[0,1],protected_s=[],knots_s=[0,.5,1],tracks=[dict(node=1,path='translation',maximum_change=.01)],
        maximum_joint_displacement_m=.01)))
    edits = SceneEdits(permissions,scene,'3'*64); controls = edits.initial.copy(); controls[0] = .1
    proposed = tmp_path/'proposed.glb'; edits.export('A',controls,proposed)
    assert edits.audit('A',proposed,0)['passed']
    updated = read(profile); updated['character_sha256'] = sha256(proposed); updated_profile = tmp_path/'proposed-profile.json'; save(updated_profile,updated)
    final = tmp_path/'edited-patches'; result = move(stage,proposed,updated_profile,final)
    assert result['transfer_depth'] == 2
    new_patch = read(final/'patches/left-surface.json'); _,new_scene = scene_for(proposed,new_patch)
    material = bundles.surface(proposed,updated_profile,bundles.source_binding(proposed,updated_profile))
    worlds = new_scene.actors['A']['sampler'].sample(.5)
    np.testing.assert_allclose(new_scene.actor_points('A',new_scene.rows[0]['ids'],[.5])[0],
        material.posed(new_patch,worlds)['positions_m'],atol=1e-15,rtol=0)


def mutate_payload(doc,binary,accessor,offset,delta):
    item = doc['accessors'][accessor]; view = doc['bufferViews'][item['bufferView']]
    dtype = {5126:'<f4',5123:'<u2'}[item['componentType']]
    values = np.frombuffer(binary,dtype=dtype,count=item['count']*{'VEC3':3,'VEC4':4,'SCALAR':1,'MAT4':16}[item['type']],
        offset=view.get('byteOffset',0)+item.get('byteOffset',0))
    values[offset] += delta


@pytest.mark.parametrize('fault',['position','outside-patch-position','weights','zero-joint-slot','indices','bind',
    'default-node','hierarchy','normal-attribute','skin-order','primitive-metadata'])
def test_complete_deformation_changes_reject_even_outside_selected_patch(tmp_path,fault):
    a,b,_,out,_ = author(tmp_path,two=False)
    def mutation(doc,binary):
        primitive = doc['meshes'][0]['primitives'][0]; attrs = primitive['attributes']
        if fault == 'position': mutate_payload(doc,binary,attrs['POSITION'],0,.01)
        elif fault == 'outside-patch-position': mutate_payload(doc,binary,doc['meshes'][1]['primitives'][0]['attributes']['POSITION'],0,.01)
        elif fault == 'weights':
            # The raw weight change stays within RigAsset's normalization tolerance.
            mutate_payload(doc,binary,attrs['WEIGHTS_0'],0,.00005)
        elif fault == 'zero-joint-slot': mutate_payload(doc,binary,attrs['JOINTS_0'],3,1)
        elif fault == 'indices': mutate_payload(doc,binary,primitive['indices'],0,1)
        elif fault == 'bind': mutate_payload(doc,binary,doc['skins'][0]['inverseBindMatrices'],12,.01)
        elif fault == 'default-node': doc['nodes'][3]['translation'] = [.01,0,0]
        elif fault == 'hierarchy': doc['nodes'][0]['children'].reverse()
        elif fault == 'normal-attribute': attrs['NORMAL'] = append_accessor(doc,binary,[[0,0,1]]*4,'VEC3')
        elif fault == 'skin-order': doc['skins'][0]['joints'].reverse()
        else: primitive['extras'] = dict(changed=True)
    target,profile = target_from(a,b,tmp_path/'changed',mutation)
    with pytest.raises(ValueError): move(out,target,profile,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


@pytest.mark.parametrize('field,value',[('mapping',dict(Root=0,LeftHand=1,RightHand=3)),('notes','changed-profile')])
def test_changed_profile_rejects(tmp_path,field,value):
    a,b,_,out,_ = author(tmp_path); target,profile = target_from(a,b,tmp_path/'changed')
    data = read(profile); data[field] = value; save(profile,data)
    with pytest.raises(ValueError): move(out,target,profile,tmp_path/'rejected')


def repack(path, output):
    rig = RigAsset.load(path); doc = copy.deepcopy(rig.document); binary = bytearray(); new_accessors=[]; views=[]; mapping={}
    for number in reversed(range(len(doc['accessors']))):
        item = copy.deepcopy(doc['accessors'][number]); values = array(rig.document,rig.binary,number)
        if item['type'] == 'MAT4': values = values.transpose(0,2,1)
        while len(binary)%4: binary.append(0)
        binary.extend(b'\0'*4)
        mapping[number] = len(new_accessors); item['bufferView'] = len(views); item.pop('byteOffset',None)
        views.append(dict(buffer=0,byteOffset=len(binary),byteLength=values.nbytes)); binary.extend(values.tobytes())
        new_accessors.append(item)
    doc['accessors'] = new_accessors; doc['bufferViews'] = views
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            primitive['attributes'] = {k:mapping[n] for k,n in primitive['attributes'].items()}
            if 'indices' in primitive: primitive['indices'] = mapping[primitive['indices']]
    for skin in doc['skins']: skin['inverseBindMatrices'] = mapping[skin['inverseBindMatrices']]
    for animation in doc.get('animations',[]):
        for sampler in animation['samplers']:
            sampler['input'] = mapping[sampler['input']]; sampler['output'] = mapping[sampler['output']]
    write_glb(output,doc,binary)


def test_accessor_and_buffer_repacking_does_not_require_identical_file_prefix(tmp_path):
    a,b,_,out,_ = author(tmp_path); target = tmp_path/'repacked.glb'; repack(a,target)
    profile = tmp_path/'repacked-profile.json'; data = read(b); data['character_sha256'] = sha256(target); save(profile,data)
    assert sha256(a) != sha256(target)
    result = move(out,target,profile,tmp_path/'repacked-patches'); assert result['transfer_depth'] == 1
    assert read(tmp_path/'repacked-patches/transfer.json')['complete_static_identity_equal']


def rebound_patch(out, field, value):
    result = read(out/'result.json'); manifest = result['patches'][0]; path = out/manifest['path']
    patch = read(path); patch[field] = value; save(path,patch); manifest['sha256'] = sha256(path); save(out/'result.json',result)


@pytest.mark.parametrize('field,value',[('anatomy_verified',True),('contact_target_approved',True),('vertices',[[6,0,3]]),
    ('reference_positions_m',[[999,0,0]]),('winding',{}),('source',{})])
def test_rebound_authored_patch_rejects(tmp_path,field,value):
    _,_,_,out,_ = author(tmp_path); rebound_patch(out,field,value)
    with pytest.raises(ValueError): bundles.verify(out)


@pytest.mark.parametrize('fault',['missing','duplicate','reverse','counts','extra','method','identity','source','false-approval','pinned-result'])
def test_portable_result_and_evidence_integrity(tmp_path,fault):
    _,_,_,out,result = author(tmp_path)
    if fault == 'missing': result['patches'].pop()
    elif fault == 'duplicate': result['patches'][1] = copy.deepcopy(result['patches'][0])
    elif fault == 'reverse': result['patches'].reverse()
    elif fault == 'counts': result['selected_geometry_patches'] = True
    elif fault == 'extra': (out/'secret.txt').write_text('Unrelated file must not be copied on transfer.')
    elif fault == 'method': (out/'implementation/rig_material_identity.py').write_text('# changed')
    elif fault == 'identity':
        value = read(out/'identity.json'); value['nodes'] = []; save(out/'identity.json',value)
        request = read(out/'request.json'); request['identity_sha256'] = sha256(out/'identity.json'); save(out/'request.json',request)
        result['request_sha256'] = sha256(out/'request.json')
    elif fault == 'source': (out/'input/character.glb').write_bytes(b'changed')
    elif fault == 'false-approval': result['anatomy_verified'] = True
    else:
        with pytest.raises(ValueError,match='caller binding'): bundles.verify(out,expected_result_sha256='0'*64)
        return
    save(out/'result.json',result)
    with pytest.raises(ValueError): bundles.verify(out)


@pytest.mark.parametrize('fault',['empty','duplicate','unsafe-id','extra','source','selector','disconnected','degenerate','budget'])
def test_invalid_explicit_selections_reject_before_creating_output(tmp_path,fault):
    a,b,selection,out,_ = author(tmp_path); data = read(selection)
    if fault == 'empty': data['patches'] = []
    elif fault == 'duplicate': data['patches'] *= 2
    elif fault == 'unsafe-id': data['patches'][0]['id'] = '../outside'
    elif fault == 'extra': data['reviewed'] = True
    elif fault == 'source': data['source']['character_sha256'] = '0'*64
    elif fault == 'selector': data['patches'][0]['selector']['anatomical'] = True
    elif fault == 'disconnected': data['patches'][0]['face_references'].append([7,0,0])
    elif fault == 'degenerate': data['patches'][0]['face_references'] = [[6,0,3]]
    else: data['patches'][0]['selector']['maximum_vertices'] = 2
    save(selection,data); rejected = tmp_path/'rejected'
    with pytest.raises(ValueError): bundles.create(a,b,selection,rejected)
    assert not rejected.exists()


def test_inventory_produces_complete_candidates_and_no_selected_defaults(tmp_path):
    a,b = fixture(tmp_path/'rig'); out = tmp_path/'inventory'
    result = bundles.inventory(a,b,out,['LeftHand','RightHand'])
    assert [len(r['face_references']) for r in result] == [3,1]
    template = read(out/'selection-template.json'); assert template['patches'] == []
    assert read(out/'inventory.json')['selected_patches'] == 0
    with pytest.raises(ValueError,match='no invented'): bundles.create(a,b,out/'selection-template.json',tmp_path/'authored')


def test_depth_limit_is_explicit_and_keeps_all_parent_evidence(tmp_path):
    a,b,_,out,_ = author(tmp_path,two=False); parent = out
    for i in range(bundles.MAXIMUM_TRANSFER_DEPTH):
        target,profile = target_from(a,b,tmp_path/f'target-{i}')
        parent_next = tmp_path/f'bundle-{i}'; assert move(parent,target,profile,parent_next)['transfer_depth'] == i+1
        parent = parent_next
    with pytest.raises(ValueError,match='maximum depth'): move(parent,a,b,tmp_path/'too-deep')
    assert not (tmp_path/'too-deep').exists()


def test_cli_create_verify_and_transfer_use_real_sources(tmp_path):
    a,b,selection,_,_ = author(tmp_path)
    script = Path(bundles.__file__); cli = tmp_path/'cli'; target,profile = target_from(a,b,tmp_path/'target')
    commands = [['create',str(a),str(b),str(selection),str(cli)], ['verify',str(cli)],
        ['transfer',str(cli),str(target),str(profile),str(tmp_path/'cli-transfer'),
         '--character-sha256',sha256(target),'--profile-sha256',sha256(profile)]]
    for command in commands:
        proc = subprocess.run([sys.executable,str(script),*command],capture_output=True,text=True)
        assert proc.returncode == 0, proc.stdout+proc.stderr
    assert bundles.verify(tmp_path/'cli-transfer')['transfer_depth'] == 1


@pytest.mark.parametrize('fault',['parent-extra','selection','proof','depth','missing-parent-pin'])
def test_transfer_parent_selection_and_proof_cannot_be_rebound(tmp_path,fault):
    a,b,_,out,_ = author(tmp_path); target,profile = target_from(a,b,tmp_path/'target')
    moved = tmp_path/'transfer'; move(out,target,profile,moved)
    request = read(moved/'request.json'); result = read(moved/'result.json')
    if fault == 'parent-extra':
        (moved/'parent/unrelated.txt').write_text('Extra parent payload')
        request['parent_file_sha256'] = bundles.files(moved/'parent')
    elif fault == 'selection':
        path = moved/'input/selection.json'; value = read(path); value['patches'][0]['face_references'] = [[6,0,2]]
        save(path,value); request['input_sha256']['selection.json'] = sha256(path)
    elif fault == 'proof':
        path = moved/'transfer.json'; value = read(path); value['raw_weights_preserved'] = False
        save(path,value); request['transfer_sha256'] = sha256(path)
    elif fault == 'missing-parent-pin': request['parent_result_sha256'] = None
    else: result['transfer_depth'] = 1.0
    save(moved/'request.json',request); result['request_sha256'] = sha256(moved/'request.json'); save(moved/'result.json',result)
    with pytest.raises(ValueError): bundles.verify(moved)


def test_raw_weight_scale_changes_reject_after_every_target_hash_and_patch_is_rebound(tmp_path):
    a,b,_,out,_ = author(tmp_path,two=False); target,profile = target_from(a,b,tmp_path/'target')
    moved = tmp_path/'transfer'; move(out,target,profile,moved)
    input_a,input_b = moved/'input/character.glb',moved/'input/rig-profile.json'
    rig = RigAsset.load(input_a); doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    for key in ('WEIGHTS_0','WEIGHTS_1'):
        number = doc['meshes'][0]['primitives'][0]['attributes'][key]
        item = doc['accessors'][number]; view = doc['bufferViews'][item['bufferView']]
        values = np.frombuffer(binary,dtype='<f4',count=item['count']*4,offset=view.get('byteOffset',0))
        values *= np.float32(1.0001)
    write_glb(input_a,doc,binary)
    value = read(input_b); value['character_sha256'] = sha256(input_a); save(input_b,value)
    source = bundles.source_binding(input_a,input_b); material = bundles.surface(input_a,input_b,source)
    # A normalization-only comparison would miss this actual raw payload change.
    np.testing.assert_array_equal(material.rig.primitives[0]['weights'][:3],rig.primitives[0]['weights'][:3])
    selection = read(moved/'input/selection.json'); selection['source'] = source; save(moved/'input/selection.json',selection)
    request,result = read(moved/'request.json'),read(moved/'result.json')
    request['source'] = source; request['input_sha256'] = {n:sha256(moved/'input'/n) for n in request['input_sha256']}
    save(moved/'identity.json',descriptor(material)); request['identity_sha256'] = sha256(moved/'identity.json')
    result['patches'] = [bundles.patch_record(name,patch,moved) for name,patch in bundles.selections(selection,material)]
    proof = read(moved/'transfer.json'); proof['target'] = source; proof['identity_sha256'] = digest(descriptor(material))
    save(moved/'transfer.json',proof); request['transfer_sha256'] = sha256(moved/'transfer.json')
    save(moved/'request.json',request); result['request_sha256'] = sha256(moved/'request.json'); save(moved/'result.json',result)
    with pytest.raises(ValueError,match='raw mesh/skinning'): bundles.verify(moved)


def test_source_change_during_authoring_preserves_failed_partial_bundle(tmp_path,monkeypatch):
    a,b,selection,_,_ = author(tmp_path); original = bundles.patch_record
    def changed(*args):
        result = original(*args); a.write_bytes(b'changed original character'); return result
    monkeypatch.setattr(bundles,'patch_record',changed)
    out = tmp_path/'failed'
    with pytest.raises(ValueError,match='Original authoring'): bundles.create(a,b,selection,out)
    assert read(out/'pipeline.json')['status'] == 'failed'
    assert (out/'request.json').exists() and not (out/'result.json').exists()


@pytest.mark.parametrize('field',['character_sha256','profile_sha256'])
def test_transfer_requires_explicit_matching_target_hashes(tmp_path,field):
    a,b,_,out,_ = author(tmp_path); target,profile = target_from(a,b,tmp_path/'target')
    hashes = dict(character_sha256=sha256(target),profile_sha256=sha256(profile)); hashes[field] = '0'*64
    with pytest.raises(ValueError,match='source changed'): bundles.transfer(out,target,profile,tmp_path/'rejected',**hashes)
    assert not (tmp_path/'rejected').exists()


def test_explicit_file_budget_rejects_before_decoding_and_output_creation(tmp_path,monkeypatch):
    a,b,selection,_,_ = author(tmp_path)
    monkeypatch.setattr(bundles,'MAXIMUM_ASSET_BYTES',10)
    monkeypatch.setattr(bundles,'MaterialSurface',lambda *args,**kwargs:pytest.fail('Oversized asset must reject before decode'))
    with pytest.raises(ValueError,match='Bounded regular'): bundles.create(a,b,selection,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()
