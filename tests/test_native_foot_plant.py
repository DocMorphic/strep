"""Planar correction geometry, independent failure gates and immutable inputs."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from native_foot_plant import envelope,policy_rows,propose,audit,run,preserve
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb,accessor
from strep import save,read,sha256


def setup(tmp_path,moving=True):
    source,rig,reader,spec=fixture(tmp_path,plane=.188)
    if moving:
        doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
        animation=doc['animations'][0];sampler=animation['samplers'][1]
        positions=accessor(doc,data,sampler['output']).copy()
        positions[:,0]=np.linspace(0,.006,len(positions))
        sampler['output']=append_accessor(doc,data,positions,'VEC3');write_glb(source,doc,data)
        rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0);spec['glb_sha256']=sha256(source)
    draft=tmp_path/'draft.json';save(draft,spec)
    policy=dict(schema='strep-native-foot-plant-v1',source_sha256=sha256(source),base_sha256=sha256(source),
        draft_sha256=sha256(draft),supports=[dict(id='left-stance',maximum_patch_anchor_error_m=.00002,maximum_patch_speed_m_s=.0001)])
    _,rows=validate(spec,rig,reader,sha256(source));limits=policy_rows(policy,source,source,draft,rows)
    return source,rig,reader,spec,draft,policy,rows,limits


def test_planar_ik_reduces_drift_without_changing_root_or_native_clocks(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    baseline=audit(source,source,spec,limits);path=tmp_path/'proposal.glb'
    propose(rig,reader,rig,reader,rows,path)
    candidate=RigAsset.load(path);new=NativeSupportSampler(candidate.document,candidate.binary,0)
    preserve(reader,new,rows)
    result=audit(source,path,spec,limits)
    assert baseline['contacts'][0]['maximum_patch_anchor_error_m']>.001
    assert result['contacts'][0]['maximum_patch_anchor_error_m']<.00002
    assert result['contact_samples_pass']
    assert not result['support_screens']['source_rates_pass'] and not result['passed']
    # A stationary root-relative source has zero angular caps. Real IK introduces
    # leg angular motion; reduced contact drift must not override that failure.
    for t in (0.,.15,.2,1.8,1.9,2.):np.testing.assert_array_equal(reader.sample(t),new.sample(t))
    for t in (.617,.853725,1.,1.45):np.testing.assert_array_equal(reader.sample(t)[[0,5,6]],new.sample(t)[[0,5,6]])
    original=reader.sample(1);changed=new.sample(1)
    np.testing.assert_allclose(changed[3,:3,:3],original[3,:3,:3],atol=2e-7,rtol=0)
    assert abs(changed[3,1,3]-original[3,1,3])<2e-8


@pytest.mark.parametrize('fault',['source','base','draft','id','duplicate','boolean','nonfinite','unknown'])
def test_bound_policy_rejects_mismatched_or_unbounded_targets(tmp_path,fault):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    if fault in ('source','base','draft'):policy[fault+'_sha256']='0'*64
    if fault=='id':policy['supports'][0]['id']='different'
    if fault=='duplicate':policy['supports']*=2
    if fault=='boolean':policy['supports'][0]['maximum_patch_anchor_error_m']=True
    if fault=='nonfinite':policy['supports'][0]['maximum_patch_speed_m_s']=float('nan')
    if fault=='unknown':policy['hidden_relaxation']=True
    with pytest.raises(ValueError):policy_rows(policy,source,source,draft,rows)


def test_failed_rate_gates_keep_exact_input_and_rejected_proposal(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    frozen={str(p):sha256(p) for p in (source,draft,policy_path)}
    out=tmp_path/'fit';result=run(source,source,draft,policy_path,out)
    assert result['retained_input'] and result['proposal']['contact_samples_pass']
    assert result['proposal']['support_screens']['support_samples_pass']
    assert not result['proposal']['support_screens']['source_rates_pass']
    assert sha256(out/'candidate.glb')==sha256(source)
    assert (out/'proposal.glb').is_file() and not result['native_npz_conversion_verified']
    assert read(out/'pipeline.json')['status']=='complete'
    assert all(sha256(p)==d for p,d in frozen.items())
    with pytest.raises(ValueError,match='fresh'):run(source,source,draft,policy_path,out)


def test_already_satisfied_input_is_retained_without_improvement_claim(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path,moving=False)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    result=run(source,source,draft,policy_path,tmp_path/'fit')
    assert result['baseline']['passed'] and result['retained_input']
    assert result['retention_reason']=='input_already_satisfies_all_gates'
    assert not result['quality_approved'] and not result['release_approved']


def test_actual_toy_correction_can_pass_every_gate_without_mocked_acceptance(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path,moving=False)
    doc=copy.deepcopy(rig.document);data=bytearray(rig.binary);animation=doc['animations'][0]
    clock=rows[0]['clock'];theta=.008*(-1.)**np.arange(len(clock))
    for channel in animation['channels'][:3]:
        node=channel['target']['node'];factor=1 if node==1 else -.875 if node==3 else 0
        q=Rotation.from_rotvec(np.c_[theta*factor,np.zeros((len(theta),2))]).as_quat()
        sampler=dict(animation['samplers'][0]);sampler['output']=append_accessor(doc,data,q,'VEC4')
        channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
    write_glb(source,doc,data);spec['glb_sha256']=sha256(source);save(draft,spec)
    policy.update(source_sha256=sha256(source),base_sha256=sha256(source),draft_sha256=sha256(draft))
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    result=run(source,source,draft,policy_path,tmp_path/'fit')
    assert not result['retained_input'] and result['selected']['passed']
    assert result['proposal']['support_screens']['source_rate_failed_rows']==[0,0,0,0]
    assert result['baseline']['contacts'][0]['maximum_patch_anchor_error_m']>.015
    assert result['selected']['contacts'][0]['maximum_patch_anchor_error_m']<1e-7
    assert sha256(tmp_path/'fit/candidate.glb')==sha256(tmp_path/'fit/proposal.glb')
    assert not result['quality_approved'] and not result['native_npz_conversion_verified']


def test_stationary_but_shifted_patch_cannot_hide_target_error_as_zero_drift(tmp_path):
    from native_leg_floor import export_rotations
    from paired_temporal_neighbor import rotation_channels
    from two_bone_waypoint import reach
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path,moving=False)
    channels=rotation_channels(rig.document,rig.binary);row=rows[0]
    values={node:channels[node][2].copy() for node in row['chain']}
    for key in range(2,9):
        world=reader.sample(float(row['clock'][key]))
        _,local=reach(world,rig.parents,*row['chain'],world[3,:3,3]+[.002,0,0])
        for node,q in zip(row['chain'],Rotation.from_matrix(local[row['chain'],:3,:3]).as_quat()):values[node][key]=q
    path=tmp_path/'shifted.glb';export_rotations(rig.document,rig.binary,values,path)
    result=audit(source,path,spec,limits)
    assert result['diagnostics']['supports'][0]['candidate']['maximum_patch_vertex_tangential_drift_m']<1e-7
    assert result['contacts'][0]['maximum_patch_anchor_error_m']>.0019
    assert not result['contact_samples_pass']


def test_plane_envelope_has_frozen_ends_and_flat_stance():
    t=np.array([-.1,0,.1,.5,.75,1,1.25,1.5,1.9,2,2.1])
    w=envelope(t,[0,2],[.5,1.5])
    np.testing.assert_array_equal(w[[0,1,-2,-1]],[0,0,0,0])
    np.testing.assert_array_equal(w[3:8],np.ones(5))
    h=1e-4
    for boundary in (0,.5,1.5,2):
        q=envelope(np.array([boundary-h,boundary,boundary+h]),[0,2],[.5,1.5])
        assert abs((q[2]-q[0])/(2*h))<1e-5
        assert abs((q[2]-2*q[1]+q[0])/(h*h))<.009
    with pytest.raises(ValueError):envelope([0,1],[0,2],[1.5,.5])


def test_changed_triangle_payload_is_rejected_even_with_same_accessor_identity(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    index=doc['meshes'][0]['primitives'][0]['indices'];acc=doc['accessors'][index];view=doc['bufferViews'][acc['bufferView']]
    start=view.get('byteOffset',0)+acc.get('byteOffset',0)
    data[start:start+2]=np.array([2],dtype='<u2').tobytes()
    changed=tmp_path/'tampered.glb';write_glb(changed,doc,data)
    with pytest.raises(ValueError,match='mesh payload'):audit(source,changed,spec,limits)


def test_tilted_plane_ik_changes_only_tangential_ankle_position(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    doc=copy.deepcopy(rig.document);data=bytearray(rig.binary);sampler=doc['animations'][0]['samplers'][1]
    positions=accessor(doc,data,sampler['output']).copy();positions[:,1]=1.2
    sampler['output']=append_accessor(doc,data,positions,'VEC3');write_glb(source,doc,data)
    rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    row=rows[0];row=dict(row,up=np.array([0.,2**-.5,2**-.5]))
    path=tmp_path/'tilted.glb';propose(rig,reader,rig,reader,[row],path)
    new_rig=RigAsset.load(path);new=NativeSupportSampler(new_rig.document,new_rig.binary,0)
    for t in row['clock'][2:9]:
        a,b=reader.sample(float(t)),new.sample(float(t))
        delta=b[3,:3,3]-a[3,:3,3]
        assert abs(delta@row['up'])<3e-8
        np.testing.assert_allclose(a[3,:3,:3],b[3,:3,:3],atol=2e-7,rtol=0)


def test_unreachable_tilted_correction_is_rejected_without_clamping(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    row=dict(rows[0],up=np.array([0.,2**-.5,2**-.5]))
    path=tmp_path/'unreachable.glb'
    with pytest.raises(ValueError,match='outside two-bone reach'):propose(rig,reader,rig,reader,[row],path)
    assert not path.exists()
