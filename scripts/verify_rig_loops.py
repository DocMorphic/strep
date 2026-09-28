"""Independent decoded loop/seam, repeated placement, contacts and package checks."""
import argparse
import hashlib
import io
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from urllib.request import urlopen
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from gltf_tools import sample_animation
from rig_clip_import import AnimationSampler


def verify(job):
    folder=ROOT/'reports/rig-jobs'/job;recipe=read(folder/'loop.json');result=read(folder/'result.json');p=recipe['period_frames'];k=recipe['blend_frames'];start=recipe['start_frame'];root=result['root_node']
    source=RigAsset.load(folder/'input/character.glb');raw=np.array([sample_animation(source.document,source.binary,0,f) for f in range(start,start+p+k)])
    cycle=np.eye(4);cycle[:3,:3]=Rotation.from_euler('y',recipe['turn_degrees'],degrees=True).as_matrix();destination=raw[p,root,:3,3] if recipe.get('root_mode','travel')=='travel' else raw[0,root,:3,3];cycle[:3,3]=destination-cycle[:3,:3]@raw[0,root,:3,3];cycle[1,3]=0
    descendants=[]
    for node in range(len(source.parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=source.parents[ancestor]
        if ancestor==root:descendants.append(node)
    expected=[]
    for f in range(p):
        world=raw[f].copy()
        if f<k:
            tail=raw[p+f].copy();tail[descendants]=np.linalg.inv(cycle)@tail[descendants]
            a,b=tail.copy(),world.copy()
            for node,parent in enumerate(source.parents):
                if parent>=0:a[node]=np.linalg.inv(tail[parent])@tail[node];b[node]=np.linalg.inv(world[parent])@world[node]
            u=np.clip((f-1)/(k-2),0,1);weight=u*u*(3-2*u);local=a.copy();local[:,:3,3]=a[:,:3,3]*(1-weight)+b[:,:3,3]*weight
            for node in range(len(local)):local[node,:3,:3]=Slerp([0,1],Rotation.from_matrix(np.array([a[node,:3,:3],b[node,:3,:3]])))(weight).as_matrix()
            computed={}
            def pose(n):
                if n not in computed:computed[n]=local[n] if source.parents[n]<0 else pose(source.parents[n])@local[n]
                return computed[n]
            world=np.array([pose(n) for n in range(len(local))])
        expected.append(world)
    checks=[];cases=[]
    for name,count in [('transfer',p+1),('repeated',3*p+1)]:
        glb=folder/name/'character.glb';rig=RigAsset.load(glb);review=read(folder/name/'contact-review.json');patches={tuple(t['vertices']):[] for t in review['authored_targets']};maximum=0.;seams=[]
        for f in range(count):
            actual=sample_animation(rig.document,rig.binary,0,f);wanted=expected[f%p].copy();wanted[descendants]=np.linalg.matrix_power(cycle,f//p)@wanted[descendants]
            maximum=max(maximum,float(np.abs(actual-wanted).max()));points=rig.vertices(actual)
            for vertices,positions in patches.items():positions.append(points[list(vertices)].mean(axis=0))
            if f in (p-1,p,p+1):seams.append(actual)
        assert maximum<1e-5
        target_errors=[];speeds=[];all_weight_speeds=[]
        for target in review['authored_targets']:
            xyz=np.asarray(patches[tuple(target['vertices'])]);ids=[f['frame'] for f in target['output_frames'] if f['weight']>=1-1e-8]
            if not ids:continue
            target_errors.extend(np.linalg.norm(xyz[ids]-target['target_position_m'],axis=1).tolist())
            active=np.zeros(count,dtype=bool);active[ids]=True;v=np.linalg.norm(np.diff(xyz[:,[0,2]],axis=0),axis=1)*30;speeds.extend(v[active[:-1]&active[1:]].tolist())
        for vertices,positions in patches.items():
            active=np.zeros(count,dtype=bool)
            for target in review['authored_targets']:
                if tuple(target['vertices'])==vertices:
                    active[[e['frame'] for e in target['output_frames'] if e['weight']>0]]=True
            v=np.linalg.norm(np.diff(np.asarray(positions)[:,[0,2]],axis=0),axis=1)*30
            all_weight_speeds.extend(v[active[:-1]&active[1:]].tolist())
        entry=dict(variant=name,frames=count,max_world_matrix_error=maximum,full_weight_authored_target_error_max_m=max(target_errors) if target_errors else None,full_weight_authored_patch_speed_p95_m_s=float(np.percentile(speeds,95)) if speeds else None,
            any_weight_authored_patch_speed_p95_m_s=float(np.percentile(all_weight_speeds,95)) if all_weight_speeds else None,any_weight_authored_patch_speed_max_m_s=max(all_weight_speeds) if all_weight_speeds else None)
        if name=='repeated':
            seam_error=float(np.abs(np.array(seams)-raw[p-1:p+2]).max());assert seam_error<1e-5;entry['source_seam_error']=seam_error
        else:
            sampler=AnimationSampler(rig.document,rig.binary,0);entry['half_frame_floor_depth_max_m']=max(max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(p))
        checks.append(entry);cases.append(dict(id=job+'-'+name,path='../rig-jobs/'+job+'/'+name+'/character.glb',sha256=sha256(glb),frames=count,fps=30))
        assert hashlib.sha256(urlopen('http://127.0.0.1:8768/files/rig-jobs/'+job+'/'+name+'/character.glb').read()).hexdigest()==sha256(glb)
    package=urlopen('http://127.0.0.1:8768'+result['package']).read();assert hashlib.sha256(package).hexdigest()==result['package_sha256']
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name!='README.txt':assert z.read(name)==(folder/name).read_bytes()
        entries=len(z.namelist())
    return dict(job=job,variants=checks,package_entries=entries,audit=read(folder/'transfer/loop-audit.json')),cases


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study');p.add_argument('jobs',nargs='+');a=p.parse_args();checks=[];cases=[]
    for job in a.jobs:
        check,items=verify(job);checks.append(check);cases.extend(items)
    save(ROOT/a.study/'verification.json',dict(checks=checks,scope='Decoded loop oracle, repeated transforms, source seam and contact/half-frame diagnostics; not independent naturalness or support approval.'))
    save(ROOT/a.study/'manifest.json',dict(cases=cases));print(checks)
