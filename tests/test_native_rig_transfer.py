"""Independent generated rigs only; no model or downloaded character assets."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gltf_tools import append_accessor, write_glb, local_matrix
from native_support_clock import NativeSupportSampler
from retarget_rig import ROLE_PARENTS, OPTIONAL
from rig_asset import RigAsset
from strep import save, read, sha256
import native_rig_transfer as bridge


def fixture(folder, label, *, optional=True, helpers=False, reverse=False, size=1., axes=0., animated=True):
    """Distinct reference axes, hierarchy, counts and order; trivial test skin."""
    folder.mkdir(parents=True, exist_ok=True)
    positions = {'Hips':[0,1,0], 'Spine2':[0,1.18,0], 'Chest':[0,1.4,0], 'Neck1':[0,1.57,0], 'Head':[0,1.74,0],
        'LeftArm':[-.25,1.4,0], 'LeftForeArm':[-.55,1.4,0], 'LeftHand':[-.8,1.4,0],
        'RightArm':[.25,1.4,0], 'RightForeArm':[.55,1.4,0], 'RightHand':[.8,1.4,0],
        'LeftLeg':[-.1,.95,0], 'LeftShin':[-.1,.5,.02], 'LeftFoot':[-.1,.05,0], 'LeftToeBase':[-.1,.05,.15],
        'RightLeg':[.1,.95,0], 'RightShin':[.1,.5,.02], 'RightFoot':[.1,.05,0], 'RightToeBase':[.1,.05,.15]}
    roles = [n for n in ROLE_PARENTS if optional or n not in OPTIONAL]
    parents = {}
    for n in roles:
        p = ROLE_PARENTS[n]
        while p and p not in roles: p = ROLE_PARENTS[p]
        parents[n] = p or 'Wrapper'
    if helpers:
        for side in ('Left', 'Right'):
            helper = side + 'ElbowHelper'; child = side + 'ForeArm'
            positions[helper] = ((np.array(positions[side + 'Arm']) + positions[child]) / 2).tolist()
            parents[helper] = side + 'Arm'; parents[child] = helper
    labels = ['Wrapper'] + list(parents) + ['Mesh']
    if reverse: labels.reverse()
    indices = {n:i for i,n in enumerate(labels)}
    globals_ref = {'Wrapper':np.eye(4), 'Mesh':np.eye(4)}
    globals_ref['Wrapper'][:3,:3] = Rotation.from_euler('yxz',[17,-9,12], degrees=True).as_matrix()
    globals_ref['Wrapper'][:3,3] = [.3,.2,-.4]
    for i,n in enumerate(parents):
        matrix = np.eye(4)
        matrix[:3,:3] = Rotation.from_euler('xyz',[axes + i*3, axes*.5-i*2, axes*.3+i], degrees=True).as_matrix()
        matrix[:3,3] = np.array(positions[n])*size + [1.3,.15,-.7]
        globals_ref[n] = matrix
    nodes = []
    for n in labels:
        local = np.linalg.inv(globals_ref[parents[n]]) @ globals_ref[n] if n in parents else globals_ref[n]
        node = dict(name=label+'_'+n, translation=local[:3,3].tolist(), rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist())
        children = [indices[c] for c,p in parents.items() if p == n]
        if children: node['children'] = children
        if n == 'Mesh': node.update(mesh=0, skin=0)
        nodes.append(node)
    doc = dict(asset=dict(version='2.0', generator='Strep independent CPU software fixture'), nodes=nodes,
        scene=0, scenes=[dict(nodes=[indices['Wrapper'],indices['Mesh']])], buffers=[dict(byteLength=0)],
        bufferViews=[], accessors=[], materials=[dict(name='Generated gray',pbrMetallicRoughness=dict(baseColorFactor=[.5,.5,.5,1],metallicFactor=0,roughnessFactor=1))])
    binary = bytearray()
    joints = [indices[n] for n in parents]
    def unsigned(values, kind):
        values = np.asarray(values, dtype='<u2')
        while len(binary)%4: binary.append(0)
        doc['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=values.nbytes)); binary.extend(values.tobytes())
        doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1, componentType=5123,count=len(values),type=kind))
        return len(doc['accessors'])-1
    vertices = np.concatenate([globals_ref[n][:3,3]+np.array([[0,0,0],[.015,0,0],[0,.015,0]]) for n in parents])
    joint_values = np.zeros((len(vertices),4),dtype=int); joint_values[:,0] = np.repeat(np.arange(len(joints)),3)
    weights = np.zeros((len(vertices),4)); weights[:,0] = 1
    doc['meshes'] = [dict(primitives=[dict(material=0, attributes=dict(
        POSITION=append_accessor(doc,binary,vertices,'VEC3'), JOINTS_0=unsigned(joint_values,'VEC4'),
        WEIGHTS_0=append_accessor(doc,binary,weights,'VEC4')),indices=unsigned(np.arange(len(vertices)),'SCALAR'))])]
    inverse = np.array([np.linalg.inv(globals_ref[n]) for n in parents])
    doc['skins'] = [dict(joints=joints,skeleton=indices['Hips'],inverseBindMatrices=append_accessor(doc,binary,inverse.transpose(0,2,1).reshape(-1,16),'MAT4'))]
    animation = dict(name='Existing authored gesture',channels=[],samplers=[],extras=dict(original=True))
    def channel(role,path,times,values,kind):
        a = append_accessor(doc,binary,np.array(times),'SCALAR'); b = append_accessor(doc,binary,values,kind)
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=indices[role],path=path)))
        animation['samplers'].append(dict(input=a,output=b,interpolation='LINEAR'))
    if animated:
        p = np.array(nodes[indices['Hips']]['translation'])
        channel('Hips','translation',[0.,.613725,2.0009999], [p,p+[.1,.04,-.2],p+[.7,.1,-.4]],'VEC3')
        for role, axis, angle in [('Hips','y',27),('Chest','x',-21),('LeftArm','z',-33),('LeftForeArm','y',16)]:
            rest = Rotation.from_quat(nodes[indices[role]]['rotation'])
            q = (Rotation.from_euler(axis,[0.,angle],degrees=True)*rest).as_quat()
            channel(role,'rotation',[0.,2.0009999],q,'VEC4')
    else:
        q = nodes[indices['Head']]['rotation']
        channel('Head','rotation',[0.,.73],[q,q],'VEC4')
    doc['animations'] = [animation]
    glb = folder/(label+'.glb'); write_glb(glb,doc,binary)
    profile = dict(schema='strep-rig-profile-v1',character_sha256=sha256(glb),reference_pose='default_nodes',
        mapping={r:label+'_'+r for r in roles},world_offset_m=[0.,0.,0.])
    path = folder/(label+'-profile.json'); save(path,profile)
    return glb,path


def pair(folder):
    a,ap = fixture(folder,'source',axes=23,optional=True)
    b,bp = fixture(folder,'target',axes=-31,optional=False,helpers=True,reverse=True,size=1.3,animated=False)
    return a,ap,b,bp


def varied_pair(folder):
    a,ap=fixture(folder,'source-helper',axes=19,optional=True,helpers=True)
    b,bp=fixture(folder,'target-short',axes=-42,optional=False,size=.85,reverse=True,animated=False)
    source=RigAsset.load(a);doc=copy.deepcopy(source.document);binary=bytearray(source.binary)
    helper=next(i for i,n in enumerate(doc['nodes']) if n['name']=='source-helper_LeftElbowHelper')
    rest=Rotation.from_quat(doc['nodes'][helper]['rotation'])
    q=(Rotation.from_euler('xz',[[0,0],[8,5],[-4,7]],degrees=True)*rest).as_quat()
    acc=append_accessor(doc,binary,q,'VEC4');times=append_accessor(doc,binary,np.array([0.,.413725,2.0009999]),'SCALAR')
    anim=doc['animations'][0];anim['channels'].append(dict(sampler=len(anim['samplers']),target=dict(node=helper,path='rotation')))
    anim['samplers'].append(dict(input=times,output=acc,interpolation='LINEAR'))
    write_glb(a,doc,binary);p=read(ap);p['character_sha256']=sha256(a);save(ap,p)
    target=RigAsset.load(b);doc=copy.deepcopy(target.document)
    for role,delta in [('LeftArm',[0.,-.09,.03]),('LeftForeArm',[0.,-.06,.025]),('RightForeArm',[0.,-.03,-.025])]:
        node=next(n for n in doc['nodes'] if n['name']=='target-short_'+role)
        node['translation']=(np.array(node['translation'])+delta).tolist()
    write_glb(b,doc,target.binary);p=read(bp);p['character_sha256']=sha256(b)
    p['world_offset_m']=[.4,.12,-.2];p['axis_alignment_xyzw']={'LeftHand':Rotation.from_euler('y',8,degrees=True).as_quat().tolist()};save(bp,p)
    return a,ap,b,bp


def test_independent_hierarchies_rebase_root_anchor_preserve_assets_and_native_keys(tmp_path):
    a,ap,b,bp = pair(tmp_path); before={p:sha256(p) for p in (a,ap,b,bp)}
    out=tmp_path/'result'; report=bridge.export(a,ap,b,bp,0,out)
    assert report['source_skin_joints']==19 and report['target_skin_joints']==17
    assert report['fidelity']['passed'] and report['original_target_payload_preserved']
    assert report['duration_extension_s']==0 and report['all_source_keys_retained']
    assert not any(report[k] for k in ('contact_verified','quality_approved','engine_import_verified','release_approved'))
    assert {p:sha256(p) for p in before}==before
    src=RigAsset.load(a); target=RigAsset.load(b); derived=RigAsset.load(out/'character.glb')
    reader=NativeSupportSampler(derived.document,derived.binary,1)
    sm=report['source_mapping']; tm=report['target_mapping']; scale=report['scale_from_mean_leg_lengths']
    assert scale==pytest.approx(1.3)
    source_reader=NativeSupportSampler(src.document,src.binary,0)
    end=source_reader.duration
    for time in (0.,end):
        source_world=source_reader.sample(time); actual=reader.sample(time)
        expected_root=target.reference[tm['Hips'],:3,3]+scale*(source_world[sm['Hips'],:3,3]-src.reference[sm['Hips'],:3,3])
        np.testing.assert_allclose(actual[tm['Hips'],:3,3],expected_root,atol=2e-6,rtol=0)
        # Reference directions agree despite independently authored rest axes:
        # no neutral direction alignment rotation is needed in this fixture.
        for role,node in tm.items():
            expected=(source_world[sm[role],:3,:3]@src.reference[sm[role],:3,:3].T@target.reference[node,:3,:3])
            np.testing.assert_allclose(actual[node,:3,:3],expected,atol=2e-6,rtol=0)
        for node in report['calibration']['target_unmapped_joints']:
            parent=target.parents[node]
            np.testing.assert_allclose(np.linalg.inv(actual[parent])@actual[node],local_matrix(target.document['nodes'][node]),atol=2e-6,rtol=0)
    source_keys=np.unique(np.concatenate([c[2] for c in source_reader.channels]))
    assert all(np.isin(source_keys,c[2]).all() for c in reader.channels)
    assert derived.document['animations'][0]==target.document['animations'][0]
    assert derived.binary[:len(target.binary)]==target.binary
    # Software-fixture CPU skin only; complete weighted test triangles preserved.
    np.testing.assert_allclose(derived.vertices(derived.reference),target.vertices(target.reference),atol=1e-12,rtol=0)
    with pytest.raises(ValueError,match='Fresh'):bridge.export(a,ap,b,bp,0,out)


def test_nonzero_profile_placement_anchors_root_without_rotating_trajectory(tmp_path):
    a,ap,b,bp=pair(tmp_path); p=read(bp);p['world_offset_m']=[2.,-.5,1.];save(bp,p)
    report=bridge.export(a,ap,b,bp,0,tmp_path/'result')
    saved=read(tmp_path/'result'/'root-motion.json');target=RigAsset.load(b)
    np.testing.assert_allclose(saved['positions_m'][0],target.reference[report['target_mapping']['Hips'],:3,3]+[2.,-.5,1.],atol=1e-6,rtol=0)


def test_direction_alignment_is_explicit_when_reference_pose_differs(tmp_path):
    a,ap,b,bp=pair(tmp_path); target=RigAsset.load(b);doc=copy.deepcopy(target.document)
    # Change the default target arm position, rather than just its bone axes.
    node=read(bp)['mapping']['LeftArm'];idx=next(i for i,n in enumerate(doc['nodes']) if n['name']==node)
    doc['nodes'][idx]['translation'][1]+=.15
    write_glb(b,doc,target.binary);p=read(bp);p['character_sha256']=sha256(b);save(bp,p)
    report=bridge.export(a,ap,b,bp,0,tmp_path/'result',240)
    assert report['fidelity']['passed'] and 'may change' in report['calibration']['neutral_policy']


@pytest.mark.parametrize('fault',['source-hash','target-hash','source-offset','source-axes','target-role','boolean-index',
    'rate','step','cubic','stretch','scale','accessory','mapping-hierarchy','duplicate','degenerate'])
def test_invalid_or_lossy_contracts_reject_before_output(tmp_path,fault):
    a,ap,b,bp=pair(tmp_path); index=0;rate=120
    if fault in ('source-hash','source-offset','source-axes','target-role'):
        p=read(ap)
        if fault=='source-hash':p['character_sha256']='0'*64
        if fault=='source-offset':p['world_offset_m']=[1,0,0]
        if fault=='source-axes':p['axis_alignment_xyzw']={'Hips':[0,0,0,1]}
        if fault=='target-role':p['mapping'].pop('Neck1');q=read(bp);q['mapping']['Neck1']='target_LeftElbowHelper';save(bp,q)
        save(ap,p)
    elif fault in ('target-hash','mapping-hierarchy','duplicate'):
        p=read(bp)
        if fault=='target-hash':p['character_sha256']='0'*64
        if fault=='mapping-hierarchy':p['mapping']['LeftHand'],p['mapping']['RightHand']=p['mapping']['RightHand'],p['mapping']['LeftHand']
        if fault=='duplicate':p['mapping']['LeftHand']=p['mapping']['RightHand']
        save(bp,p)
    elif fault=='boolean-index':index=False
    elif fault=='rate':rate=30
    else:
        rig=RigAsset.load(a);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);anim=doc['animations'][0]
        if fault in ('step','cubic'):anim['samplers'][0]['interpolation']={'step':'STEP','cubic':'CUBICSPLINE'}[fault]
        else:
            role={'stretch':'LeftForeArm','scale':'Chest','accessory':'Mesh','degenerate':'LeftShin'}[fault]
            node=next(i for i,n in enumerate(doc['nodes']) if n['name']=='source_'+role)
            if fault=='degenerate':
                doc['nodes'][node]['translation']=[0.,0.,0.]
            else:
                path='scale' if fault=='scale' else 'translation';values=np.array([[1,1,1],[1.01,1,1]]) if path=='scale' else np.array([doc['nodes'][node]['translation'],np.array(doc['nodes'][node]['translation'])+[.1,0,0]])
                acc=append_accessor(doc,binary,values,'VEC3')
                anim['channels'].append(dict(sampler=len(anim['samplers']),target=dict(node=node,path=path)))
                times=append_accessor(doc,binary,np.array([0.,2.0009999]),'SCALAR')
                anim['samplers'].append(dict(input=times,output=acc,interpolation='LINEAR'))
        write_glb(a,doc,binary);p=read(ap);p['character_sha256']=sha256(a);save(ap,p)
    out=tmp_path/'result'
    with pytest.raises(ValueError):bridge.export(a,ap,b,bp,index,out,rate)
    assert not out.exists()


def test_fidelity_failure_is_kept_separate_from_originals(tmp_path,monkeypatch):
    a,ap,b,bp=pair(tmp_path);before={p:sha256(p) for p in (a,b)}
    original=bridge.verify
    def failed(*args,**kwargs):
        value=original(*args,**kwargs);value.update(passed=False,maximum_sampled_position_error_m=.02);return value
    monkeypatch.setattr(bridge,'verify',failed)
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='fidelity failed'):bridge.export(a,ap,b,bp,0,out)
    assert read(out/'report.json')['status']=='failed' and not read(out/'report.json')['quality_approved']
    assert (out/'character.glb').is_file() and read(out/'pipeline.json')['status']=='failed'
    assert {p:sha256(p) for p in before}==before


def test_source_input_change_detected_after_candidate_saved(tmp_path,monkeypatch):
    a,ap,b,bp=pair(tmp_path); original=bridge.verify
    def mutate(*args,**kwargs):
        value=original(*args,**kwargs);save(ap,{**read(ap),'notes':'changed during run'});return value
    monkeypatch.setattr(bridge,'verify',mutate)
    with pytest.raises(ValueError,match='Input or input snapshot'):bridge.export(a,ap,b,bp,0,tmp_path/'failed')
    assert read(tmp_path/'failed'/'pipeline.json')['status']=='failed'


def test_dense_clock_keeps_very_close_original_float32_keys(tmp_path):
    a,_,_,_=pair(tmp_path);rig=RigAsset.load(a);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    channel=sampler.channels[0]; near=np.array([0.,.5,np.nextafter(np.float32(.5),np.float32(1)),sampler.duration],dtype='<f4')
    sampler.channels=[(channel[0],channel[1],near,np.zeros((4,3)),channel[4])]
    times=bridge.clock(sampler,120)
    assert np.isin(near,times).all() and np.diff(times).min()==pytest.approx(float(near[2]-near[1]))


def test_animated_source_helper_asymmetric_reference_and_override(tmp_path):
    args=varied_pair(tmp_path);report=bridge.export(*args,0,tmp_path/'result',240)
    assert report['source_skin_joints']==21 and report['target_skin_joints']==15
    assert report['fidelity']['passed'] and report['fidelity']['maximum_sampled_position_error_m']>1e-7
    assert set(report['calibration']['axis_alignment_xyzw'])=={'LeftHand'}
    assert report['calibration']['target_unmapped_joints']==[]


def test_real_under_sampling_failure_retains_numbers_and_candidate(tmp_path):
    a,ap,b,bp=varied_pair(tmp_path)
    from rig_asset import array
    source=RigAsset.load(a);doc=copy.deepcopy(source.document);binary=bytearray(source.binary)
    for sampler in doc['animations'][0]['samplers']:
        times=array(doc,binary,sampler['input'])*.01
        sampler['input']=append_accessor(doc,binary,times,'SCALAR')
    write_glb(a,doc,binary);p=read(ap);p['character_sha256']=sha256(a);save(ap,p)
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='fidelity failed'):bridge.export(a,ap,b,bp,0,out,60)
    report=read(out/'report.json')
    assert not report['fidelity']['passed'] and report['status']=='failed'
    assert (report['fidelity']['maximum_sampled_position_error_m']>report['fidelity']['position_limit_m']
        or report['fidelity']['maximum_sampled_rotation_error_rad']>report['fidelity']['rotation_limit_rad'])
    assert (out/'character.glb').exists() and report['original_selected']
