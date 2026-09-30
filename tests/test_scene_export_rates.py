import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_scene_export_rates import stages_summary, rounded_world
from test_timed_rotation_edit import fixture, model
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb


def test_stages_distinguish_nonlinearity_from_rounding_without_resetting_caps():
    source = np.array([[1., 0, 0], [0., 2., 0]])
    affine = source.copy(); affine[:, 0] -= .001
    nonlinear = affine.copy(); nonlinear[0, 0] += .002
    rounded = nonlinear.copy(); rounded[1, 1] += .003
    summary = stages_summary(dict(source=source, affine=affine, nonlinear=nonlinear, decoded=rounded), [1., 2.], ['speed', 'angular_acceleration'])
    assert summary['source']['speed']['failures'] == 0
    assert summary['affine']['angular_acceleration']['failures'] == 0
    assert summary['nonlinear']['speed']['failures'] == 1
    assert summary['nonlinear']['angular_acceleration']['failures'] == 0
    assert summary['decoded']['angular_acceleration']['failures'] == 1
    assert summary['decoded']['angular_acceleration']['maximum_vector_change_from_previous'] == pytest.approx(.003)


@pytest.mark.parametrize('fault', ['nan', 'shape', 'negative_cap', 'negative_tolerance'])
def test_invalid_stage_evidence_rejected(fault):
    values = np.zeros((2, 3)); caps = np.ones(2); tolerance = 1e-5
    if fault == 'nan': values[0, 0] = np.nan
    if fault == 'shape': values = values[:1]
    if fault == 'negative_cap': caps[0] = -1
    if fault == 'negative_tolerance': tolerance = -1
    with pytest.raises(ValueError): stages_summary(dict(decoded=values), caps, ['speed']*2, tolerance)


def test_rounded_batch_reconstructs_actual_export_and_preserves_zero(tmp_path):
    doc, binary = fixture(); edit = model(doc, binary)
    np.testing.assert_allclose(rounded_world(edit, np.zeros(edit.size)), edit.source_world, atol=1e-12, rtol=0)
    controls = np.linspace(-.012, .017, edit.size); output = tmp_path/'rounded.glb'; edit.export(controls, output)
    doc, binary = read_glb(output); sampler = AnimationSampler(doc, binary, 0)
    decoded = np.array([sampler.sample(t) for t in edit.times])
    np.testing.assert_allclose(rounded_world(edit, controls), decoded, atol=1e-12, rtol=0)
    assert np.abs(edit.world(controls)-decoded).max() > 1e-10
