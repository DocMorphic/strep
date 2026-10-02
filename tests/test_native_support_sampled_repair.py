"""Decoded refinement cannot widen source bounds or hide rejected attempts."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from native_support_path import bend_box,restrict_box
from native_support_sampled_repair import neighbors,tighten,improving,propose
from native_support_spec import validate
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region
from contact_rate_path import ProjectedSkin
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import sha256,save,read
from gltf_tools import append_accessor,write_glb
from scipy.spatial.transform import Rotation


def context(tmp_path):
    source,rig,reader,spec=fixture(tmp_path)
    _,rows=validate(spec,rig,reader,sha256(source));r=rows[0];a,b=r['edit_keys'];clock=r['clock'][a:b+1]
    worlds=np.array([reader.sample(float(t)) for t in clock]);skin=NativeSupportSkin(rig)
    projection=ProjectedSkin(skin,foot_region(skin,rig.parents,r['chain'][-1]),r['up'],r['offset'])
    box=bend_box(worlds,rig.parents,r['chain'],projection.evaluate(worlds).min(axis=1),clock,r)
    return source,rig,reader,spec,[dict(row=r,clock=clock,box=box)]


def test_fractional_dependency_does_not_snap_to_nearby_key():
    clock=np.array([0.,.48814305663108826,1.])
    assert neighbors(clock,float(clock[1]))==[1]
    assert neighbors(clock,float(clock[1])+1.0667498e-7)==[1,2]
    assert neighbors(clock,float(clock[1])-1e-7)==[0,1]


@pytest.mark.parametrize('fault',['lower','upper','order','nan','boundary'])
def test_restricting_cannot_widen_or_move_a_frozen_end(tmp_path,fault):
    *_,data=context(tmp_path);box=data[0]['box'];lo=box['lower_lift'].copy();hi=box['upper_lift'].copy()
    if fault=='lower':lo[2]-=1e-8
    if fault=='upper':hi[2]+=1e-8
    if fault=='order':lo[2]=hi[2]+1e-8
    if fault=='nan':hi[2]=np.nan
    if fault=='boundary':lo[0]=hi[0]=1e-8
    with pytest.raises(ValueError,match='bounds'):restrict_box(box,lo,hi)


def test_tightening_touches_only_fractional_neighbors_and_remains_in_original_box(tmp_path):
    *_,data=context(tmp_path);d=data[0];r=d['row'];lo=d['box']['lower_lift'];hi=d['box']['upper_lift']
    limits={r['id']:(lo.copy(),hi.copy())};time=float((d['clock'][3]+d['clock'][4])/2)
    o=dict(stance_times=[time],heights=[-.0001],edit_times=[time],movement=[r['displacement']+.000004])
    tightened=tighten(data,[o],limits);a,b=tightened[r['id']]
    assert np.all(a>=lo) and np.all(b<=hi) and np.all(a<=b)
    assert a[3]>lo[3] and a[4]>lo[4] and b[3]<hi[3] and b[4]<hi[4]
    ids=[i for i in range(len(lo)) if i not in (3,4)]
    np.testing.assert_array_equal(a[ids],lo[ids]);np.testing.assert_array_equal(b[ids],hi[ids])
    np.testing.assert_array_equal(limits[r['id']][0],lo)


def test_frozen_endpoint_violation_rejects_instead_of_discarding_sample(tmp_path):
    *_,data=context(tmp_path);d=data[0];r=d['row']
    o=dict(stance_times=[float(d['clock'][0])],heights=[-.001],edit_times=[],movement=[])
    with pytest.raises(ValueError,match='bounds'):tighten(data,[o],{r['id']:(d['box']['lower_lift'],d['box']['upper_lift'])})


def test_lexicographic_score_does_not_accept_a_larger_worst_excess():
    assert improving((.1,5.),(.2,1.))
    assert improving((.2,.9),(.2,1.))
    assert not improving((.3,.1),(.2,1.)) and not improving((.2,1.),(.2,1.))


@pytest.mark.parametrize('kwargs',[{'sampled_support_repair':1},{'sampled_support_iterations':0},
    {'sampled_support_iterations':1},{'sampled_support_repair':True,'sampled_support_iterations':17},
    {'sampled_support_repair':True,'joint_rates':True}])
def test_opt_in_job_rejects_ambiguous_modes_before_reading_files(kwargs):
    import native_support_job as job
    with pytest.raises(ValueError):job.run('missing','missing','missing',**kwargs)


def test_actual_proposal_preserves_native_clocks_and_source_outside_edit(tmp_path):
    source,rig,reader,spec,_=context(tmp_path);_,rows=validate(spec,rig,reader,sha256(source));path=tmp_path/'repair.glb'
    report=propose(rig,reader,rows,path,iterations=2)[0]
    assert report['final_score'][0]<=report['initial_score'][0]
    assert sha256(path)==report['selected_proposal_sha256'] and not report['quality_approved']
    after=RigAsset.load(path);current=NativeSupportSampler(after.document,after.binary,0)
    assert current.duration==reader.duration and after.document['meshes']==rig.document['meshes'] and after.document['skins']==rig.document['skins']
    for a,b in zip(reader.channels,current.channels):np.testing.assert_array_equal(a[2],b[2])
    for time in (0.,.17,*rows[0]['edit_s'],1.83,2.):np.testing.assert_array_equal(current.sample(time),reader.sample(time))
    for time in (.617,1.13,1.67):np.testing.assert_array_equal(current.sample(time)[[0,5]],reader.sample(time)[[0,5]])
    with pytest.raises(ValueError,match='Fresh'):propose(rig,reader,rows,path,iterations=2)


def test_actual_job_archives_proposals_and_keeps_original_rate_gate(tmp_path,monkeypatch):
    import native_support_job as job
    source,rig,reader,spec,_=context(tmp_path);monkeypatch.setattr(job,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    draft=tmp_path/'draft.json';save(draft,spec);digest=sha256(source)
    out=tmp_path/'reports/repair';r=job.run(source,draft,out,sampled_support_repair=True,sampled_support_iterations=2)
    assert r['retained_input'] and r['candidate_sha256']==digest==sha256(out/'candidate.glb')==sha256(source)
    q=read(out/'request.json');assert q['sampled_support_iterations']==2 and q['spec']==spec
    assert 'native_support_sampled_repair.py' in q['implementation'] and not r['quality_approved']
    for trial in r['trials']:
        assert trial['status']=='complete' and not trial['source_rates_pass'] and not trial['selection_gates_pass']
        report=trial['proposal'][0];assert report['sampled_support_pass']==trial['support_samples_pass']
        assert r['outputs'][report['seed_file']]==report['seed_sha256']
        for step in report['history']:
            if 'file' in step:assert r['outputs'][step['file']]==step['sha256']


def test_real_between_key_penetration_is_repaired_and_each_saved_probe_replays(tmp_path):
    from native_support_path import propose as smoothing
    source,rig,reader,spec=fixture(tmp_path)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=doc['animations'][0]
    theta=np.deg2rad(np.where(np.arange(11)%2,4.,-4.))
    for channel in animation['channels']:
        node=channel['target']['node'];kind=channel['target']['path']
        if kind=='rotation' and node in (1,3):
            q=Rotation.from_rotvec(np.c_[theta*(1 if node==1 else -1),np.zeros((11,2))]).as_quat()
            sampler=copy.deepcopy(animation['samplers'][channel['sampler']]);sampler['output']=append_accessor(doc,binary,q,'VEC4')
            channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
        if kind=='translation':
            values=np.c_[np.zeros(11),np.cos(theta)+.008,np.zeros(11)]
            animation['samplers'][channel['sampler']]['output']=append_accessor(doc,binary,values,'VEC3')
    source=tmp_path/'curved.glb';write_glb(source,doc,binary);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    spec['glb_sha256']=sha256(source);spec['supports'][0]['plane']['offset_m']=0.
    _,rows=validate(spec,rig,reader,sha256(source));path=tmp_path/'refined.glb';report=propose(rig,reader,rows,path,iterations=4)[0]
    assert report['initial_score'][0]>0 and report['sampled_support_pass'] and report['final_score']==[0.,0.]
    assert any(s['status']=='accepted' for s in report['history'])
    projection=ProjectedSkin(NativeSupportSkin(rig),foot_region(NativeSupportSkin(rig),rig.parents,3),rows[0]['up'],rows[0]['offset'])
    def heights(p,clock):
        r=RigAsset.load(p);s=NativeSupportSampler(r.document,r.binary,0)
        return projection.evaluate(np.array([s.sample(float(t)) for t in clock])).min(axis=1)
    seed=tmp_path/report['seed_file'];assert heights(seed,[.8,1.,1.2]).min()>=0
    assert heights(seed,[.9,1.1]).min()<0 and heights(path,[.9,1.1]).min()>=0
    for index,step in enumerate(report['history']):
        if 'file' not in step:continue
        replay=tmp_path/f'replay-{index}.glb'
        bounds={name:(np.array(v['lower']),np.array(v['upper'])) for name,v in step['lift_limits_m'].items()}
        smoothing(rig,reader,rows,replay,lift_limits=bounds)
        assert sha256(replay)==step['sha256']
