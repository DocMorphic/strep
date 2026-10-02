"""Loaded multi-primitive GLBs through native fitting, preserving all payloads."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region,export_rotations
from native_support_path import propose
from native_support_orientation import SupportOrientationProblem
from strep import sha256,save,read


def multisurface(tmp_path):
    _,rig,_,spec=fixture(tmp_path)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    def unsigned(values):
        a=np.asarray(values,dtype='<u2')
        while len(binary)%4:binary.append(0)
        view=len(doc['bufferViews']);doc['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=a.nbytes))
        binary.extend(a.tobytes());acc=len(doc['accessors'])
        doc['accessors'].append(dict(bufferView=view,componentType=5123,count=len(a),type='VEC4'))
        return acc
    original=doc['meshes'][0]['primitives'][0]
    for positions,joints,weights,eight in (
        ([[-.22,.18,-.02],[-.18,.18,-.02],[-.2,.18,.1]],[[3,4,0,0]]*3,[[.7,.3,0,0]]*3,True),
        ([[.4,1.3,0],[.6,1.3,0],[.5,1.4,0]],[[5,0,0,0]]*3,[[1,0,0,0]]*3,False)):
        attrs=dict(POSITION=append_accessor(doc,binary,positions,'VEC3'),
            JOINTS_0=unsigned(joints),WEIGHTS_0=append_accessor(doc,binary,weights,'VEC4'))
        if eight:
            attrs.update(JOINTS_1=unsigned([[0,0,0,0]]*3),WEIGHTS_1=append_accessor(doc,binary,np.zeros((3,4)),'VEC4'))
        doc['meshes'][0]['primitives'].append(dict(attributes=attrs,indices=original['indices']))
    source=tmp_path/'multisurface.glb';write_glb(source,doc,binary)
    rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    spec['glb_sha256']=sha256(source)
    _,rows=validate(spec,rig,reader,sha256(source))
    return source,rig,reader,spec,rows


def preserved(source,exported,reader,current):
    assert exported.document['meshes']==source.document['meshes']
    assert exported.document['skins']==source.document['skins']
    assert exported.binary[:len(source.binary)]==source.binary
    assert len(exported.primitives)==3
    for a,b in zip(reader.channels,current.channels):
        assert a[:2]==b[:2] and a[4]==b[4]
        np.testing.assert_array_equal(a[2],b[2])
        if a[1]!='rotation':np.testing.assert_array_equal(a[3],b[3])
    for t in (0.,.173,1.831,2.):np.testing.assert_array_equal(current.sample(t),reader.sample(t))
    for t in (.85,1.,1.173):np.testing.assert_array_equal(current.sample(t)[[0,5,6]],reader.sample(t)[[0,5,6]])


def test_loaded_full_surface_smoothing_uses_lower_material_and_preserves_glb(tmp_path):
    source,rig,reader,spec,rows=multisurface(tmp_path);before=sha256(source)
    skin=NativeSupportSkin(rig);np.testing.assert_array_equal(foot_region(skin,rig.parents,3),np.arange(6))
    output=tmp_path/'smooth.glb';propose(rig,reader,rows,output)
    exported=RigAsset.load(output);current=NativeSupportSampler(exported.document,exported.binary,0)
    preserved(rig,exported,reader,current);assert sha256(source)==before
    heights=np.array([exported.vertices(current.sample(float(t)))[:6,1].min()-.2 for t in np.linspace(.8,1.2,49)])
    assert heights.min()>=-1e-8 and heights.max()<=.005


def test_loaded_full_surface_orientation_proxy_matches_serialized_geometry(tmp_path):
    _,rig,reader,_,rows=multisurface(tmp_path)
    problem=SupportOrientationProblem(rig,reader,rows)
    assert problem.data[0]['projection'].matrix.shape[1]==6
    values,_=problem.rotations(problem.initial);path=tmp_path/'initial.glb'
    export_rotations(rig.document,rig.binary,values,path)
    out=RigAsset.load(path);current=NativeSupportSampler(out.document,out.binary,0)
    preserved(rig,out,reader,current)
    proxy=problem.world({n:q.astype(np.float32).astype(float) for n,q in values.items()})
    decoded=np.array([current.sample(float(t)) for t in problem.times])
    np.testing.assert_allclose(proxy,decoded,atol=2e-14,rtol=0)
    for w in decoded[::13]:
        ids=np.arange(9)
        np.testing.assert_allclose(NativeSupportSkin(out).evaluate(w[None],np.zeros(9,int),ids),out.vertices(w),atol=5e-15,rtol=0)


@pytest.mark.parametrize('joint',[False,True])
def test_real_four_trial_job_archives_full_skin_and_keeps_rate_gates(tmp_path,monkeypatch,joint):
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec,_=multisurface(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    output=tmp_path/'reports'/'fit'
    job.run(source,draft,output,joint_rates=joint,joint_swivel=joint,joint_foot_orientation=joint,joint_evaluations=1 if joint else 80)
    q=read(output/'request.json');r=read(output/'result.json')
    assert q['rate_tolerance']==1e-5 and q['absolute_peak_tolerance']==1e-7
    assert sha256(output/'implementation'/'native_support_skin.py')==q['implementation']['native_support_skin.py']
    assert len(r['trials'])==4 and all(t['status']=='complete' for t in r['trials'])
    assert not r['quality_approved']
    for t in r['trials']:
        out=RigAsset.load(output/f"trial-{t['trial']}.glb")
        preserved(rig,out,reader,NativeSupportSampler(out.document,out.binary,0))
        assert t['selection_gates_pass']==(t['source_rates_pass'] and t['support_samples_pass'])
    assert r['retained_input']==(r['selected_trial'] is None)
    assert sha256(output/'candidate.glb')==r['candidate_sha256']


def test_multisurface_warm_strict_repair_preserves_independent_selection_gate(tmp_path,monkeypatch):
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    source,rig,reader,spec,_=multisurface(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    warm=tmp_path/'reports'/'warm'
    job.run(source,draft,warm,joint_rates=True,joint_swivel=True,joint_foot_orientation=True,joint_evaluations=1)
    output=tmp_path/'reports'/'strict'
    job.run(source,draft,output,joint_rates=True,joint_swivel=True,joint_foot_orientation=True,
        repair_from=warm,repair_iterations=1,repair_trust=2e-7,repair_quantized=True,repair_strict_peaks=True)
    r=read(output/'result.json');q=read(output/'request.json')
    assert q['repair_strict_peaks'] and q['rate_tolerance']==1e-5 and q['absolute_peak_tolerance']==1e-7
    assert all(t['status']=='complete' for t in r['trials'])
    for t in r['trials']:
        assert t['selection_gates_pass']==(t['source_rates_pass'] and t['support_samples_pass'] and t['absolute_peak_comparison']['passed'])
        out=RigAsset.load(output/f"trial-{t['trial']}.glb")
        preserved(rig,out,reader,NativeSupportSampler(out.document,out.binary,0))
    assert not r['quality_approved'] and sha256(output/'candidate.glb')==r['candidate_sha256']
