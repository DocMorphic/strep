"""Bounded planar foot-patch correction with independent serialized gates.

Authored intervals and fixed vertex identities define the target. This does
not infer a sole, semantic contact, balance, dynamics or continuous collision.
"""
from pathlib import Path
import argparse
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate,number
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region,export_rotations
from native_contact_diagnostics import measure,patch_metrics
from contact_rate_path import ProjectedSkin
from paired_temporal_neighbor import rotation_channels
from two_bone_waypoint import reach
from gltf_tools import accessor


def mesh_accessor_payload(document,binary,index):
    """Read stored mesh elements for preservation, without dequantizing them.

    Normalized integer attributes can remain opaque to motion computation.
    Sparse layouts retain the existing unsupported-input rejection.
    """
    item=document['accessors'][index]
    normalized=item.get('normalized',False)
    if type(normalized) is not bool or normalized and item['componentType'] not in (5120,5121,5122,5123):
        raise ValueError('Invalid normalized mesh accessor encoding')
    raw=dict(document);raw['accessors']=list(document['accessors'])
    record=dict(item);record.pop('normalized',None);raw['accessors'][index]=record
    metadata={k:v for k,v in item.items() if k not in ('bufferView','byteOffset')}
    return metadata,accessor(raw,binary,index)


def policy_rows(policy,source,base,draft,rows):
    fields={'schema','source_sha256','base_sha256','draft_sha256','supports'}
    if (not isinstance(policy,dict) or set(policy)!=fields or policy['schema']!='strep-native-foot-plant-v1'
            or policy['source_sha256']!=sha256(source) or policy['base_sha256']!=sha256(base)
            or policy['draft_sha256']!=sha256(draft)):
        raise ValueError('Source/base/draft-bound foot-plant policy required')
    items=policy['supports']
    if not isinstance(items,list) or len(items)!=len(rows):raise ValueError('One plant limit per support required')
    result={}
    for item in items:
        if (not isinstance(item,dict) or set(item)!={'id','maximum_patch_anchor_error_m','maximum_patch_speed_m_s'}
                or not isinstance(item['id'],str) or item['id'] in result):
            raise ValueError('Distinct named plant limits required')
        result[item['id']]=dict(anchor=number(item['maximum_patch_anchor_error_m'],'patch anchor error',0,.03),
                               speed=number(item['maximum_patch_speed_m_s'],'patch speed',0,.1))
    if set(result)!={r['id'] for r in rows}:raise ValueError('Plant support identities differ')
    return result


def envelope(times,edit,stance):
    times=np.asarray(times,float);start,end=edit;a,b=stance
    if (times.ndim!=1 or not np.isfinite(times).all() or not np.isfinite([start,end,a,b]).all()
            or not start<=a<b<=end or start==end):raise ValueError('Ordered finite edit/stance times required')
    weight=np.ones(len(times))
    def smooth(x):return x*x*x*(10+x*(-15+6*x))
    if a>start:weight[times<a]=smooth(np.clip((times[times<a]-start)/(a-start),0,1))
    if b<end:weight[times>b]=smooth(np.clip((end-times[times>b])/(end-b),0,1))
    weight[(times<=start)|(times>=end)]=0
    return weight


def patch_geometry(rig,reader,row):
    skin=NativeSupportSkin(rig);region=foot_region(skin,rig.parents,row['chain'][-1])
    projections=[ProjectedSkin(skin,region,axis) for axis in np.eye(3)]
    def points(world):return np.stack([p.evaluate(world) for p in projections],axis=2)
    anchor=points(np.array([reader.sample(row['stance_s'][0])]))[0]
    heights=anchor@row['up']+row['offset'];patch=np.flatnonzero(heights<=heights.min()+.003)
    return points,anchor,patch,skin.vertex_references[region[patch]].tolist()


def preserve(source,candidate,rows):
    """Verify all native tracks except declared interior leg rotations exactly."""
    allowed={n for r in rows for n in r['chain']}
    if len(source.channels)!=len(candidate.channels) or source.duration!=candidate.duration:
        raise ValueError('Native channels/duration changed')
    for old,new in zip(source.channels,candidate.channels):
        if old[:2]!=new[:2] or old[4]!=new[4] or not np.array_equal(old[2],new[2]):
            raise ValueError('Native channel identities/clocks changed')
        if old[1]!='rotation' or old[0] not in allowed:
            if not np.array_equal(old[3],new[3]):raise ValueError('Unedited native track changed')
        else:
            frozen=np.ones(len(old[2]),bool)
            for row in rows:
                if old[0] in row['chain']:
                    a,b=row['edit_keys'];frozen[a+1:b]=False
            if not np.array_equal(old[3][frozen],new[3][frozen]):raise ValueError('Frozen native rotation keys changed')


def propose(source_rig,source_reader,base_rig,base_reader,rows,path):
    channels=rotation_channels(base_rig.document,base_rig.binary)
    values={n:channels[n][2].copy() for row in rows for n in row['chain']};reports=[]
    for row in rows:
        points,anchor,patch,refs=patch_geometry(source_rig,source_reader,row)
        first,last=row['edit_keys'];clock=row['clock'][first:last+1]
        world=np.array([base_reader.sample(float(t)) for t in clock])
        u=row['up'];target=anchor[patch].mean(axis=0)
        centroid=points(world)[:,patch].mean(axis=1)
        delta=target-centroid;delta-=np.outer(delta@u,u)
        delta*=envelope(clock,row['edit_s'],row['stance_s'])[:,None]
        delta[[0,-1]]=0
        shifts=[]
        for key,(pose,shift) in enumerate(zip(world,delta)):
            if key in (0,len(clock)-1) or np.linalg.norm(shift)<=1e-12:continue
            _,local=reach(pose,base_rig.parents,*row['chain'],pose[row['chain'][-1],:3,3]+shift)
            for node,q in zip(row['chain'],Rotation.from_matrix(local[row['chain'],:3,:3]).as_quat()):
                values[node][first+key]=q if q@channels[node][2][first+key]>=0 else -q
            shifts.append(float(np.linalg.norm(shift)))
        reports.append(dict(id=row['id'],source_patch_vertex_references=refs,patch_vertices=len(patch),
            maximum_proposed_tangential_ankle_shift_m=max(shifts,default=0.),
            method='Planar patch-centroid target, quintic exterior ramps, exact two-bone IK with retained foot-world orientation'))
    export_rotations(base_rig.document,base_rig.binary,values,path)
    return reports


def audit(source,candidate,spec,limits):
    diagnostics=measure(source,candidate,spec)
    rig=RigAsset.load(source);changed=RigAsset.load(candidate)
    old=NativeSupportSampler(rig.document,rig.binary,0);new=NativeSupportSampler(changed.document,changed.binary,0)
    _,rows=validate(spec,rig,old,sha256(source));preserve(old,new,rows)
    for mesh in rig.document['meshes']:
        for primitive in mesh['primitives']:
            ids=list(primitive['attributes'].values())
            if 'indices' in primitive:ids.append(primitive['indices'])
            ids.extend(i for target in primitive.get('targets',[]) for i in target.values())
            for i in ids:
                a=mesh_accessor_payload(rig.document,rig.binary,i);b=mesh_accessor_payload(changed.document,changed.binary,i)
                if a[0]!=b[0] or not np.array_equal(a[1],b[1]):raise ValueError('Native mesh payload changed')
    for image in rig.document.get('images',[]):
        if 'bufferView' in image:
            v=rig.document['bufferViews'][image['bufferView']];start=v.get('byteOffset',0);end=start+v['byteLength']
            w=changed.document['bufferViews'][image['bufferView']];other=w.get('byteOffset',0)
            if rig.binary[start:end]!=changed.binary[other:other+w['byteLength']]:raise ValueError('Native image payload changed')
    result=[]
    for row,observed in zip(rows,diagnostics['supports']):
        points,anchor,patch,refs=patch_geometry(rig,old,row);times=np.asarray(observed['times_s'])
        current=points(np.array([new.sample(float(t)) for t in times]))
        delta=current[:,patch]-anchor[patch];delta-=(delta@row['up'])[...,None]*row['up']
        error=float(np.linalg.norm(delta,axis=2).max());speed=observed['candidate']['maximum_patch_vertex_tangential_speed_m_s']
        limit=limits[row['id']]
        result.append(dict(id=row['id'],source_patch_vertex_references=refs,maximum_patch_anchor_error_m=error,
            maximum_patch_speed_m_s=speed,maximum_anchor_error_m=limit['anchor'],maximum_speed_m_s=limit['speed'],
            passed=bool(error<=limit['anchor'] and speed<=limit['speed'])))
    from native_review_support import serialized_screens
    screens=serialized_screens(source,candidate,spec)
    return dict(contacts=result,contact_samples_pass=all(r['passed'] for r in result),support_screens=screens,
                passed=all(r['passed'] for r in result) and screens['passed'],diagnostics=diagnostics,
                continuous_collision_certified=False,planted_contact_certified=False,quality_approved=False)


def run(source,base,draft,policy_path,output):
    source,base,draft,policy_path,output=map(lambda p:Path(p).resolve(),(source,base,draft,policy_path,output))
    if output.exists():raise ValueError('Choose a fresh foot-plant output directory')
    inputs={str(p):sha256(p) for p in (source,base,draft,policy_path)}
    spec=read(draft);rig=RigAsset.load(source);original=NativeSupportSampler(rig.document,rig.binary,0)
    base_rig=RigAsset.load(base);reader=NativeSupportSampler(base_rig.document,base_rig.binary,0)
    _,rows=validate(spec,rig,original,sha256(source));limits=policy_rows(read(policy_path),source,base,draft,rows)
    baseline=audit(source,base,spec,limits)
    output.mkdir();shutil.copyfile(base,output/'input.glb');archive=output/'implementation';archive.mkdir()
    names=('native_foot_plant.py','native_contact_diagnostics.py','native_support_clock.py','native_support_spec.py',
           'native_support_skin.py','native_leg_floor.py','native_review_support.py','two_bone_waypoint.py',
           'elbow_swivel.py','paired_guarded_temporal.py','paired_temporal_neighbor.py','paired_approach_basis.py',
           'contact_rate_path.py','sampled_motion_caps.py','native_engine_clock.py','rig_asset.py','gltf_tools.py','strep.py')
    from native_review_support import method_names
    methods={}
    for name in sorted(set(names)|set(method_names())):
        path=Path(__file__).resolve().parent/name;methods[str(path)]=sha256(path);shutil.copyfile(path,archive/name)
    save(output/'request.json',dict(at=now(),inputs_sha256=inputs,implementation_sha256=methods,
         spec=spec,policy=read(policy_path),scope='Deterministic planar patch correction; source-relative caps unchanged',quality_approved=False))
    save(output/'pipeline.json',dict(status='processing'))
    try:
        proposal=output/'proposal.glb';error=None;report=None;edits=None
        try:
            edits=propose(rig,original,base_rig,reader,rows,proposal)
            changed=RigAsset.load(proposal);preserve(reader,NativeSupportSampler(changed.document,changed.binary,0),rows)
            report=audit(source,proposal,spec,limits)
        except ValueError as exc:error=str(exc)
        accepted=bool(report and report['passed'] and not baseline['passed'])
        shutil.copyfile(proposal if accepted else base,output/'candidate.glb')
        chosen=audit(source,output/'candidate.glb',spec,limits)
        if any(sha256(p)!=d for p,d in {**inputs,**methods}.items()):raise ValueError('Plant inputs or methods changed')
        result=dict(status='complete',at=now(),retained_input=not accepted,
            retention_reason=None if accepted else 'input_already_satisfies_all_gates' if baseline['passed'] else 'plant_proposal_failed_gates',
            baseline=baseline,proposal=report,proposal_error=error,edits=edits,selected=chosen,
            candidate_sha256=sha256(output/'candidate.glb'),proposal_sha256=sha256(proposal) if proposal.exists() else None,
            quality_approved=False,training_admitted=False,release_approved=False,native_npz_conversion_verified=False)
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete'));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','draft','policy','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        result=run(args.source,args.base,args.draft,args.policy,args.output)
        print(dict(retained_input=result['retained_input'],reason=result['retention_reason'],proposal_error=result['proposal_error']))
