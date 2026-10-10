"""Complete-population cache integrity; these fixtures are not real geometry."""
import copy
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from geometry_evidence import digest, load


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf8")


@pytest.fixture
def evidence(tmp_path):
    folder = tmp_path / "cache"; folder.mkdir()
    methods = tmp_path / "methods"; methods.mkdir()
    (folder / "implementation").mkdir()
    original = tmp_path / "character.bin"; original.write_bytes(b"synthetic test asset")
    frozen = folder / "character.bin"; frozen.write_bytes(original.read_bytes())
    source = methods / "producer.py"; source.write_text("# synthetic method fixture")
    (folder / "implementation/producer.py").write_bytes(source.read_bytes())
    auditor = tmp_path / "auditor.py"; auditor.write_text("# synthetic replay fixture")
    scene_path, policy_path = tmp_path / "scene.json", tmp_path / "policy.json"
    scene = dict(duration_s=1., actors={
        a: dict(glb=str(original), sha256=digest(original)) for a in ("A", "B")
    }, objects={"prop": {}, "other": {}})
    policy = dict(schema="strep-native-scene-geometry-v1", contacts_sha256="",
                  clock=dict(mode="explicit", times_s=[0., 1.]),
                  limits=dict(penetration_m=.005), planes={"floor": {}})
    save(scene_path, scene); policy["contacts_sha256"] = digest(scene_path); save(policy_path, policy)
    for path in (scene_path, policy_path):
        (folder / path.name).write_bytes(path.read_bytes())
    archive = folder / "observations.npz"; archive.write_bytes(b"synthetic archive fixture")
    receipt = folder / "observations.npz.receipt.json"
    save(receipt, dict(archive_sha256=digest(archive)))
    topology = {a: dict(vertices=3, faces=1) for a in scene["actors"]}
    samples = []
    for time in [0., 1.]:
        samples.append(dict(
            time_s=time, passed=True, conditions_available=True,
            volumes={a: {} for a in scene["actors"]},
            degenerate_faces={a: [] for a in scene["actors"]},
            actor_objects=[dict(actor=a, object=o, passed=True)
                           for a in scene["actors"] for o in scene["objects"]],
            actor_pairs=[dict(actors=["A", "B"], passed=True)],
            world_planes=[dict(actor=a, plane="floor", passed=True) for a in scene["actors"]],
        ))
    result = dict(
        schema="strep-native-scene-geometry-result-v1", status="complete",
        contacts_sha256=digest(scene_path), policy_sha256=digest(policy_path),
        times_s=[0., 1.], clock_mode="explicit", limits=policy["limits"],
        declared_planes=["floor"], topology=topology, samples=samples,
        sampled_conditions_pass=True, observations_sha256=digest(archive),
        observation_receipt_sha256=digest(receipt),
        source_snapshots={
            str(p): dict(path=p.name, sha256=digest(p))
            for p in (original, scene_path, policy_path)
        },
        implementation_sha256={"producer.py": digest(source)},
    )
    replay_path = tmp_path / "replay.json"
    def reseal():
        save(folder / "result.json", result)
        population = {k: copy.deepcopy(result[k]) for k in
                      ("topology", "times_s", "limits", "declared_planes",
                       "sampled_conditions_pass", "observations_sha256")}
        population["objects"] = list(scene["objects"])
        replay = dict(schema="strep-full-geometry-replay-v1", status="complete",
                      validation_passed=True, complete_population_replayed=True,
                      result_sha256=digest(folder / "result.json"), auditor_sha256=digest(auditor),
                      observations_sha256=digest(archive), population=population,
                      sampled_geometry_pass=result["sampled_conditions_pass"])
        save(replay_path, replay)
    reseal()
    return dict(folder=folder, scene_path=scene_path, policy_path=policy_path,
                replay_path=replay_path, replay_source=auditor, method_root=methods), result, reseal


def test_full_scene_binding_and_failed_geometry_are_preserved(evidence):
    args, result, reseal = evidence
    checked, bindings = load(**args)
    assert checked["sampled_conditions_pass"] and len(bindings) == 13
    result["samples"][0]["actor_objects"][0]["passed"] = False
    result["samples"][0]["passed"] = False
    result["sampled_conditions_pass"] = False
    reseal()
    assert load(**args)[0]["sampled_conditions_pass"] is False


@pytest.mark.parametrize("fault", ["object", "pair", "plane", "duplicate", "volume",
                                  "time", "decision", "global", "empty-topology"])
def test_coherently_resealed_partial_populations_still_fail(evidence, fault):
    args, result, reseal = evidence
    sample = result["samples"][0]
    if fault == "object": sample["actor_objects"].pop()
    elif fault == "pair": sample["actor_pairs"].clear()
    elif fault == "plane": sample["world_planes"].pop()
    elif fault == "duplicate": sample["actor_objects"].append(copy.deepcopy(sample["actor_objects"][0]))
    elif fault == "volume": sample["volumes"].pop("B")
    elif fault == "time": result["times_s"].pop(); result["samples"].pop()
    elif fault == "decision": sample["actor_pairs"][0]["passed"] = False
    elif fault == "global": result["sampled_conditions_pass"] = False
    elif fault == "empty-topology": result["topology"]["B"]["faces"] = 0
    reseal()
    with pytest.raises(ValueError): load(**args)


@pytest.mark.parametrize("fault", ["scene", "policy", "archive", "receipt",
                                  "original", "snapshot", "method", "auditor", "replay-scope"])
def test_changed_inputs_archives_or_provenance_fail(evidence, fault):
    args, result, reseal = evidence
    path = {
        "scene": args["scene_path"], "policy": args["policy_path"],
        "archive": args["folder"] / "observations.npz",
        "receipt": args["folder"] / "observations.npz.receipt.json",
        "original": Path(next(iter(result["source_snapshots"]))),
        "snapshot": args["folder"] / "character.bin",
        "method": args["method_root"] / "producer.py", "auditor": args["replay_source"],
    }.get(fault)
    if fault == "replay-scope":
        replay = json.loads(args["replay_path"].read_bytes())
        replay["complete_population_replayed"] = False
        save(args["replay_path"], replay)
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError): load(**args)


def test_snapshot_path_escape_and_nonfinite_json_fail(evidence):
    args, result, reseal = evidence
    result["source_snapshots"][next(iter(result["source_snapshots"]))]["path"] = "../character.bin"
    reseal()
    with pytest.raises(ValueError): load(**args)
    args["folder"].joinpath("result.json").write_text('{"status":NaN}', encoding="utf8")
    with pytest.raises(ValueError): load(**args)
