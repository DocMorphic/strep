"""Actual export-rounding regression on the original authorized control basis."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_control_neighborhood import refine
from native_mesh_character_fit import MeshCharacterProblem,fit
from strep import read,save,sha256
from test_native_mesh_character_fit import prepared
from test_native_mesh_character_surface import rotation_source

# Retained full-clock proposal: continuous native rows pass; Float32 keys fail.
CONTROL=np.array([-.20086694524818516,.021945461260109992,-.08760420781471928,
    -.24998002728545657,.021897222482170433,-.08760867395331934,
    -.20002362869111118,.021928227584336178,-.08760572010500776,
    .020661418046820847,.24995665410714094,.0624787536794486,
    .020659106701020214,.24995666878125752,.06247966766379278,
    .020657408741139156,.24995666928968693,.062480194639812234])


def test_nearby_existing_controls_repair_actual_export_without_new_permissions(tmp_path):
    path,permission,policy=prepared(tmp_path);rotation_source(tmp_path,path,permission,policy)
    problem=MeshCharacterProblem(permission);before={p:sha256(p) for p in problem.inputs}
    smooth=problem.constraints(CONTROL,problem.worlds(CONTROL,quantized=False))
    assert np.all(smooth[:problem.protected_rows]<=0)
    assert np.any(problem.model(CONTROL)[:problem.protected_rows]>0)
    choice,report=refine(problem,CONTROL,problem.initial,problem.model(problem.initial),.25,tmp_path/'search')
    assert choice is not None and report['probes']<=report['possible_probes']==120
    assert not report['exported'] and not report['quality_approved']
    np.testing.assert_array_equal(choice[9:],CONTROL[9:])
    assert np.max(abs(choice-CONTROL))<.000012 and np.max(abs(choice-problem.initial))<=.25
    _,decoded,_,audits=problem.write(choice,tmp_path/'actual-export')
    assert np.all(decoded[:problem.protected_rows]<=0)
    assert all(a['passed'] and a['strict_edit_caps_pass'] for a in audits.values())
    assert all(sha256(p)==h for p,h in before.items())
    record=read(tmp_path/'search/probes.json')[report['selected_preview_probe']]
    with np.load(tmp_path/'search'/f"probe-{record['index']:04d}.npz") as archive:
        np.testing.assert_array_equal(archive['controls'],choice)
        assert np.all(archive['residual'][:problem.protected_rows]<=0)


def test_refinement_never_changes_frozen_keys_or_control_bounds(tmp_path):
    _,permission,_=prepared(tmp_path);data=read(permission);data['actors']['A']['editable_clip_boundaries']=[];save(permission,data)
    problem=MeshCharacterProblem(permission);value=np.array([-.1,0.,0.])
    _,report=refine(problem,value,problem.initial,problem.model(problem.initial),.25,tmp_path/'search')
    for path in (tmp_path/'search').glob('probe-*.npz'):
        with np.load(path) as archive:control=archive['controls']
        assert np.all(abs(control)<=.25)
        values=problem.edits.values('A',control)
        for entry in problem.edits.actors['A']['tracks']:
            frozen=np.setdiff1d(np.arange(len(entry['source'])),entry['ids'])
            assert len(frozen)>0
            np.testing.assert_array_equal(values[entry['node'],entry['path']][frozen],entry['source'][frozen])
    with pytest.raises(FileExistsError):refine(problem,value,problem.initial,problem.model(problem.initial),.25,tmp_path/'search')
    with pytest.raises(ValueError,match='trust boxes'):
        refine(problem,np.array([-.3,0.,0.]),problem.initial,problem.model(problem.initial),.25,tmp_path/'outside')
    assert not (tmp_path/'outside').exists()


@pytest.mark.parametrize('value',[None,1,'true'])
def test_storage_refinement_is_an_explicit_choice(tmp_path,value):
    with pytest.raises(ValueError,match='storage refinement choice'):
        fit(tmp_path/'missing',tmp_path/'missing',tmp_path/'output',refine_storage=value)
