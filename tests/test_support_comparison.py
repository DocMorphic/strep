import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pytest
from compare_support_reference import comparable


def inputs():
    spec={'frames':150,'limits':{'root_horizontal_m':.04},'provenance':'original'}
    request=dict(method='support',input_glb_sha256='source',native_motion_sha256='motion',native_skin_sha256='skin',
        targets_m={'Left':[0.]},raw_native_heights_m={'Left':[-.001]},support={'intervals':[{'start':2,'end':9}]},support_weight=40.,max_sweeps=6)
    new_spec=copy.deepcopy(spec);new_spec['provenance']='revised description'
    new=copy.deepcopy(request);new.update(method='support_reference',horizontal_reference_weight='faded')
    return spec,new_spec,request,new


def test_comparison_allows_only_declared_method_and_provenance_change():
    values=inputs();comparable(*values)
    values[1]['limits']['root_horizontal_m']=.05
    with pytest.raises(ValueError):comparable(*values)


@pytest.mark.parametrize('key,value',[('input_glb_sha256','other'),('max_sweeps',7),('support',{'intervals':[]}),('support_weight',60.)])
def test_comparison_rejects_unmatched_sources_guides_and_solver_budget(key,value):
    values=inputs();values[3][key]=value
    with pytest.raises(ValueError):comparable(*values)
