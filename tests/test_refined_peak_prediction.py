import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_refined_peak_prediction import selected
from strep import save,sha256


@pytest.mark.parametrize('fault',[None,'incomplete','changed','duplicates','missing_step','failed','shape'])
def test_peak_diagnostic_requires_bound_completed_subset_proposal(tmp_path,fault):
    save(tmp_path/'request.json',dict(inputs={}))
    row=dict(name='probe',step=[0.,0.,0.],solver=dict(proposal_hard_checks=True))
    if fault=='missing_step':row['step']=None
    if fault=='failed':row['solver']['proposal_hard_checks']=False
    if fault=='shape':row['step']=[0.,0.]
    save(tmp_path/'variants.json',[row,row] if fault=='duplicates' else [row])
    save(tmp_path/'result.json',dict(status='processing' if fault=='incomplete' else 'complete',request_sha256=sha256(tmp_path/'request.json'),variants_sha256=sha256(tmp_path/'variants.json')))
    if fault=='changed':save(tmp_path/'request.json',{})
    if fault is None:assert selected(tmp_path,'probe')[1]==row
    else:
        with pytest.raises(ValueError):selected(tmp_path,'probe')
