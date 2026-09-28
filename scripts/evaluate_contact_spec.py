"""Independently measure explicit contact targets on the full eight-weight skin."""
import argparse
import numpy as np
from contact_spec import validate
from support_contact import regions
from floor_contact import Surface
from build_soma_preview import ASSET
from strep import read,save,sha256


def evaluate(base,candidate,skin,spec,tolerance_m=.03):
    groups=regions(skin);validate(spec,len(base['root_positions']),groups)
    surface=Surface(skin);records=[]
    for name,entry in spec['regions'].items():
        if entry['mode']!='explicit':continue
        for interval in entry['segments']:
            start,end=interval['start_frame'],interval['end_frame']
            ids=groups[name]
            if 'vertex_id' in interval:vertex=interval['vertex_id']
            else:
                points=surface.vertices(base['global_rot_mats'][start],base['posed_joints'][start],ids)
                vertex=int(ids[points[:,1].argmin()])
            errors=[]
            for f in range(start,end+1):
                p=surface.vertices(candidate['global_rot_mats'][f],candidate['posed_joints'][f],[vertex])[0]
                if interval['space']=='world':target=np.asarray(interval['position_m'])
                elif interval['space']=='track':target=np.asarray(interval['positions_m'][f-start])
                else:
                    target=surface.vertices(base['global_rot_mats'][f],base['posed_joints'][f],[vertex])[0]
                    target[1]=max(.002,target[1])
                errors.append(float(np.linalg.norm(p-target)))
            records.append(dict(region=name,start_frame=start,end_frame=end,vertex_id=vertex,space=interval['space'],
                mean_error_m=float(np.mean(errors)),p95_error_m=float(np.percentile(errors,95)),max_error_m=max(errors),
                frames_outside_tolerance=int(np.sum(np.array(errors)>tolerance_m)),frame_count=len(errors),per_frame_error_m=errors))
    return dict(intervals=records,tolerance_m=tolerance_m,all_explicit_targets_within_tolerance=bool(records) and all(r['frames_outside_tolerance']==0 for r in records),
        scope='Requested interval/point error, independent of optimization weights. No force, semantic, unrequested-contact or collision certification; empty explicit target list is not a pass.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('take');a=p.parse_args()
    from pathlib import Path
    path=Path(a.take);result=evaluate(dict(np.load(path/'limb/motion.npz')),dict(np.load(path/'motion.npz')),dict(np.load(ASSET)),read(path/'contact-spec.json'))
    result['evaluator_sha256']=sha256(__file__);save(path.parent.parent/'explicit-contact-evaluation.json',result);print(result)
