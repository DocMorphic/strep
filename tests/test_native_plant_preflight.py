"""Necessary native-key rejection, conservative applicability and pipeline ordering."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_foot_plant import setup
from gltf_tools import append_accessor,write_glb,accessor
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_foot_plant import patch_geometry
from strep import sha256,save,read
import native_plant_preflight as preflight
import native_studio_plant as pipeline


def fixture(tmp_path,*,travel=0.,rotate=False):
    source,rig,reader,spec,draft,policy,rows,limits=setup(tmp_path,moving=False)
    doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    animation=doc['animations'][0]
    for channel in animation['channels']:
        sampler=animation['samplers'][channel['sampler']]
        if channel['target']['path']=='translation':
            values=accessor(doc,data,sampler['output']).copy();values[:,0]=np.linspace(0,travel,len(values))
            sampler['output']=append_accessor(doc,data,values,'VEC3')
        elif rotate and channel['target']['node']==3:
            # Separate the formerly shared rotation sampler: only the foot rotates.
            angle=np.zeros(11);angle[5:]=30.
            values=Rotation.from_euler('y',angle,degrees=True).as_quat()
            channel['sampler']=len(animation['samplers'])
            animation['samplers'].append(dict(sampler,output=append_accessor(doc,data,values,'VEC4')))
    write_glb(source,doc,data)
    rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    spec['glb_sha256']=sha256(source);save(draft,spec)
    _,rows=validate(spec,rig,reader,sha256(source))
    return source,rig,reader,spec,draft,rows,limits


def test_satisfactory_patch_is_only_not_ruled_out(tmp_path):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path)
    result=preflight.analyze(rig,reader,rows,limits)
    assert result['status']=='not_ruled_out' and result['complete_native_key_coverage']
    assert result['native_keys_checked']>=2 and result['point_observations']>=6
    assert not any(result[k] for k in ('quality_approved','feasibility_proven','formal_interval_certificate','interpolated_times_checked'))


def test_reachable_rotation_moves_mesh_more_than_ankle_without_false_rejection(tmp_path):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path,rotate=True)
    rows[0]['displacement']=.000001
    points,anchor,patch,_=patch_geometry(rig,reader,rows[0])
    current=points(reader.sample(1.)[None])[0,patch]
    assert np.max(np.linalg.norm(current-anchor[patch],axis=1))>.01
    # Undoing the 30-degree foot rotation exactly restores the source patch;
    # the ankle does not move, and the authored local angle allowance is 45.
    np.testing.assert_allclose(reader.sample(1.)[3,:3,3],reader.sample(.8)[3,:3,3],atol=1e-12)
    assert preflight.analyze(rig,reader,rows,limits)['status']=='not_ruled_out'


def test_long_root_travel_has_actionable_native_key_witness(tmp_path):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path,travel=.2)
    rows[0].update(displacement=.000001,angle=.0001)
    result=preflight.analyze(rig,reader,rows,limits)
    assert result['status']=='incompatible_support_target'
    witness=result['supports'][0]['worst_conflict']
    assert witness['required_point_displacement_m']>.01
    assert witness['pivot_translation_allowance_m']==pytest.approx(.0000011)
    assert witness['world_angle_allowance_degrees']==pytest.approx(.0006)
    assert 'original clip is preserved' in preflight.conflict_message(result)


def test_frozen_boundary_has_no_translation_or_rotation_allowance(tmp_path):
    _,rig,reader,spec,_,_,limits=fixture(tmp_path,travel=.2)
    spec['supports'][0].update(edit_keys=[2,6],stance_s=[float(reader.channels[0][2][4]),float(reader.channels[0][2][6])])
    _,rows=validate(spec,rig,reader,spec['glb_sha256'])
    result=preflight.analyze(rig,reader,rows,limits);w=result['supports'][0]['worst_conflict']
    assert w['frozen_key'] and w['pivot_translation_allowance_m']==w['world_angle_allowance_degrees']==0


@pytest.mark.parametrize('kind',['static_scale','matrix','scale_channel','outside_influence','too_many_points'])
def test_unsupported_applicability_keeps_ordinary_fitting_available(tmp_path,monkeypatch,kind):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path,travel=.2)
    if kind=='static_scale':rig.document['nodes'][0]['scale']=[1,1.000001,1]
    elif kind=='matrix':rig.document['nodes'][0]['matrix']=np.eye(4).reshape(-1).tolist()
    elif kind=='scale_channel':reader.channels.append((0,'scale',np.array([0.,2.]),np.ones((2,3)),'LINEAR'))
    elif kind=='too_many_points':monkeypatch.setattr(preflight,'MAX_POINT_OBSERVATIONS',1)
    else:
        original=preflight.NativeSupportSkin
        def mixed(rig):
            skin=original(rig);skin.weights[:,1]=1e-15;skin.nodes[:,1]=0
            return skin
        monkeypatch.setattr(preflight,'NativeSupportSkin',mixed)
    result=preflight.analyze(rig,reader,rows,limits)
    assert result['status']=='not_applicable' and result['incompatible_points']==0
    assert not result['complete_native_key_coverage']
    assert result['supports'][0]['reason']


def test_near_unit_plane_retains_original_clearance_convention(tmp_path):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path)
    plain=preflight.analyze(rig,reader,rows,limits)
    rows[0]['up']*=1+5e-9
    assert preflight.analyze(rig,reader,rows,limits)['status']==plain['status']


def test_existing_clearance_roundoff_tolerance_is_respected_at_frozen_keys(tmp_path):
    _,rig,reader,spec,_,rows,limits=fixture(tmp_path)
    row=rows[0]
    points,_,patch,_=patch_geometry(rig,reader,row)
    height=float(np.min(points(reader.sample(1.)[None])[0,patch]@row['up']+row['offset']))
    spec['supports'][0].update(edit_keys=[4,8],stance_s=[float(row['clock'][4]),float(row['clock'][6])],clearance_m=height+5e-9)
    _,rows=validate(spec,rig,reader,spec['glb_sha256'])
    assert preflight.analyze(rig,reader,rows,limits)['status']=='not_ruled_out'


def test_between_key_excursion_is_not_claimed_checked(tmp_path):
    _,rig,reader,_,_,rows,limits=fixture(tmp_path)
    sample=reader.sample;clock=rows[0]['clock']
    def excursion(t):
        world=sample(t)
        if not np.any(np.abs(clock-t)<1e-7) and abs(t-rows[0]['stance_s'][0])>1e-7:world[:,:3,3]+=[.2,0,0]
        return world
    reader.sample=excursion
    assert reader.sample(.9)[3,0,3]-sample(.9)[3,0,3]>.1
    result=preflight.analyze(rig,reader,rows,limits)
    assert result['status']=='not_ruled_out' and not result['interpolated_times_checked']


def test_impossible_target_stops_before_seed_or_optimizer_preserving_inputs(tmp_path,monkeypatch):
    source,rig,reader,spec,draft,rows,limits=fixture(tmp_path,travel=.2)
    spec['supports'][0].update(maximum_displacement_m=.000001,maximum_angle_degrees=.0001);save(draft,spec)
    original={p:p.read_bytes() for p in (source,draft)}
    def forbidden(*args,**kwargs):pytest.fail('Impossible target reached expensive fitting')
    monkeypatch.setattr(pipeline,'propose',forbidden);monkeypatch.setattr(pipeline,'joint_fit',forbidden)
    output=tmp_path/'rejected'
    with pytest.raises(ValueError,match='cannot hold its foot patch'):
        pipeline.run(source,draft,output,dict(maximum_patch_anchor_error_m=.00002,maximum_patch_speed_m_s=.0001),headroom=True,preflight=True)
    early=read(output/'plant-preflight.json')
    assert early['source_sha256']==sha256(source) and early['draft_sha256']==sha256(draft)
    assert early['policy_sha256']==sha256(output/'plant-policy.json')
    assert all(p.read_bytes()==b for p,b in original.items())
    assert (output/'input.glb').read_bytes()==source.read_bytes()
    assert read(output/'pipeline.json')['status']=='failed'
    assert not (output/'plant-seed.glb').exists() and not (output/'joint').exists()


def test_source_changed_during_check_cannot_enter_optimizer(tmp_path,monkeypatch):
    source,_,_,_,draft,_,_=fixture(tmp_path)
    analyze=preflight.analyze
    def stale(*args):
        result=analyze(*args);source.write_bytes(source.read_bytes()+b'changed');return result
    monkeypatch.setattr(preflight,'analyze',stale)
    with pytest.raises(ValueError,match='changed during preflight'):
        pipeline.run(source,draft,tmp_path/'stale',dict(maximum_patch_anchor_error_m=.00002,maximum_patch_speed_m_s=.0001),headroom=True,preflight=True)
    assert not (tmp_path/'stale/plant-seed.glb').exists()


@pytest.mark.parametrize('limits',[None,[],{}, {'left-stance':None},{'left-stance':{'anchor':True,'speed':.001}}])
def test_invalid_limits_are_explicitly_rejected(tmp_path,limits):
    _,rig,reader,_,_,rows,_=fixture(tmp_path)
    with pytest.raises(ValueError):preflight.analyze(rig,reader,rows,limits)
