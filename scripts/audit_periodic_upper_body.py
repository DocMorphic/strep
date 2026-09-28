"""Additional upper-body-only audit, separate from the frozen release gate."""
import numpy as np
from strep import ROOT,read,save,now
from gltf_tools import read_glb,sample_animation


def main():
    folder=ROOT/'reports/periodic-controls-v1';summary=read(folder/'summary.json')
    skin=dict(np.load(ROOT/'vendor/kimodo/kimodo/assets/skeletons/somaskel77/skin_standard.npz'))
    selected={1}
    for parent,child in skin['rig_joint_connections']:
        if parent in selected:selected.add(int(child))
    indices=sorted(selected);records=[]
    def measures(positions):
        relative=positions[:,indices]-positions[:,:1]
        velocity=(np.roll(relative,-1,axis=0)-relative)*30
        acceleration=(np.roll(velocity,-1,axis=0)-velocity)*30
        return {name:np.linalg.norm(value,axis=-1).max(axis=0) for name,value in [('speed',velocity),('acceleration',acceleration)]}
    for trial in summary['trials']:
        take=folder/'takes'/trial['id'];motion=dict(np.load(take/'motion.npz'))
        doc,binary=read_glb(take/'before.glb')
        previous=np.array([sample_animation(doc,binary,0,i)[1:78,:3,3] for i in range(len(motion['posed_joints']))])
        before=measures(previous);after=measures(motion['posed_joints'])
        records.append({'id':trial['id'],**{k:{'before_upper_max':float(before[k].max()),'after_upper_max':float(after[k].max()),
            'max_per_joint_ratio':float((after[k]/np.maximum(before[k],.01)).max())} for k in before}})
    save(folder/'upper-body-audit.json',{'created_at':now(),'scope':'Post-hoc additional audit; separate from frozen whole-body gate. Every upper-body joint and every cyclic frame, relative to pelvis. Ratios use a 0.01 denominator floor. Not physical dynamics or contact validation.','trials':records})
    print({k:max(r[k]['max_per_joint_ratio'] for r in records) for k in ['speed','acceleration']})


if __name__=='__main__':main()
