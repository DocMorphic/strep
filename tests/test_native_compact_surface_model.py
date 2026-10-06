"""Original constraints remain; nonlinear guide reduction does not certify a step."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_compact_surface_model as compact
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_scene_norms import NormRows,rows as native_rows
from native_surface_model import include_times
from test_native_partner_surface_rows import scene_fixture


def test_actual_model_preserves_all_native_vectors_caps_scales_and_full_guides(tmp_path):
    scene,p,digest=scene_fixture(tmp_path)
    permission=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors={'A':dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)})
    problem=SceneProblem(scene,SceneEdits(permission,scene,digest));include_times(problem,p['clock']['times_s'])
    before=native_rows(problem,problem.initial)
    result,jac,guides,report=compact.model(problem,problem.initial,scene,p,digest,.02)
    hard=len(before.caps)
    np.testing.assert_array_equal(result.vectors[:hard],before.vectors)
    np.testing.assert_array_equal(result.caps[:hard],before.caps);np.testing.assert_array_equal(result.scales[:hard],before.scales)
    np.testing.assert_allclose(result.residual()[:hard],problem.model(problem.initial),atol=1e-9,rtol=0)
    np.testing.assert_allclose(result.residual()[hard:],(.0005-guides.gaps())/.005,atol=1e-10,rtol=0)
    assert jac.shape==(3*len(result.caps),problem.size) and report['surface_rows']==len(guides.rows)
    assert len(report['surface_differences'])==problem.size
    assert not report['affine_nine_pair_equivalence'] and not report['quality_approved'] and not report['release_approved']


@pytest.mark.parametrize('changed_caps',[False,True])
def test_decoded_anchor_is_bound_to_original_native_caps(monkeypatch,changed_caps):
    old=NormRows([[0.,0,0]],[1.],[1.]);anchor=NormRows([[.1,0,0]],[2. if changed_caps else 1.],[1.]);jac=sparse.csr_matrix((3,1))
    monkeypatch.setattr(compact,'linearize',lambda *a,**kw:(old,jac,{}));monkeypatch.setattr(compact,'native_rows',lambda *a:anchor)
    monkeypatch.setattr(compact,'build',lambda *a,**kw:SimpleNamespace(rows=[],report={}))
    problem=SimpleNamespace(edits=SimpleNamespace(controls=lambda x:np.asarray(x)))
    if changed_caps:
        with pytest.raises(ValueError,match='caps'):compact.model(problem,[0.],None,None,None,.02,decoded_worlds={})
    else:
        result,_,_,report=compact.model(problem,[0.],None,None,None,.02,decoded_worlds={})
        np.testing.assert_array_equal(result.vectors,anchor.vectors);np.testing.assert_array_equal(result.caps,old.caps)
        assert report['surface_rows']==0


@pytest.mark.parametrize('settings',[dict(trust=True),dict(trust=.021),dict(step=True),dict(step=0),dict(maximum_rows=100001),dict(clearance=-.1),dict(difference_scheme='guess')])
def test_invalid_model_settings_reject_before_native_or_surface_query(settings):
    settings={'trust':.02,**settings}
    with pytest.raises(ValueError):compact.model(None,None,None,None,None,**settings)
