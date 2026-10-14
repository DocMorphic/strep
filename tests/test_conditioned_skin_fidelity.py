"""Original-reference skin checks cannot be replaced by export-relative checks."""
import copy,sys
from pathlib import Path
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_conditioned_skin_fidelity import compare
from test_native_component_storage import fixture


def assets(tmp_path):
    base,*_=fixture(tmp_path);actor=base.scene.actors['A'];return actor['rig'],actor['sampler']


def test_same_skin_at_exact_clock_matches_original_and_counts_every_vertex(tmp_path):
    rig,sampler=assets(tmp_path);times=np.array([0.,.125,.9,2.])
    report,arrays=compare(rig,rig,0,(np.zeros(3),np.eye(3)),times,lambda t:rig.vertices(sampler.sample(t)))
    assert report['original_reference_fidelity_pass'] and report['samples']==4
    assert report['vertices']==len(rig.vertices(sampler.sample(0)))
    assert report['tolerance_m']==1e-4 and not report['quality_approved'] and not report['release_approved']
    np.testing.assert_array_equal(arrays['imported_original_errors_m'],np.zeros(4))


def test_export_relative_match_cannot_hide_original_reference_drift(tmp_path):
    rig,sampler=assets(tmp_path)
    def shifted(t):return rig.vertices(sampler.sample(t))+np.array([.0002,0,0])
    report,arrays=compare(rig,rig,0,(np.zeros(3),np.eye(3)),[0.,.5,2.],shifted)
    assert not report['original_reference_fidelity_pass'] and report['imported_original_error_m']>report['tolerance_m']
    assert len(arrays['imported_original_errors_m'])==3 and not report['release_approved']


@pytest.mark.parametrize('fault',['short','nan','clock','animation'])
def test_missing_population_changed_animation_and_invalid_clock_reject(tmp_path,fault):
    rig,sampler=assets(tmp_path);other=copy.deepcopy(rig);times=[0.,.5,2.]
    def observed(t):
        value=rig.vertices(sampler.sample(t))
        if fault=='short':value=value[:-1]
        elif fault=='nan':value[0,0]=np.nan
        return value
    if fault=='clock':times=[0.,.5,.5]
    if fault=='animation':other.document['animations'][0]['name']='Changed'
    with pytest.raises(ValueError):compare(rig,other,0,(np.zeros(3),np.eye(3)),times,observed)
