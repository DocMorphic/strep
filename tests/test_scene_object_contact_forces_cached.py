"""Real tiny skin/force queries; replay receipt is a test fixture, not an audit."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import native_scene_geometry as geometry
import scene_object_contact_forces_cached as subject
from test_scene_object_contact_forces import fixture, prepared
from strep import read, save, sha256


def cache(tmp_path, monkeypatch, intersecting=False):
    paths = fixture(tmp_path, intersecting=intersecting)
    path, request, scene_path, sp, gp = paths
    scene, prep = prepared(paths)
    _, contacts = scene.evaluate()
    policy = read(gp)
    policy["clock"]["times_s"] = np.unique(np.concatenate(
        [prep["times"]] + [v for k, v in contacts.items() if k.endswith("_times_s")]
    )).tolist()
    save(gp, policy)
    request["geometry_policy"]["sha256"] = sha256(gp)
    save(path, request)
    folder = tmp_path / "archive"
    result = geometry.run(scene_path, gp, folder)
    auditor = tmp_path / "synthetic_replay.py"
    auditor.write_text("# Test-only receipt fixture; no independent numeric replay.\n")
    population = {k: result[k] for k in ("topology", "times_s", "limits", "declared_planes",
                                         "sampled_conditions_pass", "observations_sha256")}
    population["objects"] = list(read(scene_path)["objects"])
    replay = tmp_path / "replay.json"
    save(replay, dict(schema="strep-full-geometry-replay-v1", status="complete", validation_passed=True,
                     complete_population_replayed=True, result_sha256=sha256(folder / "result.json"),
                     auditor_sha256=sha256(auditor), observations_sha256=result["observations_sha256"],
                     population=population, sampled_geometry_pass=result["sampled_conditions_pass"]))
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    return paths, folder, replay, auditor


@pytest.mark.parametrize("intersecting", [False, True])
def test_fresh_forces_retain_complete_geometry_failure(tmp_path, monkeypatch, intersecting):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch, intersecting)
    archive_hash = sha256(folder / "observations.npz")
    def forbidden(*args, **kwargs):
        raise AssertionError("Complete geometry must not be recomputed")
    monkeypatch.setattr(geometry, "evaluate_to_archive", forbidden)
    output = tmp_path / "reports/forces"
    result = subject.run(paths[0], folder, replay, auditor, output)
    assert result["conditional_force_feasible"] == 3
    assert result["coupled_sampled_scene_force_consistent"] == (0 if intersecting else 3)
    assert result["sampled_geometry_pass"] is (not intersecting)
    assert result["geometry_recomputed"] is False
    assert not result["quality_approved"] and not result["release_approved"]
    assert sha256(folder / "observations.npz") == archive_hash
    for name, expected in result["files_sha256"].items():
        assert sha256(output / name) == expected
    with pytest.raises(FileExistsError):
        subject.run(paths[0], folder, replay, auditor, output)


def test_uniform_force_clock_must_exist_before_surface_work(tmp_path, monkeypatch):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch)
    request = read(paths[0]); request["sample_count"] = 8
    request["phases"][0]["end_frame_exclusive"] = 8
    save(paths[0], request)
    def forbidden(*args, **kwargs):
        raise AssertionError("Missing geometry must be caught before skin queries")
    monkeypatch.setattr(subject, "surface_evaluate", forbidden)
    output = tmp_path / "reports/forces"
    with pytest.raises(ValueError, match="missing requested clock"):
        subject.run(paths[0], folder, replay, auditor, output)
    assert not output.exists()


def test_surface_clock_missing_is_not_silently_subsampled(tmp_path, monkeypatch):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch)
    original = subject.surface_evaluate
    def extra_time(*args, **kwargs):
        report, arrays = original(*args, **kwargs)
        arrays["contact_0_times_s"] = np.array([.123456789])
        return report, arrays
    monkeypatch.setattr(subject, "surface_evaluate", extra_time)
    output = tmp_path / "reports/forces"
    with pytest.raises(ValueError, match="missing requested clock"):
        subject.run(paths[0], folder, replay, auditor, output)
    assert read(output / "pipeline.json")["status"] == "failed"
    assert not (output / "assessment.json").exists()


def test_changed_evidence_after_force_queries_cannot_complete(tmp_path, monkeypatch):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch)
    original = subject.assess
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        replay.write_bytes(replay.read_bytes() + b" ")
        return result
    monkeypatch.setattr(subject, "assess", changed)
    output = tmp_path / "reports/forces"
    with pytest.raises(ValueError, match="Bound evidence"):
        subject.run(paths[0], folder, replay, auditor, output)
    assert read(output / "pipeline.json")["status"] == "failed"
    assert (output / "assessment.json").exists() and not (output / "result.json").exists()


def test_method_binding_cannot_be_overwritten_during_freezing(tmp_path, monkeypatch):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch)
    source = Path(subject.__file__).parent / "native_scene_geometry.py"
    original = subject.sha256
    calls = 0
    def changed_hash(path):
        nonlocal calls
        if Path(path) == source:
            calls += 1
            if calls >= 2:
                return "1" * 64
        if Path(path) == output / "implementation" / source.name:
            return "1" * 64
        return original(path)
    # Simulate a consistently changed live/frozen method hash without editing
    # any implementation imported by the running worker.
    monkeypatch.setattr(subject, "sha256", changed_hash)
    output = tmp_path / "reports/forces"
    with pytest.raises(ValueError, match="method changed before freezing"):
        subject.run(paths[0], folder, replay, auditor, output)
    assert read(output / "pipeline.json")["status"] == "failed"
    assert not (output / "assessment.json").exists()


@pytest.mark.parametrize("fault", ["faces", "vertices", "indices", "primitives"])
def test_positive_but_partial_resealed_topology_fails_before_skin_queries(tmp_path, monkeypatch, fault):
    paths, folder, replay, auditor = cache(tmp_path, monkeypatch)
    result = read(folder / "result.json")
    topology = result["topology"]["A"]
    if fault in ("faces", "vertices"):
        topology[fault] -= 1
    elif fault == "indices":
        topology["faces_sha256"] = "0" * 64
    else:
        topology["primitives"].clear()
    save(folder / "result.json", result)
    receipt = read(replay)
    receipt["population"]["topology"] = result["topology"]
    receipt["result_sha256"] = sha256(folder / "result.json")
    save(replay, receipt)
    def forbidden(*args, **kwargs):
        raise AssertionError("Partial topology must be caught before skin queries")
    monkeypatch.setattr(subject, "surface_evaluate", forbidden)
    output = tmp_path / "reports/forces"
    with pytest.raises(ValueError, match="complete loaded assets"):
        subject.run(paths[0], folder, replay, auditor, output)
    assert not output.exists()


@pytest.mark.parametrize("clock", [[0., .123], [0., float("nan")], [1.1]])
def test_no_clock_interpolation_or_nonfinite_times(clock):
    with pytest.raises(ValueError):
        subject.covered_clock({"times_s": [0., .5, 1.]}, [clock])
