"""Independent decoding and dependency coverage for joint planted geometry."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_foot_plant import setup
from native_joint_plant import JointPlantProblem
from native_joint_plant_job import run,restore
from native_foot_plant import propose
from native_support_clock import NativeSupportSampler
from native_support_feasibility import colored_jacobian,constraint_model
from native_support_roundtrip import preview_values
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels
from sampled_motion_caps import features,measures
from rig_asset import RigAsset
from strep import save,read,sha256
from gltf_tools import append_accessor,write_glb


def problem_fixture(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    return JointPlantProblem(rig,reader,rows,limits,reader),(source,rig,reader,spec,draft,policy,rows,limits)


def test_raw_and_preview_models_match_independent_export_and_scalar_decoders(tmp_path):
    p,data=problem_fixture(tmp_path);source,rig,reader,spec,draft,policy,rows,limits=data
    x=p.initial.copy();x[p.data[0]['ids'][2]]=[[.0001,.0002,-.0003],[.0002,-.0001,.0001],[.0001,.0002,.0001]]
    values,_=p.rotations(x);raw=tmp_path/'raw.glb';export_rotations(rig.document,rig.binary,values,raw)
    actual=RigAsset.load(raw);channels=rotation_channels(actual.document,actual.binary)
    preview=tmp_path/'preview.glb';export_rotations(rig.document,rig.binary,
        preview_values({n:channels[n][2] for n in p.nodes},p.channels),preview)
    population=[]
    for path in (raw,preview):
        asset=RigAsset.load(path);decoder=NativeSupportSampler(asset.document,asset.binary,0)
        world=np.array([decoder.sample(float(t)) for t in p.times]);q=rotation_channels(asset.document,asset.binary)
        current={n:q[n][2] for n in p.nodes}
        # Tiny near-identity SLERP dot/norm reductions differ between scalar
        # and batch NumPy paths. Final acceptance always uses scalar decoding.
        np.testing.assert_allclose(p.world(current),world,atol=2e-12,rtol=0)
        population.append(p.constraints(current,world))
        full=measures(features(world[p.rate_ids],rig.joints),p.caps.dt)
        subset=measures(features(world[p.rate_ids],np.asarray(rig.joints)[p.columns]),p.caps.dt)
        for a,b in zip(full,subset):np.testing.assert_array_equal(a[:,p.columns],b)
    np.testing.assert_allclose(p.model(x,native_roundtrip=True),np.r_[tuple(population)],atol=2e-8,rtol=0)
    assert p.sparsity(native_roundtrip=True).shape==(2*len(population[0]),len(x))


def test_graph_covers_every_observed_direct_key_dependency(tmp_path):
    p,_=problem_fixture(tmp_path);pattern=p.sparsity();x=p.initial.copy();before=p.model(x)
    for col in range(len(x)):
        z=x.copy();z[col]+=2e-6;difference=p.model(z)-before
        changed=np.flatnonzero(abs(difference)>1e-8)
        assert np.all(pattern[changed,col].toarray().ravel()!=0),col
    function=lambda z:p.model(z,quantized=True)
    grouped=colored_jacobian(function,x,p.lower,p.upper,pattern,step=1e-5).toarray()
    full=np.column_stack([(function(x+np.eye(1,len(x),k=col).ravel()*1e-5)-function(x))/1e-5 for col in range(len(x))])
    np.testing.assert_allclose(grouped,full,atol=1e-7,rtol=0)


def test_component_boxes_include_angle_ball_but_radial_constraints_reject_corners(tmp_path):
    p,_=problem_fixture(tmp_path);x=p.initial.copy();d=p.data[0]
    x[d['ids'][2,2]]=p.upper[d['ids'][2,2]]
    values,_=p.rotations(x);core=p.core_constraints(values,p.world(values))
    angular=core[-3*len(d['clock']):].reshape(-1,3)
    assert angular[d['free'][2],2]>.7
    # Frozen native quaternion signs/keys remain exact, regardless of the
    # excessive interior radial angle. Final gates must reject that angle.
    for node in p.nodes:
        a,b=d['row']['edit_keys'];np.testing.assert_array_equal(values[node][[a,b]],p.channels[node][2][[a,b]])


def test_actual_joint_step_is_independently_decoded_and_retained_on_failed_gates(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    seed=tmp_path/'centering.glb';propose(rig,reader,rig,reader,rows,seed)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    output=tmp_path/'joint';result=run(source,source,draft,policy_path,output,seed=seed,iterations=1,trust=.001)
    assert result['retained_input'] and sha256(output/'candidate.glb')==sha256(source)
    assert result['optimization']['iterations']==1
    for probe in result['probes']:
        assert sha256(output/probe['file'])==probe['sha256']
        assert sha256(output/probe['preview_file'])==probe['preview_sha256']
    assert result['probes'][-1]['label']=='final'
    assert read(output/'request.json')['policy']==policy
    assert read(output/'pipeline.json')['status']=='complete'
    assert not result['quality_approved'] and not result['native_npz_conversion_verified']
    controls=read(output/'controls.json')
    assert all(a<=x<=b for a,x,b in zip(controls['lower'],controls['parameters'],controls['upper']))


@pytest.mark.parametrize('options',[dict(iterations=0),dict(iterations=True),dict(trust=0),dict(trust=float('nan')),dict(native_roundtrip=1),dict(coordinates=1),dict(coordinates=True,trust=.002)])
def test_invalid_search_modes_rejected_before_inputs_or_output(options):
    with pytest.raises(ValueError):run(None,None,None,None,None,**options)


def test_satisfactory_source_stays_exact_and_unapproved(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path,moving=False)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    result=run(source,source,draft,policy_path,tmp_path/'fit',iterations=1)
    assert result['retained_input'] and result['selected']['passed']
    assert result['optimization']['iterations']==0
    assert result['candidate_sha256']==sha256(source)
    assert not result['release_approved']
    # Cache entries bind exact GLB bytes, including the actual decode at start.
    final=result['probes'][-1];start=result['probes'][0]
    assert final['raw_decode_reused_from']==start['file']
    assert final['sha256']==start['sha256']
    assert (tmp_path/'fit'/final['file']).read_bytes()==(tmp_path/'fit'/start['file']).read_bytes()


def test_coordinate_hook_includes_contact_and_preview_populations(tmp_path):
    p,_=problem_fixture(tmp_path)
    for preview in (False,True):
        p.native_roundtrip=preview
        actual=constraint_model(p,p.initial,quantized=True)
        np.testing.assert_array_equal(actual,p.model(p.initial,quantized=True,native_roundtrip=preview))
        assert p.sparsity().shape==(len(actual),len(p.initial))


def test_coordinate_search_uses_real_serialized_joint_contact_gates(tmp_path):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path)
    seed=tmp_path/'centering.glb';propose(rig,reader,rig,reader,rows,seed)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    output=tmp_path/'coordinate'
    result=run(source,source,draft,policy_path,output,seed=seed,iterations=1,trust=2e-7,coordinates=True)
    assert result['optimization']['method']=='quantized_coordinate_search'
    assert result['optimization']['numerical_screens']>0
    assert result['optimization']['iterations']==1
    assert result['retained_input'] and result['candidate_sha256']==sha256(source)
    assert read(output/'request.json')['coordinate_search']
    assert not result['proposal']['passed'] and not result['quality_approved']
    assert (output/'implementation/native_support_coordinates.py').is_file()
    hashes={}
    for probe in result['probes']:
        for prefix in ('raw','preview'):
            file=probe['file' if prefix=='raw' else 'preview_file']
            digest=probe['sha256' if prefix=='raw' else 'preview_sha256']
            assert sha256(output/file)==digest
            reused=probe[prefix+'_decode_reused_from']
            if reused is not None:assert hashes[reused]==digest
            hashes[file]=digest
    assert result['optimization']['independently_decoded_unique_glbs']==len(set(hashes.values()))


def test_real_toy_seed_passes_raw_and_preview_constraints_without_mock_gates(tmp_path):
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
    rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    from native_support_spec import validate
    _,rows=validate(spec,rig,reader,sha256(source));seed=tmp_path/'seed.glb';propose(rig,reader,rig,reader,rows,seed)
    result=run(source,source,draft,policy_path,tmp_path/'fit',seed=seed,iterations=1)
    assert not result['retained_input'] and result['selected']['passed'] and result['preview_proposal']['passed']
    assert result['optimization']['final_merit']==[0.,0.]
    assert result['candidate_sha256']==result['proposal_sha256']
    assert not result['quality_approved'] and not result['native_npz_conversion_verified']
