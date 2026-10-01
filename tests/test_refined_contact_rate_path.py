import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from refined_contact_rate_path import RefinedContactRatePath
from contact_rate_path import ContactRatePath
from test_native_wrist_retraction import fixture
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from rotation_rate_support import rate_support
from sampled_motion_caps import features, measures


def models():
    doc, binary = fixture(); times = np.unique(np.r_[np.linspace(0, 3, 121), 1.4])
    args = (doc, binary, ['Upper','Elbow','Wrist'], times, [0.,3.], [], 1.4, (doc,binary))
    return ContactRatePath(*args), RefinedContactRatePath(*args)


@pytest.mark.parametrize('quantize', [False, True])
def test_refinement_contains_old_control_space(quantize):
    coarse, fine = models(); x = np.linspace(-.035,.042,coarse.size)
    lifted = fine.lift_coarse(x)
    assert fine.size == 2*coarse.size == 72
    np.testing.assert_allclose(coarse.world(x,quantize),fine.world(lifted,quantize),atol=1e-12,rtol=0)
    assert np.max(np.abs(lifted)) <= np.max(np.abs(x))


def test_new_controls_preserve_contact_native_export_and_untouched_keys(tmp_path):
    _, fine = models(); x = np.random.default_rng(119).uniform(-.04,.04,fine.size)
    before = fine.world(np.zeros(fine.size),True); world = fine.world(x,True)
    event = np.searchsorted(fine.model.times,1.4)
    np.testing.assert_allclose(world[event],before[event],atol=1e-7,rtol=0)
    path = tmp_path/'refined.glb'; fine.export(x,path); doc,binary = read_glb(path); reader=AnimationSampler(doc,binary,0)
    np.testing.assert_allclose(world,np.array([reader.sample(t) for t in fine.model.times]),atol=1e-12,rtol=0)
    for entry in fine.model.entries:
        q=fine.quaternions(x,True)[entry['node']]; frozen=np.ones(len(q),bool);frozen[entry['ids']]=False
        np.testing.assert_array_equal(q[frozen],entry['source'][frozen])
    np.testing.assert_array_equal(world[[0,-1]],before[[0,-1]])
    assert np.max(np.abs(world-before)) > .001


def test_local_extra_knot_and_rate_support():
    _,fine=models();x=np.zeros(fine.size);x[0]=.035
    q=fine.quaternions(x);entry=fine.model.entries[0];lock=fine.locks[0]
    active=(entry['clock']>fine.knots[0])&(entry['clock']<fine.knots[2]);active[lock['left']:lock['left']+2]=True
    np.testing.assert_array_equal(q[entry['node']][~active],entry['source'][~active])
    times=np.linspace(0,3,121);ids=np.searchsorted(fine.model.times,times);joints=list(range(len(fine.model.parents)))
    masks=rate_support(fine.model.parents,joints,fine.model.entries,times)
    a=measures(features(fine.world(np.zeros(fine.size),True)[ids],joints),.025)
    b=measures(features(fine.world(x,True)[ids],joints),.025)
    for first,second,mask in zip(a,b,masks):np.testing.assert_allclose(first[~mask],second[~mask],atol=1e-10,rtol=0)


def test_zero_and_invalid_controls():
    _,fine=models()
    for entry in fine.model.entries:np.testing.assert_array_equal(fine.quaternions(np.zeros(fine.size),True)[entry['node']],entry['source'])
    with pytest.raises(ValueError):fine.lift_coarse(np.zeros(fine.size))
    with pytest.raises(ValueError):fine.quaternions(np.full(fine.size,np.nan))
    x=np.zeros(fine.size);x[fine.components-3]=np.pi
    with pytest.raises(ValueError,match='Ambiguous'):fine.quaternions(x)
