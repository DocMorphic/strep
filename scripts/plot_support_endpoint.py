"""Plot independently decoded endpoint speeds from a completed experiment."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now


def run(folder,output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder,output=Path(folder).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous plot')
    proof=read(folder/'completion.json');request=read(folder/'request.json')
    if read(folder/'pipeline.json')['status']!='complete' or sha256(folder/'traces.json')!=proof['traces_sha256']:
        raise ValueError('Incomplete/changed decoded traces')
    if sha256(folder/'results.json')!=proof['results_sha256'] or sha256(folder/'engine/audit/verification.json')!=proof['engine_sha256']:
        raise ValueError('Changed completion evidence')
    traces=read(folder/'traces.json')['variants'];source=Path(request['source'])
    paths={'raw':source/'input/character.glb','parent_correction':source/'candidate/character.glb',
        **{v:folder/v/'candidate/character.glb' for v in ['same_weights_continuation','retain_end_support']}}
    engine={c['id']:c for c in read(folder/'engine/audit/verification.json')['checks']}
    for row in traces:
        if sha256(paths[row['variant']])!=row['source_sha256'] or engine[row['variant']]['source_sha256']!=row['source_sha256']:
            raise ValueError('Trace/engine source mismatch')
    colors=['#7b8491','#b75635','#db9a3a','#147c75']
    labels=['Raw transfer','Prior correction','Extra iterations, same weights','Support retained through clip end']
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    for row,color,label in zip(traces,colors,labels):
        for ax,side in zip(axes[:2],['Left','Right']):
            y=np.asarray(row['feet'][side]['speed_m_s']);x=np.arange(1,len(y)+1)
            keep=x>=request['first_editable_frame']
            ax.plot(x[keep],y[keep],color=color,label=label,linewidth=1.8,
                linestyle='--' if row['variant']=='same_weights_continuation' else '-')
    for ax,side in zip(axes[:2],['Left','Right']):
        ax.set_ylabel(side+' foot speed (m/s)');ax.grid(alpha=.2);ax.set_ylim(bottom=0)
    axes[0].legend(loc='upper left',fontsize=8)
    for name,color,label in [('same_weights_continuation',colors[2],'Original EOF fade'),('retain_end_support',colors[3],'Retained EOF support')]:
        recipe=read(folder/name/'request.json');weights=recipe['support']['guides']['Left']['weights'];x=np.arange(len(weights));keep=x>=request['first_editable_frame']
        axes[2].plot(x[keep],np.asarray(weights)[keep],color=color,label=label,marker='o',markersize=3)
    axes[2].set_ylabel('Drafted support weight');axes[2].set_xlabel('Frame (speed is the incoming step)')
    axes[2].set_ylim(0,1.1);axes[2].grid(alpha=.2);axes[2].legend(loc='lower left',fontsize=8)
    fig.suptitle('A clip boundary was treated as a foot release\nOne development input · matched six-sweep tail continuations · support labels unconfirmed',fontsize=12)
    output.mkdir();path=output/'endpoint-speeds.png';fig.savefig(path,dpi=160);plt.close(fig)
    save(output/'plot.json',dict(at=now(),completion_sha256=sha256(folder/'completion.json'),traces_sha256=proof['traces_sha256'],
        plotter_sha256=sha256(__file__),png_sha256=sha256(path),quality_approved=False))
    print(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder,a.output)
