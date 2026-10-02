"""Independent matrix/preview serialization and joint-population repair checks."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_roundtrip import preview_values,SupportRoundtripProblem
from native_support_feasibility import constraint_model,signed_constraints
from native_support_orientation import SupportOrientationProblem
from native_support_spec import validate
from native_support_clock import NativeSupportSampler
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels
from rig_asset import RigAsset
from strep import read,save,sha256
from test_native_support import fixture


def test_changed_quaternions_match_independent_stored_matrix_reconstruction():
    q=Rotation.from_euler('xyz',[[.1,.2,.3],[.4,.5,.6],[.7,.8,.9]]).as_quat().astype(np.float32)
    changed=q.copy();changed[1]=Rotation.from_euler('xyz',[.40001,.4999,.6002]).as_quat()
    predicted=preview_values({3:changed},{3:(None,None,q)})[3]
    stored_matrix=Rotation.from_quat(changed[1]).as_matrix().astype(np.float32)
    expected=Rotation.from_matrix(stored_matrix).as_quat().astype(np.float32)
    if expected@predicted[0]<0:expected=-expected
    np.testing.assert_array_equal(predicted[1],expected)
    np.testing.assert_array_equal(predicted[[0,2]],q[[0,2]])


@pytest.mark.parametrize('fault',['shape','nonfinite','zero'])
def test_invalid_rotation_keys_rejected(fault):
    q=np.tile([0.,0.,0.,1.],(3,1));changed=q.copy()
    if fault=='shape':changed=changed[:,:3]
    if fault=='nonfinite':changed[1,0]=float('nan')
    if fault=='zero':changed[1]=0
    with pytest.raises(ValueError):preview_values({3:changed},{3:(None,None,q)})


def test_raw_and_preview_proxy_rows_match_separate_independent_decoders(tmp_path):
    source,rig,reader,spec=fixture(tmp_path)
    _,rows=validate(spec,rig,reader,sha256(source))
    p=SupportRoundtripProblem(rig,reader,rows)
    ordinary=SupportOrientationProblem(rig,reader,rows)
    np.testing.assert_array_equal(p.lower,ordinary.lower)
    np.testing.assert_array_equal(p.upper,ordinary.upper)
    x=p.initial.copy()
    for d in p.data:x[d['orientation_ids']]=[.001,-.002,.003]
    values,_=p.rotations(x);raw=tmp_path/'raw.glb'
    export_rotations(rig.document,rig.binary,values,raw)
    actual=RigAsset.load(raw);raw_q=rotation_channels(actual.document,actual.binary)
    forwarded={}
    for node in p.nodes:
        original=p.channels[node][2];stored=raw_q[node][2]
        changed=np.any(stored!=original,axis=1)
        local=Rotation.from_quat(original).as_matrix().astype(np.float32)
        local[changed]=Rotation.from_quat(stored[changed]).as_matrix()
        rebuilt=Rotation.from_matrix(local).as_quat()
        for frame in range(1,len(rebuilt)):
            if rebuilt[frame]@rebuilt[frame-1]<0:rebuilt[frame]*=-1
        forwarded[node]=rebuilt
    preview=tmp_path/'preview.glb';export_rotations(rig.document,rig.binary,forwarded,preview)
    population=[]
    for path in (raw,preview):
        asset=RigAsset.load(path);decoder=NativeSupportSampler(asset.document,asset.binary,0)
        world=np.array([decoder.sample(float(t)) for t in p.times])
        q=rotation_channels(asset.document,asset.binary)
        population.append(signed_constraints(p,{n:q[n][2] for n in p.nodes},world))
    model=constraint_model(p,x,quantized=True)
    np.testing.assert_allclose(model,np.r_[tuple(population)],atol=2e-9,rtol=0)
    graph=p.sparsity();single=ordinary.sparsity()
    assert graph.shape==(2*single.shape[0],single.shape[1])
    assert (graph[:single.shape[0]]!=single).nnz==0
    assert (graph[single.shape[0]:]!=single).nnz==0


@pytest.mark.parametrize('mode',[True,1,'yes',None])
def test_roundtrip_mode_needs_explicit_warm_orientation_job(mode):
    from native_support_job import run
    with pytest.raises(ValueError,match='[Rr]epair'):run(None,None,None,repair_native_roundtrip=mode)


def test_roundtrip_job_keeps_controls_boxes_and_archives_both_decoded_populations(tmp_path,monkeypatch):
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec=fixture(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    flags=dict(joint_rates=True,joint_swivel=True,joint_foot_orientation=True)
    warm=tmp_path/'reports/warm';original=job.run(source,draft,warm,**flags,joint_evaluations=1)
    frozen={str(p):sha256(p) for p in warm.rglob('*') if p.is_file()}
    output=tmp_path/'reports/roundtrip'
    result=job.run(source,draft,output,**flags,repair_from=warm,repair_native_roundtrip=True,
                   repair_coordinates=True,repair_iterations=1,repair_trust=2e-7)
    request=read(output/'request.json')
    assert request['proposal_method']=='serialized_native_support_roundtrip_repair'
    assert request['repair_native_roundtrip'] and request['repair_quantized_differences']
    assert request['spec']==spec and request['rate_tolerance']==1e-5
    assert sha256(output/'implementation/native_support_roundtrip.py')==request['implementation']['native_support_roundtrip.py']
    for t in result['trials']:
        proposal=t['proposal'][0]
        assert proposal['probes'][0]['sha256']==original['trials'][t['trial']]['sha256']
        for probe in proposal['probes']:
            assert sha256(output/probe['file'])==probe['sha256']
            assert sha256(output/probe['preview_file'])==probe['preview_sha256']
        assert proposal['probes'][-1]['label']=='final'
        assert proposal['native_roundtrip_constraints_pass']==proposal['probes'][-1]['preview_constraints_pass']
        if t['selection_gates_pass']:assert proposal['native_roundtrip_constraints_pass']
        old=read(warm/f"trial-{t['trial']}.controls.json");new=read(output/proposal['controls_file'])
        for key in ('lower','upper','intervals'):assert old[key]==new[key]
    assert all(sha256(p)==digest for p,digest in frozen.items())
    assert not result['quality_approved']
