"""Verify raw solver proposals were projected into the unchanged original box."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from verify_angular_release import run as angular_audit


def run(folder,output):
    if output.exists():raise ValueError('Preserve previous audit')
    output.mkdir(parents=True);angular_audit(folder,output/'angular')
    base=read(output/'angular/completion.json');solver=read(folder/'take/solver.json');spec=read(folder/'take/spec.json')
    limits=spec['limits'];full=np.r_[[limits['root_horizontal_m']/np.sqrt(2),limits['root_vertical_m'],limits['root_horizontal_m']/np.sqrt(2)],
        np.repeat(np.radians([j['limit_degrees'] for j in spec['edit_joints'].values()])/np.sqrt(3),3)]
    bounds=np.tile(full[solver['free_columns']],len(solver['variable_frames']));x=np.asarray(solver['starting_coordinates'],float);checked=0;largest=0.
    for step in solver['history']:
        accepted=None
        for attempt in step['attempts']:
            if 'raw_proposed_delta' not in attempt:continue
            raw=np.asarray(attempt['raw_proposed_delta']);trust=attempt['trust']
            if raw.shape!=x.shape or not np.isfinite(raw).all():raise ValueError('Invalid raw proposal')
            expected=np.clip(raw,np.maximum(-trust,-bounds-x),np.minimum(trust,bounds-x))
            if 'proposed_delta' in attempt:np.testing.assert_array_equal(expected,attempt['proposed_delta'])
            change=float(np.abs(expected-raw).max());largest=max(largest,change)
            if change!=attempt['max_projection_change'] or np.abs(expected).max()>trust:raise ValueError('Projection record differs')
            checked+=1
            for trial in attempt['trials']:
                if trial['accepted']:accepted=trial['fraction']*expected
        if accepted is not None:x+=accepted
    np.testing.assert_allclose(x,solver['final_coordinates'],atol=1e-14,rtol=0)
    result=dict(base,at=now(),implementation_sha256=sha256(__file__),angular_audit_sha256=sha256(output/'angular/completion.json'),
        projected_proposals_checked=checked,max_projection_change=largest,projection_reconstructed=True,quality_approved=False)
    save(output/'completion.json',result);print(dict(projected_proposals_checked=checked,max_projection_change=largest,target_passed=result['target_passed'],all_preservation_checks_passed=result['all_preservation_checks_passed']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
