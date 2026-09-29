"""Decoded per-joint and contact-boundary rate changes, without quality approval."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def compare_rates(source,candidate,names,windows,fps=30,subdivisions=4):
    source,candidate=np.asarray(source),np.asarray(candidate)
    if source.shape!=candidate.shape or source.ndim!=3 or source.shape[1:]!=(len(names),3) or len(source)<3:
        raise ValueError('Matching sampled joint positions required')
    if not np.isfinite(source).all() or not np.isfinite(candidate).all() or len(set(names))!=len(names):
        raise ValueError('Finite positions and distinct joint names required')
    if type(fps) not in (int,float) or not np.isfinite(fps) or fps<=0 or type(subdivisions)!=int or subdivisions<1:
        raise ValueError('Positive frame rate and integer subdivisions required')
    result={}
    for order,name,unit in [(1,'speed','m/s'),(2,'acceleration','m/s2')]:
        before=np.linalg.norm(np.diff(source,n=order,axis=0)*(fps*subdivisions)**order,axis=-1)
        after=np.linalg.norm(np.diff(candidate,n=order,axis=0)*(fps*subdivisions)**order,axis=-1)
        clock=(np.arange(len(before))+order/2)/subdivisions
        rows=[]
        for label,(start,end) in windows.items():
            if not np.isfinite([start,end]).all() or not 0<=start<=end<=(len(source)-1)/subdivisions:
                raise ValueError('Window outside sampled clip')
            mask=(clock>=start)&(clock<=end)
            if not mask.any():
                rows.append(dict(window=label,start_frame=start,end_frame=end,samples=0,joints=[]));continue
            a,b=before[mask],after[mask];times=clock[mask]
            joints=[dict(joint=n,source_peak=float(a[:,j].max()),candidate_peak=float(b[:,j].max()),
                         change=float(b[:,j].max()-a[:,j].max()),source_peak_frame=float(times[a[:,j].argmax()]),
                         candidate_peak_frame=float(times[b[:,j].argmax()])) for j,n in enumerate(names)]
            rows.append(dict(window=label,start_frame=start,end_frame=end,samples=int(mask.sum()),
                             source_peak=float(a.max()),candidate_peak=float(b.max()),
                             increased_joints_over_1e_5=sum(j['change']>1e-5 for j in joints),joints=joints))
        result[name]=dict(unit=unit,windows=rows)
    return result


def run(study,output):
    study,output=Path(study),Path(output)
    if output.exists():raise ValueError('Fresh rate report path required')
    result,protocol,scene=read(study/'result.json'),read(study/'protocol.json'),read(study/'authored-scene.json')
    if result['status']!='complete' or sha256(study/'protocol.json')!=result['protocol_sha256'] or sha256(study/'authored-scene.json')!=result['authored_scene_sha256']:
        raise ValueError('Completed unchanged study required')
    tracks=[];joint_names=None;count=scene['frame_count'];windows={'whole_clip':[0,count-1]}
    for c in scene['contacts']:
        if c['id'] not in protocol['contact_ids']:continue
        start,end=c['start_frame'],c['end_frame'];name=c['id']
        windows.update({name+'/approach':[0,start],name+'/grasp':[start,end],name+'/release':[end,count-1],
                        name+'/start_boundary':[max(0,start-2),min(count-1,start+2)],
                        name+'/end_boundary':[max(0,end-2),min(count-1,end+2)]})
    for label in ['source','candidate']:
        path=study/(label+'.glb')
        if sha256(path)!=result[label+'_glb_sha256']:raise ValueError('Export changed')
        doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
        names=[doc['nodes'][j]['name'] for j in joints]
        if joint_names is not None and joint_names!=names:raise ValueError('Joint identities changed')
        joint_names=names
        if abs(sampler.duration-(count-1)/30)>1e-5:raise ValueError('Clip duration mismatch')
        tracks.append(np.array([sampler.sample(t/120)[joints,:3,3] for t in range((count-1)*4+1)]))
    report=dict(result_sha256=sha256(study/'result.json'),auditor_sha256=sha256(__file__),
                rates=compare_rates(*tracks,joint_names,windows),quality_approved=False,
                scope='120 Hz finite differences on independently decoded GLBs. Speed timestamp is edge midpoint; acceleration timestamp is stencil center. Overlapping authored phase/boundary windows are diagnostic, not disjoint categories or acceptance gates.')
    save(output,report);print(dict(output=str(output),samples=len(tracks[0]),joints=len(joint_names)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study,a.output)
