"""Bind a complete, independently replayed scene archive to a later stage.

This checks provenance and population coverage. It does not compute geometry,
authenticate the author of a replay receipt, or grant animation quality.
"""
import hashlib
import json
import math
from pathlib import Path
from itertools import combinations


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def document(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Evidence metadata exceeds the bounded reader")
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Nonfinite evidence metadata")
        return result
    def nonfinite(value):
        raise ValueError("Nonfinite evidence metadata")
    return json.loads(path.read_bytes(), parse_float=finite_float, parse_constant=nonfinite)


def inside(root, relative):
    root = Path(root).resolve()
    value = Path(relative)
    target = (root / value).resolve()
    if value.is_absolute() or not target.is_relative_to(root):
        raise ValueError("Frozen evidence path escapes its archive")
    return target


def load(scene_path, policy_path, folder, replay_path, replay_source, method_root):
    """Return full geometry only after checking every declared binding/scope."""
    scene_path, policy_path, folder, replay_path, replay_source, method_root = (
        Path(p).resolve() for p in
        (scene_path, policy_path, folder, replay_path, replay_source, method_root)
    )
    result_path = folder / "result.json"
    result = document(result_path)
    scene, policy, replay = map(document, (scene_path, policy_path, replay_path))
    if (result.get("schema") != "strep-native-scene-geometry-result-v1"
            or policy.get("schema") != "strep-native-scene-geometry-v1"
            or result.get("status") != "complete"
            or replay.get("schema") != "strep-full-geometry-replay-v1"
            or replay.get("status") != "complete"
            or replay.get("validation_passed") is not True
            or replay.get("complete_population_replayed") is not True):
        raise ValueError("Completed full-population independent replay required")
    if (result.get("contacts_sha256") != digest(scene_path)
            or result.get("policy_sha256") != digest(policy_path)
            or policy.get("contacts_sha256") != digest(scene_path)
            or replay.get("result_sha256") != digest(result_path)
            or replay.get("auditor_sha256") != digest(replay_source)):
        raise ValueError("Scene, policy, result or replay source binding changed")
    times = result.get("times_s", [])
    if (len(times) < 2
            or any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
            or any(b <= a for a, b in zip(times, times[1:]))
            or times[0] != 0 or times[-1] != scene["duration_s"]):
        raise ValueError("Complete ordered clip clock required")
    if (result["clock_mode"] != policy["clock"]["mode"]
            or result["limits"] != policy["limits"]
            or result["declared_planes"] != list(policy["planes"])):
        raise ValueError("Geometry policy coverage changed")
    if policy["clock"]["mode"] == "explicit" and times != policy["clock"]["times_s"]:
        raise ValueError("Explicit geometry clock changed")
    if not set(policy["clock"]["times_s"]).issubset(times):
        raise ValueError("Mandatory policy times are missing")
    population = dict(
        topology=result["topology"], objects=list(scene["objects"]), times_s=times,
        limits=result["limits"], declared_planes=list(policy["planes"]),
        sampled_conditions_pass=result["sampled_conditions_pass"],
        observations_sha256=result["observations_sha256"],
    )
    if replay.get("population") != population or set(result["topology"]) != set(scene["actors"]):
        raise ValueError("Replay does not cover the entire scene population")
    for actor in result["topology"].values():
        if any(type(actor[key]) is not int or actor[key] <= 0 for key in ("vertices", "faces")):
            raise ValueError("Complete nonempty actor topology required")
    samples = result["samples"]
    if len(samples) != len(times):
        raise ValueError("Missing complete-clock geometry samples")
    actors, objects = list(scene["actors"]), list(scene["objects"])
    expected_objects = {(a, o) for a in actors for o in objects}
    expected_pairs = {tuple(sorted(pair)) for pair in combinations(actors, 2)}
    expected_planes = {(a, p) for a in actors for p in policy["planes"]}
    for time, sample in zip(times, samples):
        def complete(rows, keys, expected):
            observed = [keys(row) for row in rows]
            if len(observed) != len(set(observed)) or set(observed) != expected:
                raise ValueError("Missing or duplicated scene geometry conditions")
        if sample["time_s"] != time or type(sample["passed"]) is not bool:
            raise ValueError("Geometry sample identity or decision changed")
        if (set(sample["volumes"]) != set(actors)
                or set(sample["degenerate_faces"]) != set(actors)):
            raise ValueError("Missing actor volume or degeneracy records")
        complete(sample["actor_objects"], lambda r: (r["actor"], r["object"]), expected_objects)
        complete(sample["actor_pairs"], lambda r: tuple(sorted(r["actors"])), expected_pairs)
        complete(sample["world_planes"], lambda r: (r["actor"], r["plane"]), expected_planes)
        conditions = sample["actor_objects"] + sample["actor_pairs"] + sample["world_planes"]
        if (type(sample["conditions_available"]) is not bool
                or sample["conditions_available"] != bool(conditions)
                or any(type(row["passed"]) is not bool for row in conditions)
                or sample["passed"] != bool(conditions and all(row["passed"] for row in conditions)
                                             and not any(sample["degenerate_faces"].values()))):
            raise ValueError("Geometry condition decisions are inconsistent")
    if (type(result["sampled_conditions_pass"]) is not bool
            or result["sampled_conditions_pass"] != all(s["passed"] for s in samples)
            or replay["sampled_geometry_pass"] != result["sampled_conditions_pass"]):
        raise ValueError("Full-clock geometry outcome changed")
    archive = folder / "observations.npz"
    receipt = Path(str(archive) + ".receipt.json")
    archive_hash = digest(archive)
    if (archive_hash != result["observations_sha256"]
            or digest(receipt) != result["observation_receipt_sha256"]
            or document(receipt)["archive_sha256"] != archive_hash
            or replay.get("observations_sha256") != archive_hash):
        raise ValueError("Complete observation archive changed")
    snapshots = result.get("source_snapshots", {})
    methods = result.get("implementation_sha256", {})
    if not snapshots or not methods:
        raise ValueError("Frozen source and method populations required")
    normalized = {Path(path).resolve(): value for path, value in snapshots.items()}
    assets = {
        (scene_path.parent / actor["glb"]).resolve(): actor["sha256"]
        for actor in scene["actors"].values()
    }
    if not ({scene_path, policy_path} | set(assets)).issubset(normalized):
        raise ValueError("Scene, policy or actor source snapshot is missing")
    if any(normalized[path]["sha256"] != expected for path, expected in assets.items()):
        raise ValueError("Actor asset identity changed")
    bindings = {
        str(p): digest(p) for p in
        (scene_path, policy_path, result_path, replay_path, replay_source, archive, receipt)
    }
    for original, snapshot in snapshots.items():
        frozen = inside(folder, snapshot["path"])
        if digest(original) != snapshot["sha256"] or digest(frozen) != snapshot["sha256"]:
            raise ValueError("Original or frozen scene input changed")
        bindings[str(Path(original).resolve())] = snapshot["sha256"]
        bindings[str(frozen)] = snapshot["sha256"]
    for name, expected in methods.items():
        live, frozen = inside(method_root, name), inside(folder / "implementation", name)
        if live.suffix != ".py" or digest(live) != expected or digest(frozen) != expected:
            raise ValueError("Live or frozen geometry method changed")
        bindings[str(live)] = bindings[str(frozen)] = expected
    return result, bindings
