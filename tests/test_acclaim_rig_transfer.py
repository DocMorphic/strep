"""Artificial capture and independently authored rig; no downloaded payloads."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_rig_transfer import fixture
from acclaim_motion import parse_asf,read_motion
from retarget_rig import ROLE_PARENTS,PRIMARY,resolve_profile
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import save,read,sha256
import acclaim_rig_transfer as bridge


def capture(tmp_path):
    character,target_profile=fixture(tmp_path/'target','target',axes=19,helpers=True,reverse=True)
    rig=RigAsset.load(character);mapping,_=resolve_profile(rig,read(target_profile))
    positions={role:rig.reference[node,:3,3] for role,node in mapping.items()};hip=positions['Hips']
    names={r:'cap_'+r for r in mapping};names['Hips']='root'
    endpoint={}
    for r in mapping:endpoint[r]=positions.get(PRIMARY.get(r),positions[r]) if r!='Hips' else hip
    rows=[':version 1.10',':name artificial',':units','mass 1','length 1','angle deg',
          ':root','order TX TY TZ RX RY RZ','axis XYZ','position 0 0 0','orientation 0 0 0',':bonedata']
    hierarchy={};id=0
    def bone(name,vector,rotations):
        nonlocal id;id+=1;length=np.linalg.norm(vector);direction=vector/length if length>1e-12 else np.zeros(3)
        rows.extend(['begin',f'id {id}',f'name {name}','direction '+' '.join(map(str,direction)),f'length {length}','axis 0 0 0 XYZ'])
        if rotations:rows.append('dof rx ry rz')
        rows.append('end')
    for role,parent in ROLE_PARENTS.items():
        if parent is None:continue
        helper='offset_'+role;bone(helper,positions[role]-endpoint[parent],False)
        bone(names[role],endpoint[role]-positions[role],True)
        hierarchy.setdefault(names[parent],[]).append(helper);hierarchy[helper]=[names[role]]
    # Independent hand orientation segment after the wrist-origin role.
    bone('hand_orientation',np.zeros(3),True);hierarchy[names['LeftHand']]=['hand_orientation']
    rows.extend([':hierarchy','begin',*[p+' '+' '.join(c) for p,c in hierarchy.items()],'end'])
    asf=tmp_path/'capture.asf';asf.write_text('\n'.join(rows)+'\n')
    amc_rows=[':FULLY-SPECIFIED',':DEGREES']
    for frame in range(1,4):
        amc_rows.extend([str(frame),'root '+' '.join(map(str,np.r_[hip+[(frame-1)*.02,0,0],[0,0,0]]))])
        for role in list(mapping)[1:]:
            values=[7*(frame-1),0,0] if role=='Chest' else [0,0,0]
            amc_rows.append(names[role]+' '+' '.join(map(str,values)))
        amc_rows.append('hand_orientation '+f'0 {11*(frame-1)} 0')
    amc=tmp_path/'capture.amc';amc.write_text('\n'.join(amc_rows)+'\n')
    source_profile=dict(schema='strep-acclaim-humanoid-profile-v1',asf_sha256=sha256(asf),reference_pose='zero_amc_rotations',
        mapping={r:dict(position_bone=n,rotation_bone=n) for r,n in names.items()})
    source_profile['mapping']['LeftHand']['rotation_bone']='hand_orientation'
    source_path=tmp_path/'source-profile.json';save(source_path,source_profile)
    return asf,amc,source_path,character,target_profile


def test_real_export_retains_clock_payload_root_and_every_source_frame(tmp_path):
    args=capture(tmp_path);pins={str(p):sha256(p) for p in args};out=tmp_path/'out'
    r=bridge.export(*args,out,fps=120,metres_per_unit=1)
    assert r['status']=='complete' and r['frames']==3 and r['output_animation_index']==1
    assert r['original_target_payload_preserved'] and r['all_source_frames_retained']
    assert r['roundtrip_max_vertex_error_m']<1e-5 and r['automatic_floor_lift_m']==0
    assert not any(r[k] for k in ('quality_approved','contact_verified','training_admitted','engine_import_verified','release_approved'))
    original=RigAsset.load(args[3]);candidate=RigAsset.load(out/'character.glb')
    np.testing.assert_allclose(candidate.reference,original.reference,atol=1e-12,rtol=0)
    sampler=NativeSupportSampler(candidate.document,candidate.binary,1)
    with np.load(out/'target-transforms.npz',allow_pickle=False) as archive:
        np.testing.assert_array_equal(archive['source_frame_ids'],[1,2,3])
        np.testing.assert_array_equal(archive['times_s'],np.arange(3)/120)
        np.testing.assert_allclose(sampler.sample(0),original.reference,atol=1e-6)
        for i,t in enumerate(archive['encoded_times_s']):
            np.testing.assert_allclose(sampler.sample(float(t)),archive['global_matrices'][i],atol=1e-6)
        hips=r['target_mapping']['Hips'];root=read(out/'root-motion.json')
        np.testing.assert_allclose(archive['global_matrices'][:,hips,:3,3],root['positions_m'])
    assert read(out/'contacts.json')['intervals']==[] and not read(out/'contacts.json')['contact_verified']
    assert all(sha256(p)==h for p,h in pins.items())
    with pytest.raises(ValueError,match='Fresh'):bridge.export(*args,out,fps=120,metres_per_unit=1)


def test_position_and_orientation_segments_remain_distinct(tmp_path):
    asf,amc,profile,*_=capture(tmp_path);s,m,_=read_motion(asf,amc,fps=120,metres_per_unit=1)
    reference,mapped,binding=bridge.mapped_motion(s,m,read(profile),sha256(asf))
    i=reference.bone_order_names.index('LeftHand');lookup={n:i for i,n in enumerate(s['names'])}
    np.testing.assert_array_equal(mapped['posed_joints'][:,i],m['positions_m'][:,lookup['cap_LeftHand']])
    np.testing.assert_array_equal(mapped['global_rot_mats'][:,i],m['rotations'][:,lookup['hand_orientation']])
    assert not np.allclose(m['rotations'][-1,lookup['cap_LeftHand']],mapped['global_rot_mats'][-1,i])
    assert binding['position_segments']['LeftHand']!=binding['rotation_segments']['LeftHand']


@pytest.mark.parametrize('fault',['schema','hash','reference','missing','extra','bad-segment','duplicate-position',
    'duplicate-orientation','root','hierarchy','orientation-ancestor','orientation-other-branch','field','mapping-type'])
def test_source_admission_rejects_ambiguous_or_incompatible_roles(tmp_path,fault):
    asf,_,path,*_=capture(tmp_path);profile=read(path);s=parse_asf(asf.read_text(),metres_per_unit=1)
    if fault=='schema':profile['schema']='wrong'
    if fault=='hash':profile['asf_sha256']='a'*64
    if fault=='reference':profile['reference_pose']='first_capture_frame'
    if fault=='missing':del profile['mapping']['Head']
    if fault=='extra':profile['mapping']['Unknown']=profile['mapping']['Head']
    if fault=='bad-segment':profile['mapping']['Head']['position_bone']='missing'
    if fault=='duplicate-position':profile['mapping']['Head']['position_bone']='cap_Neck1'
    if fault=='duplicate-orientation':profile['mapping']['Head']['rotation_bone']='cap_Neck1'
    if fault=='root':profile['mapping']['Hips']['rotation_bone']='offset_Spine2'
    if fault=='hierarchy':profile['mapping']['LeftHand']['position_bone']='offset_RightHand'
    if fault=='orientation-ancestor':profile['mapping']['LeftHand']['rotation_bone']='offset_LeftForeArm'
    if fault=='orientation-other-branch':profile['mapping']['LeftHand']['rotation_bone']='offset_RightHand'
    if fault=='field':profile['mapping']['Head']['guessed']=True
    if fault=='mapping-type':profile['mapping']=[]
    with pytest.raises(ValueError):bridge.resolve_source(s,profile,sha256(asf))


def test_target_hash_rejects_without_overwriting_originals(tmp_path):
    args=capture(tmp_path);profile=read(args[-1]);profile['character_sha256']='a'*64;save(args[-1],profile)
    with pytest.raises(ValueError,match='checksum'):bridge.export(*args,tmp_path/'out',fps=120,metres_per_unit=1)
    assert not (tmp_path/'out').exists()


def test_failed_roundtrip_is_terminal_and_preserved(tmp_path,monkeypatch):
    args=capture(tmp_path);sample=bridge.sample_animation
    def corrupt(*a,**kw):
        result=sample(*a,**kw);result[0,0,3]+=.01;return result
    monkeypatch.setattr(bridge,'sample_animation',corrupt);out=tmp_path/'out'
    with pytest.raises(ValueError,match='roundtrip failed'):bridge.export(*args,out,fps=120,metres_per_unit=1)
    assert read(out/'report.json')['status']=='failed' and read(out/'pipeline.json')['status']=='failed'
    assert (out/'character.glb').is_file() and not read(out/'report.json')['quality_approved']
