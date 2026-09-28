"""Compare two completed case exports, even while other population cases run."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits

from strep import read,save,sha256,now
from compare_support_iterations import selected_metrics
from support_comparison_protocol import match_studies
from analyze_support_regressions import curve
from support_temporal_cleanup import support_mask
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(before,after,case_id,output,comparison_kind='iterations'):
    if output.exists():raise ValueError('Preserve the previous case audit')
    protocols=[read(folder/'protocol.json') for folder in [before,after]]
    match_studies(*protocols,comparison_kind)
    if not case_id or Path(case_id).name!=case_id:raise ValueError('Use a case identifier')
    case=next(c for c in protocols[1]['cases'] if c['id']==case_id)
    if not case['eligible']:raise ValueError('Only targeted, completed case pairs have edited outputs')
    inputs={};paths=[];audits=[]
    for study,protocol in zip([before,after],protocols):
        if read(study/'freeze.json')['protocol_sha256']!=sha256(study/'protocol.json'):
            raise ValueError('Study protocol changed')
        folder=study/case_id;result=read(folder/'result.json');audit=read(folder/'audit.json')
        selected_metrics(audit,result)
        if sha256(folder/'audit.json')!=result['audit_sha256']:raise ValueError('Case audit changed')
        path=Path(result['selected']).resolve()
        if not path.is_relative_to(study) or sha256(path)!=result['selected_sha256']:raise ValueError('Selected case changed')
        for name,digest in case['files'].items():
            if sha256(folder/'base'/name)!=digest:raise ValueError('Case source changed')
        for p in [study/'protocol.json',study/'freeze.json',folder/'result.json',folder/'audit.json',
                  folder/'base/spec.json',folder/'base/input/contacts.json',path]:
            inputs[str(p)]=sha256(p)
        paths.append(path);audits.append(audit)
    if audits[0]['source_sha256']!=audits[1]['source_sha256']:raise ValueError('Case inputs differ')
    spec=read(after/case_id/'base/spec.json');annotations=read(after/case_id/'base/input/contacts.json')
    expected_peaks=[{f['side']:f['selected_peak_m_s'] for f in selected_metrics(audit,read(study/case_id/'result.json'))['feet']}
                    for audit,study in zip(audits,[before,after])]
    return measure_pair(paths,spec,annotations,expected_peaks,output,case_id,comparison_kind,inputs)


def measure_pair(paths,spec,annotations,expected_peaks,output,case_id,comparison_kind,inputs):
    if output.exists():raise ValueError('Preserve previous decoded pair')
    rigs=[RigAsset.load(path) for path in paths]
    if rigs[0].parents!=rigs[1].parents:raise ValueError('Rig hierarchy changed')
    if not np.array_equal(rigs[0].inverse,rigs[1].inverse) or rigs[0].joints!=rigs[1].joints:raise ValueError('Skin binding changed')
    if len(rigs[0].primitives)!=len(rigs[1].primitives):raise ValueError('Mesh population changed')
    for a,b in zip(rigs[0].primitives,rigs[1].primitives):
        for key in ['positions','joints','weights']:
            if not np.array_equal(a[key],b[key]):raise ValueError('Skin geometry or weights changed')
    clocks=[AnimationSampler(rig.document,rig.binary,0) for rig in rigs]
    frames=spec['frames'];times=np.arange((frames-1)*4+1)/4
    output.mkdir(parents=True)
    roots=[[],[]];centers=[[],[]];rows=[]
    with threadpool_limits(limits=1):
        for index,frame in enumerate(times):
            sample=float(np.float32(frame/30)) if frame.is_integer() else frame/30
            world=[clock.sample(sample) for clock in clocks]
            vertices=[rig.vertices(w) for rig,w in zip(rigs,world)]
            depths=[np.maximum(-v[:,1],0) for v in vertices]
            delta=depths[1]-depths[0];vertex=int(delta.argmax())
            rows.append(dict(frame=float(frame),before_max_depth_m=float(depths[0].max()),after_max_depth_m=float(depths[1].max()),
                maximum_per_vertex_depth_increase_m=float(delta[vertex]),worst_vertex=vertex,
                before_witness_depth_m=float(depths[0][vertex]),after_witness_depth_m=float(depths[1][vertex])))
            if frame.is_integer():
                for i in [0,1]:
                    roots[i].append(world[i][spec['root_node'],:3,3])
                    centers[i].append([vertices[i][patch['vertices']].mean(axis=0) for patch in spec['patches'].values()])
            if index%100==0:save(output/'pipeline.json',dict(status='measuring',completed=index+1,total=len(times)))
    root_acc=[np.linalg.norm(np.diff(np.asarray(points),n=2,axis=0),axis=1)*900 for points in roots]
    speeds=[np.linalg.norm(np.diff(np.asarray(points)[:,:,[0,2]],axis=0),axis=2)*30 for points in centers]
    feet={}
    for index,side in enumerate(spec['patches']):
        active=support_mask(annotations,side,frames);mask=active[:-1]&active[1:]
        for i in range(2):
            expected=expected_peaks[i][side]
            peak=float(speeds[i][mask,index].max()) if mask.any() else None
            if peak!=expected:raise ValueError('Decoded speed differs from source audit')
        feet[side]=curve(speeds[0][:,index],speeds[1][:,index],np.arange(1,frames),mask)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Case evidence changed while measuring')
    worsened=[r for r in rows if r['maximum_per_vertex_depth_increase_m']>1e-6]
    save(output/'timeline.json',dict(rows=rows,quality_approved=False))
    save(output/'completion.json',dict(at=now(),case=case_id,comparison_kind=comparison_kind,inputs=inputs,before_sha256=sha256(paths[0]),after_sha256=sha256(paths[1]),
        samples=len(rows),fractions=[0,.25,.5,.75],terminal_frame_included=True,
        floor=dict(before_peak_m=max(r['before_max_depth_m'] for r in rows),after_peak_m=max(r['after_max_depth_m'] for r in rows),
            maximum_per_vertex_depth_increase_m=max(r['maximum_per_vertex_depth_increase_m'] for r in rows),
            worsened_samples=len(worsened),worst=max(rows,key=lambda r:r['maximum_per_vertex_depth_increase_m'])),
        root_acceleration=curve(root_acc[0],root_acc[1],np.arange(1,frames-1)),feet=feet,
        timeline_sha256=sha256(output/'timeline.json'),implementation_sha256=sha256(__file__),quality_approved=False,
        scope='One independently decoded, completed case pair; parent population may still run and final engine verification may be pending. '
              'Quarter/key floor and integer root/support dynamics compare the two bound outputs directly; a pilot candidate is not promoted. '
              '1micrometre floor reporting threshold unchanged. No continuous-time, semantic, anatomical or human approval.'))
    save(output/'pipeline.json',dict(status='complete',completion_sha256=sha256(output/'completion.json')))
    print(dict(case=case_id,samples=len(rows),floor_worsened_samples=len(worsened),
        foot_peak_changes={side:value.get('peak_change') for side,value in feet.items()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after']:p.add_argument(name,type=Path)
    p.add_argument('case');p.add_argument('output',type=Path)
    p.add_argument('--comparison-kind',choices=['iterations','backtracking'],default='iterations')
    a=p.parse_args();run(a.before.resolve(),a.after.resolve(),a.case,a.output.resolve(),a.comparison_kind)
