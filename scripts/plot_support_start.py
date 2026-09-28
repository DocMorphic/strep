"""Plot completed clipped-start variants from verified summary evidence."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now


def run(summary,output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary,output=Path(summary).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve prior plots')
    evidence=read(summary/'summary.json');study=Path(evidence['study'])
    for path,digest in evidence['verified_files'].items():
        if sha256(path)!=digest:raise ValueError('Verified evidence changed')
    output.mkdir();figures=[]
    colors=['#7b8491','#bb4a47','#d59535','#178079']
    labels=['Raw transfer','Endpoint + temporal initializer','Extra iterations, original start ramp','Support retained from first frame']
    for row in evidence['rows']:
        folder=study/row['case'];traces=read(folder/'traces.json')['variants']
        fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
        fig.subplots_adjust(top=.79,bottom=.07,left=.10,right=.98,hspace=.10)
        for trace,color,label in zip(traces,colors,labels):
            y=np.asarray(trace['root_acceleration_magnitude_m_s2']);x=np.arange(1,len(y)+1);keep=(x>=0)&(x<=16)
            style='--' if trace['variant']=='same_start_weights' else '-'
            axes[0].plot(x[keep],y[keep],color=color,label=label,linewidth=1.5,linestyle=style)
            for ax,side in zip(axes[1:],['Left','Right']):
                y=np.asarray(trace['feet'][side]['speed_m_s']);x=np.arange(1,len(y)+1);keep=(x>=0)&(x<=16)
                ax.plot(x[keep],y[keep],color=color,linewidth=1.5,linestyle=style)
        axes[0].set_ylabel('Root acceleration (m/s²)')
        fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.925),fontsize=8,ncol=2)
        for ax,side in zip(axes[1:],['Left','Right']):ax.set_ylabel(side+' foot speed (m/s)')
        for ax in axes:
            ax.grid(alpha=.2);ax.set_ylim(bottom=0)
            ax.axvline(0,color='#444444',linewidth=.7,linestyle=':');ax.axvline(11,color='#444444',linewidth=.7,linestyle=':')
        axes[-1].set_xlabel('Frame · dotted lines bound the editable window; foot speed is the incoming step')
        fig.suptitle(row['case']+' · clipped-start support comparison\nEqual six-sweep budget · unconfirmed support · no quality approval',fontsize=12,y=.985)
        dest=output/(row['case']+'.png');fig.savefig(dest,dpi=160);plt.close(fig)
        figures.append(dict(case=row['case'],path=dest.name,sha256=sha256(dest)))
    save(output/'figures.json',dict(at=now(),summary_sha256=sha256(summary/'summary.json'),plotter_sha256=sha256(__file__),figures=figures,quality_approved=False))
    print(figures)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.summary,a.output)
