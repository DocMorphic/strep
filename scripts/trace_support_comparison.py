"""Decode root/foot time traces for every completed matched comparison case."""
import argparse
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def extract(comparison,output):
    import numpy as np
    from threadpoolctl import threadpool_limits
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    comparison,output=Path(comparison).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier trace')
    summary=read(comparison/'summary.json')
    for path,digest in summary['verified_files'].items():
        if sha256(path)!=digest:raise ValueError('Changed comparison evidence')
    study,baseline=Path(summary['study']),Path(summary['baseline'])
    output.mkdir();rows=[]
    with threadpool_limits(limits=1):
        for pair in summary['paired']:
            new=study/'takes'/pair['case'];old=baseline/'takes'/(pair['case']+'-support')
            spec=read(new/'spec.json');annotations=read(new/'input/contacts.json');request=read(new/'request.json')
            count,fps=spec['frames'],spec['fps'];variants={};sources={}
            for method,path in [('input',new/'input/character.glb'),('original_support',old/'candidate/character.glb'),('revised_support',new/'candidate/character.glb')]:
                if str(path) not in summary['verified_files'] or sha256(path)!=summary['verified_files'][str(path)]:
                    raise ValueError('Trace source was not verified in comparison')
                rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
                root=[];centroids={k:[] for k in spec['patches']}
                for f in range(count):
                    world=sampler.sample(float(np.float32(f/fps)));root.append(world[spec['root_node'],:3,3])
                    vertices=rig.vertices(world)
                    for side,patch in spec['patches'].items():centroids[side].append(vertices[patch['vertices']][:,[0,2]].mean(axis=0))
                root=np.asarray(root);acc=np.diff(root,n=2,axis=0)*fps*fps;mag=np.linalg.norm(acc,axis=1)
                if abs(float(mag.max())-pair[method]['root_acceleration_max_m_s2'])>1e-10:raise ValueError('Acceleration proof mismatch')
                peak=int(mag.argmax())+1
                feet={}
                for side,points in centroids.items():
                    active=np.zeros(count,dtype=bool)
                    for interval in annotations['intervals']:
                        if interval['joint'] in [side+'Foot',side+'ToeBase']:
                            active[interval['start_frame']:interval['end_frame_exclusive']]=True
                    speed=np.linalg.norm(np.diff(points,axis=0),axis=1)*fps
                    feet[side]=dict(speed_m_s=speed.tolist(),predicted_support_steps=(active[:-1]&active[1:]).tolist(),
                        draft_weights=request['support']['guides'][side]['weights'])
                variants[method]=dict(root_positions_m=root.tolist(),root_acceleration_xyz_m_s2=acc.tolist(),
                    root_acceleration_magnitude_m_s2=mag.tolist(),peak_frame=peak,peak_acceleration_xyz_m_s2=acc[peak-1].tolist(),feet=feet)
                sources[method]=dict(path=str(path),sha256=sha256(path))
            raw=np.asarray(variants['input']['root_positions_m'])
            for method in ['original_support','revised_support']:
                delta=np.asarray(variants[method]['root_positions_m'])-raw
                acc=np.diff(delta,n=2,axis=0)*fps*fps
                variants[method]['root_correction_acceleration_magnitude_m_s2']=np.linalg.norm(acc,axis=1).tolist()
            data=dict(case=pair['case'],rig=pair['rig'],fps=fps,frames=count,sources=sources,variants=variants,quality_approved=False)
            save(output/(pair['case']+'.json'),data)
            peaks={m:dict(frame=v['peak_frame'],acceleration_xyz_m_s2=v['peak_acceleration_xyz_m_s2'],
                acceleration_m_s2=max(v['root_acceleration_magnitude_m_s2']),
                draft_weights={s:f['draft_weights'][v['peak_frame']] for s,f in v['feet'].items()}) for m,v in variants.items()}
            rows.append(dict(case=pair['case'],trace_sha256=sha256(output/(pair['case']+'.json')),peaks=peaks))
    save(output/'summary.json',dict(at=now(),comparison_sha256=sha256(comparison/'summary.json'),extractor_sha256=sha256(__file__),
        completed_cases=len(rows),planned_cases=summary['planned_pairs'],rows=rows,quality_approved=False,
        scope='Finite-difference kinematic diagnostics from decoded files. Root acceleration is not an estimate of net body force, balance or perceived realism. Predicted/drafted support remains unconfirmed.'))
    print(rows,flush=True)


def plot(folder,output=None):
    # Run with isolated plotting dependencies, not the frozen model runtime.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=Path(folder).resolve();summary=read(folder/'summary.json');figures=[]
    output=Path(output).resolve() if output else folder
    if output!=folder:output.mkdir(exist_ok=False)
    colors={'input':'#8c96a3','original_support':'#1674b8','revised_support':'#b84f1e'}
    labels={'input':'Input','original_support':'Original correction','revised_support':'Revised correction'}
    for row in summary['rows']:
        path=folder/(row['case']+'.json')
        if sha256(path)!=row['trace_sha256']:raise ValueError('Trace changed')
        data=read(path);fps=data['fps'];n=data['frames'];dest=output/(row['case']+'.png')
        if dest.exists():raise ValueError('Preserve earlier figure')
        fig,axes=plt.subplots(3,1,figsize=(10.4,7.4),sharex=True,layout='constrained')
        for method,v in data['variants'].items():
            color=colors[method]
            axes[0].plot([f/fps for f in range(1,n-1)],v['root_acceleration_magnitude_m_s2'],color=color,label=labels[method],linewidth=1.4)
            for ax,side in zip(axes[1:],['Left','Right']):
                foot=v['feet'][side]
                y=[speed if active else float('nan') for speed,active in zip(foot['speed_m_s'],foot['predicted_support_steps'])]
                ax.plot([(f+.5)/fps for f in range(n-1)],y,color=color,linewidth=1.4)
        for ax,side in zip(axes[1:],['Left','Right']):
            ax.axhline(.05,color='#66727e',linestyle='--',linewidth=.9)
            ax.set_ylabel(f'{side} foot speed\n(m/s, predicted support)')
        axes[0].set_ylabel('Root acceleration\n(m/s²)');axes[0].legend(loc='upper right',ncols=3,fontsize=9)
        v=data['variants']['revised_support'];frame=v['peak_frame'];peak=max(v['root_acceleration_magnitude_m_s2'])
        axes[0].annotate(f'Revised peak {peak:.2f} m/s²\nframe {frame}',xy=(frame/fps,peak),xytext=(.47,.86),textcoords='axes fraction',fontsize=9,va='top',
                         arrowprops=dict(arrowstyle='-',color='#b84f1e'),bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
        axes[-1].set_xlabel('Time (s)')
        for ax in axes:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.set_xlim(0,(n-1)/fps)
        fig.suptitle(f"{row['case']} · speed improvement and acceleration trade-off",fontsize=14)
        fig.text(.01,-.018,f"Development comparison: {summary['completed_cases']}/{summary['planned_cases']} cases complete. Dashed line: 0.05 m/s speed proxy. No motion-quality approval.",fontsize=9)
        fig.savefig(dest,dpi=150,bbox_inches='tight');plt.close(fig)
        figures.append(dict(path=dest.name,sha256=sha256(dest)))
    save(output/'figures.json',dict(at=now(),matplotlib_version=matplotlib.__version__,script_sha256=sha256(__file__),
        summary_sha256=sha256(folder/'summary.json'),figures=figures,quality_approved=False))
    print(figures,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('extract');e.add_argument('comparison',type=Path);e.add_argument('output',type=Path)
    q=sub.add_parser('plot');q.add_argument('folder',type=Path);q.add_argument('--output',type=Path);a=p.parse_args()
    if a.command=='extract':extract(a.comparison,a.output)
    else:plot(a.folder,a.output)
