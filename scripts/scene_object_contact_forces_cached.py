"""Reuse complete independently replayed geometry for fresh contact forces.

Run under the same full-posed-body resource profile as the ordinary force
worker. This avoids repeating geometry; it never substitutes a selected patch,
changes a clock/threshold, authenticates a replay author, or approves motion.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from geometry_evidence import load, document
from native_scene_geometry import faces_for
from scene_object_contact_forces import (
    FIELDS, METHODS, SCHEMA, SceneContacts, fields, prepare, assess, surface_evaluate,
)
from strep import ROOT, save, sha256, now

CACHED_METHODS = tuple(dict.fromkeys(METHODS + (
    "geometry_evidence.py", "scene_object_contact_forces_cached.py",
)))


def covered_clock(geometry, clocks):
    """Require exact measured times, including all contact and COM stencils."""
    times = np.asarray(geometry["times_s"], dtype=float)
    for clock in clocks:
        clock = np.asarray(clock, dtype=float)
        if not np.isfinite(clock).all():
            raise ValueError("Finite requested clock required")
        indices = np.searchsorted(times, clock)
        if np.any(indices >= len(times)) or not np.array_equal(times[indices], clock):
            raise ValueError("Cached geometry is missing requested clock times")


def unchanged(bindings):
    if any(sha256(path) != expected for path, expected in bindings.items()):
        raise ValueError("Bound evidence, original input or method changed")


def complete_topology(scene, geometry):
    """Check declared population against the loaded asset's actual indices."""
    expected = {}
    for name, actor in scene.actors.items():
        rig = actor["rig"]
        faces, primitives = faces_for(rig)
        expected[name] = dict(
            vertices=sum(len(p["positions"]) for p in rig.primitives),
            faces=len(faces), primitives=primitives,
            faces_sha256=hashlib.sha256(faces.astype("<i8").tobytes()).hexdigest(),
        )
    if geometry["topology"] != expected:
        raise ValueError("Cached topology differs from the complete loaded assets")


def run(request_path, geometry_folder, replay_path, replay_source, output):
    request_path, geometry_folder, replay_path, replay_source, output = (
        Path(p).resolve() for p in
        (request_path, geometry_folder, replay_path, replay_source, output)
    )
    if output.exists():
        raise FileExistsError(output)
    if not output.is_relative_to(ROOT / "reports") or output == ROOT / "reports":
        raise ValueError("Fresh ignored scene-force output required")
    inputs = {str(request_path): sha256(request_path)}
    request = document(request_path)
    fields(request, FIELDS, "scene force request")
    paths = {}
    for name in ("scene", "surface_policy", "geometry_policy"):
        entry = request[name]
        fields(entry, ("path", "sha256"), "bound scene force input")
        path = (request_path.parent / entry["path"]).resolve()
        if sha256(path) != entry["sha256"]:
            raise ValueError("Bound input changed")
        paths[name] = path
        inputs[str(path)] = entry["sha256"]
    geometry, evidence = load(
        paths["scene"], paths["geometry_policy"], geometry_folder,
        replay_path, replay_source, Path(__file__).resolve().parent,
    )
    scene = SceneContacts(document(paths["scene"]), paths["scene"].parent)
    complete_topology(scene, geometry)
    inputs.update(scene.inputs)
    sp, gp = document(paths["surface_policy"]), document(paths["geometry_policy"])
    prepared = prepare(scene, sp, gp, request, inputs[str(paths["scene"])])
    covered_clock(geometry, [prepared["times"]])
    bindings = {**evidence, **inputs}
    for path in (geometry_folder, *map(Path, bindings)):
        if output.is_relative_to(path) or path.is_relative_to(output):
            raise ValueError("Output must be separate from immutable evidence")
    unchanged(bindings)
    output.mkdir(parents=True)
    copies, methods = {}, {}
    try:
        save(output / "pipeline.json", dict(status="processing", stage="freeze-inputs"))
        for i, (path, expected) in enumerate(inputs.items()):
            dest = output / "inputs" / f"{i}{Path(path).suffix}"
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, dest)
            if sha256(dest) != expected:
                raise ValueError("Input changed while freezing")
            copies[path] = dest.relative_to(output).as_posix()
        for name in CACHED_METHODS:
            source = Path(__file__).resolve().parent / name
            expected = sha256(source)
            if str(source) in bindings and bindings[str(source)] != expected:
                raise ValueError("Geometry evidence method changed before freezing")
            dest = output / "implementation" / name
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, dest)
            if sha256(dest) != expected:
                raise ValueError("Method changed while freezing")
            methods[name] = expected
            bindings[str(source)] = expected
            bindings[str(dest)] = expected
        save(output / "protocol.json", dict(
            schema=SCHEMA, at=now(), inputs_sha256=inputs, input_snapshots=copies,
            methods_sha256=methods, geometry_evidence_sha256=evidence,
            geometry_folder=str(geometry_folder), replay_source=str(replay_source),
            geometry_recomputed=False, external_geometry_archive_required=True,
            quality_approved=False, release_approved=False,
        ))
        save(output / "pipeline.json", dict(status="processing", stage="actual-surface-contacts"))
        surface, arrays = surface_evaluate(scene, sp, inputs[str(paths["scene"])])
        covered_clock(geometry, [v for k, v in arrays.items() if k.endswith("_times_s")])
        np.savez(output / "surface-observations.npz", **arrays)
        save(output / "surface-result.json", surface)
        save(output / "pipeline.json", dict(status="processing", stage="coupled-contact-forces"))
        report = assess(scene, request, prepared, surface, geometry,
                        maximum_actor_pose_queries=sp["maximum_actor_pose_queries"])
        save(output / "assessment.json", report)
        unchanged(bindings)
        unchanged({str(output / copies[p]): h for p, h in inputs.items()})
        scene.check_inputs()
        files = {p.relative_to(output).as_posix(): sha256(p) for p in output.rglob("*")
                 if p.is_file() and p != output / "pipeline.json"}
        result = dict(
            status="complete", at=now(), files_sha256=files,
            geometry_evidence_sha256=evidence, geometry_recomputed=False,
            sampled_geometry_pass=geometry["sampled_conditions_pass"],
            assessed_samples=len(report["assessed_samples"]),
            conditional_force_feasible=report["conditional_force_feasible"],
            coupled_sampled_scene_force_consistent=report["coupled_sampled_scene_force_consistent"],
            quality_approved=False, release_approved=False, training_admitted=False,
        )
        save(output / "result.json", result)
        save(output / "pipeline.json", dict(status="complete", result_sha256=sha256(output / "result.json")))
        return result
    except BaseException as exc:
        save(output / "pipeline.json", dict(status="failed", error_type=type(exc).__name__, error=str(exc),
                                           quality_approved=False, release_approved=False))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("request", "geometry_folder", "replay", "replay_source", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(), threadpool_limits(limits=1):
        print(json.dumps(run(args.request, args.geometry_folder, args.replay, args.replay_source, args.output)))
