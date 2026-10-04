# Scene reference checks before generation

New scene-generation preparations now measure the authored poses and their exact SOMA77 → SOMA30 → relaxed SOMA77 conversion before text encoding or model inference. This catches incompatible reference geometry early; it does not make Kimodo aware of objects or partners, or establish that every pose satisfying its sparse constraints is infeasible.

The [official constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html) describes reduction to SOMA30 and distinguishes position constraints from explicit local-rotation constraints. The pinned local export code fills omitted hand joints from its relaxed-hand pose. Consequently, fitting a detailed hand reference is not sufficient evidence that its surface contacts survive model conversion. A previous dedicated high-five target study exposed this; the check now belongs to the general scene preparation path.

The [SOMA-SEED-v1.1 model card](https://huggingface.co/nvidia/Kimodo-SOMA-SEED-v1.1) also specifies a 30-joint output. Switching to that checkpoint would not supply independently generated finger articulation. No alternate checkpoint was downloaded or selected for this work; compatible references and an explicit hand-authoring layer remain necessary to investigate.

## Behavior

`scene_target_preflight.py` uses the unchanged pinned skeleton conversion on CPU. It verifies source forward kinematics, conversion idempotence, unchanged root/contact/auxiliary arrays, and original source hashes. Original and converted motions remain separate. It retains the complete contact tracks and source/method/asset bindings.

At the union of **every authored contact frame**, it skins every actor with all supplied influences, checks the floor and every declared primitive object, and queries both directions of every partner pair. The reference depth screens are 5 mm; ordinary vertex-normal/tangent screens remain 15 degrees. Contacts retain their authored position tolerances. Distributed primitive contact regions keep their own area, spacing, clearance and normal requirements; they are no longer rejected merely because the separate vertex-normal auditor has different semantics. These are reference diagnostics, not changes to frozen release criteria.

A partner appearing only as the target of a contact now receives its own hand/foot guide. Simultaneous effectors still merge into one guide rather than conflicting implicit root constraints.

Default preparation rejects failed references and preserves the audit and rejection state. `run_actions.py` checks the request's preparation folder even when a different output folder is specified, before launching encoding. Changed sources, projection arrays, skin, methods, upstream checkout, incomplete observation populations, missing bindings and partial/failed preparations reject. Failed references can be sampled only with an explicitly prepared `--diagnostic-targets` batch. That mode remains visible in generation state and scene metadata and never grants quality approval. Existing ordinary historical batches without this new contract remain readable.

## Development measurements

| Reference | Native maximum partner depth | After model conversion | Outcome |
| --- | ---: | ---: | --- |
| Existing planned high-five, frame 75 | 1.894 mm | 7.727 mm | Converted partner reference fails |
| Existing fitted seed-11 high-five, frame 60 | 16.038 mm | 16.038 mm | Both reference geometries fail; standard preparation rejects |
| Constructive moving-box reference, frames 10–12 | No partner | No partner | Strict preparation passes |

The planned high-five also misses the existing **vertex-normal** screen: 17.133 degrees native and 16.774 degrees after conversion. Its previous region-normal result used a different measurement and threshold. Neither result substitutes for the other. Its palm point remains within 30 mm (22.627/22.732 mm), illustrating why point accuracy alone cannot approve a reference. The fitted high-five's small point errors and passing orientation likewise do not hide partner overlap. These rows measure contact-frame references, not whole-motion collision maxima.

The positive case uses a pinned native relaxed pose translated alongside an authored box for 30 frames, with a yawed actor placement. A selected exterior hand vertex is matched to an object-local face point over three contact frames, with an explicit surface-normal target. Original and converted references have no floor penetration, about 0.000024 mm maximum object depth/point error, and no reference failure flags. It is a constructive compiler/geometry fixture, **not generated motion, a realistic grasp or held-out animation evidence**. Its request is prepared but not encoded or sampled.

The first standalone high-five audit and earlier positive/strict prototypes remain immutable. Final preparations use `reports/action-jobs/scene-target-preflight-object-pass-v3` and `reports/action-jobs/scene-target-preflight-rejected-v2`. An independent NumPy replay in `reports/scene-target-preflight-replay-v3` checks all-frame local subset projection, hierarchical forward kinematics and all-influence skinning for five actor/reference inputs across three cases. It reproduces 42 complete geometry/contact comparison rows and verifies actual dispatch rejection before encoding. The primitive and conservative Trimesh depth helpers are shared; normals/regions are producer observations. This is independent of the Torch projector, not an independently implemented physics system. The intermediate replay's dispatch probe also blocked read-only Git validation; that failed harness attempt is retained. The final probe permits only the two exact upstream revision/status queries while rejecting encoding/generation subprocesses.

Final targeted validation covers 113 unique Python cases: 45 model-free checks and 69 integration checks with one overlapping orientation test. Initial missing-Torch collection failures and an unsuitable overlapping-box vertex fixture are retained locally. Geometry-only skinning now imports without the correction routine's Torch dependency; actual correction tests still pass. Complete method archives and retained failures remain outside the public source repository.

## Reproduce

Use new output directories and the separately acquired pinned vendor assets. Never overwrite an earlier study.

```powershell
.venv\Scripts\python.exe scripts/scene_target_preflight.py reports/paired-contact-target-plan-v3/scene.json reports/<new-target-audit>
.venv\Scripts\python.exe scripts/scene_generation.py prepare <scene.json> <actor-plan.json> reports/action-jobs/<new-scene-job>
.venv\Scripts\python.exe scripts/run_actions.py reports/action-jobs/<new-scene-job>/request.json --output reports/action-jobs/<new-scene-job>
```

For a deliberate failed-reference comparison, add `--diagnostic-targets` to **preparation**. That preserves failure evidence; it is not a correction or approval. Source point/region/orientation fitting remains required. New prompts still require encoding their actual text; the existing baseline cache is not a substitute.

No new checkpoint sampling, training, GPU rendering, Studio restart, engine run, human rating or cleanup timing occurred. All 14 release evidence lists and acceptance criteria remain unchanged. Passing a converted reference does not establish actual generated adherence, approach/release continuity, balance, anatomy, finger control, self collision, continuous collision, forces, rig transfer or natural animation. Next work must measure meaningful generated/corrected object and partner motion against compatible references and collect developer semantics/cleanup observations under the same full-project goal.
