"""Complete triangle pairs, barycentric containment and scalar proposal data."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture,policy
from native_scene_contacts import SceneContacts
from native_partner_surface_rows import build,separation_axis
from native_surface_lift import lift
from triangle_crossing import classify
from strep import save,sha256


def scene_fixture(tmp_path):
    source,path,spec=closed_fixture(tmp_path);spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement'].update(translation_m=[.1,.1,.07],rotation_xyzw=Rotation.from_euler('y',40,degrees=True).as_quat().tolist())
    save(path,spec);return SceneContacts(spec,tmp_path),policy(path),sha256(path)


def test_triangle_axis_and_nine_scalar_pairs_produce_real_separation():
    left=np.array([[0.,0,0],[1,0,0],[0,1,0]]);right=np.array([[.2,.2,-.3],[.2,.2,.3],[.6,.2,0.]])
    assert classify(left,right)['kind']=='proper_crossing'
    n,gap=separation_axis(left,right);assert abs(np.linalg.norm(n)-1)<1e-12
    pair_gaps=(left[:,None]-right[None])@n;assert pair_gaps.min()==pytest.approx(gap)
    shifted=left+(.001-gap)*n
    assert ((shifted[:,None]-right[None])@n).min()>=.001-1e-14
    assert classify(shifted,right)['kind']=='disjoint'


def test_coplanar_disjoint_triangles_have_positive_separation_axis():
    left=np.array([[0.,0,0],[1,0,0],[0,1,0]]);n,gap=separation_axis(left,left+[2.,0,0])
    assert gap>0 and abs(np.linalg.norm(n)-1)<1e-12


def test_complete_surface_records_and_containment_generate_nontruncated_rows(tmp_path):
    scene,p,digest=scene_fixture(tmp_path);result=build(scene,p,digest)
    assert result.report['complete_triangle_populations']=={'A':12,'B':12}
    records=sum(q['complete_surface_records'] for s in result.report['samples'] for q in s['pairs'])
    triangle=[r for r in result.rows if r['kind']=='triangle-separation'];assert len(triangle)==9*records
    inside=[r for r in result.rows if r['kind']=='penetrating-vertex'];assert inside
    gaps=result.gaps();assert len(gaps)==len(result.rows) and np.isfinite(gaps).all()
    for i,r in enumerate(result.rows):
        assert abs(np.linalg.norm(r['normal_world'])-1)<1e-9
        if r['kind']=='penetrating-vertex':
            assert gaps[i]<0 and abs(sum(r['right']['weights'])-1)<1e-12
            assert min(r['right']['weights'])>=0
    assert not result.report['quality_approved'] and not result.report['release_approved']


def test_full_population_requirement_and_row_budget_reject_incomplete_evidence(tmp_path):
    scene,p,digest=scene_fixture(tmp_path)
    with pytest.raises(ValueError,match='resource budget'):build(scene,p,digest,maximum_rows=1)
    result=build(scene,p,digest)
    with pytest.raises(ValueError,match='population'):result.gaps(lambda *args:np.zeros((1,3)))


@pytest.mark.parametrize('gaps,trust',[([-2.,-.1,.3],.02),([2.,-3.,4.],.3)])
def test_scalar_lift_matches_direct_affine_halfspaces_everywhere_in_trust_box(gaps,trust):
    jac=np.array([[1.,2],[-3.,4],[5,-6]]);x=np.zeros(2);lo=-np.ones(2);hi=np.ones(2)
    rows,j,report=lift(gaps,jac,x,lo,hi,trust)
    for delta in np.random.default_rng(3).uniform(-trust,trust,(100,2)):
        expected=(.0005-(np.asarray(gaps)+jac@delta))/.005
        np.testing.assert_allclose(rows.residual(j,delta),expected,atol=2e-12,rtol=1e-12)
    assert report['trust']==trust


def test_invalid_triangle_and_scalar_models_fail():
    with pytest.raises(ValueError):separation_axis(np.zeros((3,3)),np.eye(3))
    with pytest.raises(ValueError):lift([0.],[[1.]], [0.],[-1.],[1.],True)
