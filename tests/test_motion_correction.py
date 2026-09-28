"""Guard the skeleton-space diagnostic and exercise the compiled correction."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from verify_motion_correction import anchor_errors


def test_boundary_diagnostic_uses_conditioned_hierarchy_not_expanded_preview():
    import torch
    from kimodo.skeleton import SOMASkeleton30
    guide=dict(np.load(ROOT/'reports/motion-correction-v1/jump-205/source-guide.npz'))
    s=SOMASkeleton30()
    projected=s.to_SOMASkeleton77(s.from_SOMASkeleton77(torch.tensor(guide['local_rot_mats']))).numpy()
    # Omitted helper/terminal joints differ but must not enter a SOMA30 target error.
    assert np.max(np.abs(projected-guide['local_rot_mats']))>.1
    position,rotation=anchor_errors(projected,guide['root_positions'],guide,[0,1,49,50])
    assert position<1e-7 and rotation<1e-5
    shifted=guide['root_positions'].copy();shifted[:,0]+=.1
    position,_=anchor_errors(projected,shifted,guide,[0,1,49,50])
    assert position==pytest.approx(.1,abs=1e-6)


@pytest.mark.parametrize('case',['jump-205','jump-204','dance-203','dance-204'])
def test_native_guided_correction_hits_targets_and_preserves_inputs(case):
    import torch
    sys.path.insert(0,str(ROOT/'.cache/motion-correction-package'))
    from kimodo.skeleton import SOMASkeleton30
    from kimodo.postprocess import post_process_motion
    from generation_constraints import load_guides
    folder=ROOT/'reports/motion-correction-v1'/case
    raw=dict(np.load(folder/'raw/motion.npz'));guide=dict(np.load(folder/'source-guide.npz'))
    s=SOMASkeleton30();local=s.from_SOMASkeleton77(torch.tensor(raw['local_rot_mats']))[None]
    root=torch.tensor(raw['root_positions'])[None];contacts=torch.tensor(raw['foot_contacts'][:,[0,1,3,4]])[None]
    snapshots=[v.clone() for v in (local,root,contacts)]
    result=post_process_motion(local,root,contacts,s,load_guides(read(folder/'source-constraints.json'),s))
    for before,after in zip(snapshots,(local,root,contacts)):assert torch.equal(before,after)
    expanded=s.output_to_SOMASkeleton77(result)
    n=len(root[0]);p,r=anchor_errors(expanded['local_rot_mats'][0].numpy(),expanded['root_positions'][0].numpy(),guide,[0,1,n-2,n-1])
    assert p<1e-5 and r<.001
