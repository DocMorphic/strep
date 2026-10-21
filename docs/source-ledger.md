# Primary-source ledger

Checked 2026-09-24 unless marked otherwise. Preserve license files with assets and review the complete terms before distribution.

## 2026-10-10: upstream scope recheck during contact continuation

- The current [RP-v1.1 model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1) still describes one-character, object-unaware motion and possible prompt/skating failures. Game/media animation remains an intended use. This recheck does not establish successful general scene interaction or change the pinned local checkpoint, asset or data permissions.
- NVIDIA's [best practices and limitations](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html) recommend focused, self-contained action prompts, primarily sparse constraints and enough time for transitions at the start of later segments. The published limit is ten seconds per prompt. Complex descriptions or out-of-training behaviors can fail. Keep arbitrary input prompts, but measure their actual correctness rather than treating a supported input string as a supported motion.
- The [constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/constraints.html) specifies reduced SOMA30 model conditioning, wrist/hand and heel/toe end-effector targets and optimization post-processing. Those controls do not by themselves certify full-mesh contact, object penetration, partner timing or anatomy. Existing Strep native and exported checks remain required.

No new model, dependency, raw motion data or asset is acquired. The [verified failed contact continuation](contact-interval-batch-v4.md) remains a development study, not evidence that prompting has solved object interactions.

## 2026-10-12: supplied-rig editing preservation follow-up

Source inspection of UniMate revision `b78c7807df7cf4231d4e67f8d0ece29c5e11025b`
adds per-actor name-resolution and decoded-export preservation requirements to
the [existing model screen](interaction-model-screen-2026-10.md). Unmatched kept
joint names can yield an all-false feature mask; the default export recovery
uses rotations, root trajectory and rest offsets. Feature clamping is therefore
not treated as proof of preserved world/skin contacts. Seventeen small source
and terms snapshots are retained in `reports/model-alternatives-source-v1`.
No external code is executed, no weights/data are acquired and no alternative
is selected. MotionFix/HY-Motion availability and permission findings remain
those already recorded; this follow-up adds no motion-performance evidence.

| Source | Finding / project decision |
|---|---|
| [Kimodo-SOMA-RP-v1.1 card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1) | Human skeletal motion checkpoint; game/media use listed. Single-character output, object-unaware, possible skating and prompt failures. Card describes 30 internal joints; current code exposes SOMA77. Inspect actual output metadata instead of assuming identical skeletons. |
| [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) | Commercial use and derivatives permitted subject to terms; redistribution notices and separately licensed components matter. No model outputs or weights redistributed here. |
| [Official source](https://github.com/nv-tlabs/kimodo) | Apache-2.0 code; cloned unchanged and commit pinned. Inference, demo, benchmark, correction code present. No documented turnkey training recipe established by this inspection. |
| [Installation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/getting_started/installation.html) | Linux is primary development platform; PyTorch environment and gated Meta Llama access required. Native Windows remains untested here. |
| [CLI](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/cli.html) | Seed, multi-prompt durations, NPZ/BVH exports, and optional postprocessing supported; flags checked against cloned code. |
| [Benchmark metrics](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html) | Upstream covers skating/contact consistency, constraints, text alignment. Our scene, transition, transfer, import, and cleanup measures extend this. Do not download raw benchmark data by implication. |
| [BONES-SEED terms](https://bones.studio/info/seed-license) | Eligibility and generative-model restrictions remain. Do not acquire or train this product on raw BONES-SEED without a separate license. |
| [Meta Llama 3 8B Instruct](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct) | Separately licensed, manually gated encoder dependency. Account access must be established by the user; never put tokens in chat or repository files. |
| [CesiumMan asset](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CesiumMan) | Downloaded pinned GLB, CC BY 4.0, © 2017 Cesium; separate logo terms retained. Attribution and modification status in asset provenance. |
| [CMU mocap](https://mocap.cs.cmu.edu/) | Official indexed homepage rechecked 2026-10-11: broad free-use statement and commercial inclusion, with direct resale of raw or converted data prohibited. Requested publication attribution names the database and NSF EIA-0196217. Two specifically chosen ground-reference ASF/AMC pairs acquired locally on 2026-10-11 and fully reconstructed at original 120 Hz; [intake and rights scope](cmu-ground-reference-v1.md). Exact proposed training/distribution workflow remains unadmitted; no raw/converted payload published. |
| [Uni-Inter](https://arxiv.org/abs/2511.13032) | Research precedent carried forward from handoff; not re-reviewed or integrated here. |
| [MotionFix](https://motionfix.is.tue.mpg.de/) | Source-motion/text editing precedent; latest code, metadata/motion terms and unresolved permission distinctions are recorded in [the editing recheck](source-aware-editing-research-v2.md). No weights or motion data acquired. |

`benchmarks/sources.lock.json` records public revision identifiers, not downloaded weights. Before running, download those exact revisions, verify checksums, and freeze package versions. Code currently resolves Hugging Face names without a revision argument, so using a model display name alone is insufficient for an immutable run.


## 2026-09-26: independent rig assets

- Quaternius Universal Base Characters: https://quaternius.com/packs/universalbasecharacters.html and https://quaternius.itch.io/universal-base-characters . Free Standard archive acquired via official page; included license CC0-1.0. Original archive, selected source files, SHA-256 and explicit missing-texture substitutions retained in assets/characters/quaternius-base. No raw motion training dataset acquired.
- RiggedFigure: KhronosGroup/glTF-Sample-Assets revision c6a6bd13ab2b3c685c7903d03561b8a9392f38b8, Models/RiggedFigure; pinned README credits Cesium under CC BY4.0. Shares existing rig family.
- RobotExpressive: mrdoob/three.js revision1af6de5bd8cd481993483dc6127eba668e818dfd, examples/models/gltf/RobotExpressive; pinned README credits Tomas Laulhe/Quaternius under CC0 with Don McCurdy modifications. Original preserved and unsupported; compatibility/format failures documented.

## 2026-10-11: additional independently authored rig candidate

The official [Kenney Animated Characters Protagonists page](https://kenney.nl/assets/animated-characters-protagonists) lists CC0. Its small official archive was acquired and inspected without executing third-party code or animation trials. The included `License.txt` confirms CC0-1.0 and identifies Kenney as creator/distributor; its pack version is 1.1, while the page's update list says 1.0. The retained original archive is 581,441 bytes, SHA-256 `ec3787de70fa2200256848d74201b10f6b6c3126594e9857bf989753312c2b84`; it contains `Model/characterMedium.fbx` and three separate animation FBX files (idle, jump, run), with no GLB or glTF file. Original page, archive, included license and bounded ZIP inventory are retained locally under `reports/kenney-protagonists-acquisition-v1`.

This provides a candidate outside the existing Quaternius family, not evidence of transfer generalization. Bounded scalar inspection of its FBX 7400 model finds 60 model nodes: one root, one mesh and 58 limb nodes. Exact FBX cluster connections identify 45 deforming model nodes and 13 helper limbs. A 19-role development proposal passes the source model hierarchy check, distinguishing upper legs from lower legs and using UpperChest for the branching chest role. Numerical skin/mesh arrays were not decoded. Root and mesh scale metadata include 100; these raw values do not establish exported units or compatibility. Metadata and role-link receipts are retained locally in `reports/kenney-protagonists-fbx-metadata-v1` and `reports/kenney-deforming-roles-v1`. At this acquisition checkpoint, format conversion, complete skin/topology validation, exported mapping and engine compatibility had not been tested. Do not replace or expose the existing frozen reservations, count this archive as a held-out rig, or infer motion quality from its acquisition. No model training, motion generation or release approval follows.


## 2026-09-26: prompt editing research

- [Kimodo constraint guide](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html): read alongside pinned local constraints/model/postprocess code; full-body guides are positional, not exact rotations. Used unchanged checkpoint for finite boundary-guided replacement.
- [MotionFix](https://motionfix.is.tue.mpg.de/): re-reviewed as a trained source-motion/text editing precedent. No MotionFix data or weights acquired; no new license or training assumption. See docs/prompt-edit-v1.md for measured differences and failures.


## 2026-09-27: boundary conditioning and optional upstream correction

- Official constraint docs revisited: https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html . Fullbody constrains derived positions, not exact rotations; smoothed-root canonical XZ conventions checked against pinned code and 24 matched runs.
- Official Windows build path: https://github.com/nv-tlabs/kimodo/blob/main/setup.py . Pinned local MotionCorrection source and CMakeLists reviewed; extension currently absent. No community wheel acquired, no new dependencies installed this turn. See docs/boundary-conditioning-v1.md.


## 2026-09-27: native correction build and measured contact regressions

- Official compiler release: https://github.com/skeeto/w64devkit/releases/tag/v2.10.0 ; official CMake release: https://github.com/Kitware/CMake/releases/tag/v3.31.8 . Portable downloads verified against official release SHA256 digests. Built pinned NVIDIA MotionCorrection unchanged; source dependency commits and copied licenses retained in `.cache/motion-correction-package/build-provenance.json`.
- Upstream constraint/postprocessor/C++ utility code was inspected locally. Actual matched studies demonstrate accurate boundary fitting and skin/contact regressions; see `docs/motion-correction-v1.md`. No community wheel, training data, or checkpoint changes. Offline rebuild works on this machine; no broader installer claim.

## 2026-09-27: interaction-model feasibility revisited

- [Uni-Inter author code](https://github.com/Darkdawner/Uni-Inter) is now available; public source-only snapshots at revision `0d5248c9948939d47382f482b06f6e86b037b012` are retained under `reports/interaction-research-v2`. The [repository license](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/LICENSE) is CC BY-NC-SA 4.0. No product integration or weight/data acquisition.
- [InterControl](https://github.com/zhenzhiwang/intercontrol) and [InterAct](https://github.com/wzyabcas/InterAct) author repositories inspected as comparators; exact checkpoint/data permissions and local feasibility remain unverified. No models installed.
- [Kimodo training question](https://github.com/nv-tlabs/kimodo/issues/25) and pinned source inspected. Do not assume a ready fine-tuning command. Findings and next-experiment decision: [interaction research v2](interaction-research-v2.md).

- 2026-09-27 interaction survey extension: InterMask MIT code and author checkpoint-download script inspected; separate checkpoint commercial permissions unresolved. Interact2Ar author LICENSE restricts software to noncommercial research; checkpoint manifest available. Neither selected or acquired for product integration. Exact primary links and scope are in [interaction-research-v3.md](interaction-research-v3.md).


### Experimental conic solver (checked 2026-09-28)

[Clarabel official Python documentation](https://clarabel.org/stable/python/getting_started_py/) specifies direct sparse conic problem construction. [Pinned0.11.1 PyPI metadata](https://pypi.org/project/clarabel/0.11.1/) lists Python>=3.9, Apache2.0 and a Windows abi3 wheel; downloaded bytes match its published SHA256557d5148a4377ae1980b65d00605ae870a8f34f95f0f6a41e04aa6d3edf67148. Vendored separately under vendor/clarabel-0.11.1 with license retained; active venv packages unchanged. See reports/conic-solver-bootstrap-v1.json. This is an optimization dependency, not motion training data. The conic-speed toy proof retains AlmostSolved status and is not a character-motion result.


### Per-joint angular development (2026-09-28)

Official SciPy rotation-vector API/source checked: https://scipy.github.io/devdocs/reference/generated/scipy.spatial.transform.Rotation.as_rotvec.html and https://github.com/scipy/scipy/blob/main/scipy/spatial/transform/_rotation.py . Runtime dependency unchanged. Project tests prove the chord/relative-angle identity and local derivatives; docs/angular-release-v1.md records the new protocol and limits. No training data or model acquired.

### Endpoint angular-rate returns (2026-09-29)

Official SciPy [rotation-spline source](https://github.com/scipy/scipy/blob/main/scipy/spatial/transform/_rotation_spline.py) checked, alongside the installed 1.15.3 angular-rate/rotation-log Jacobian implementation. The project uses an explicit cubic Hermite return, tested with noncommuting rotations and independently audited. This is not use of RotationSpline or a claim of continuity after correction/baking. Results and retained failures: [endpoint-rate study](sphere-region-tangent-v1.md). No dependency, model or data acquisition.


### Contact feasibility certificates (2026-09-29)

Official [SciPy HiGHS interface](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html) checked for inequality form, status, residuals and marginals. Existing SciPy 1.15.3 retained; no dependency acquisition. The project independently derives and exactly verifies bounded-domain contradiction certificates, and a separate conservative skin/joint displacement bound. Results and assumptions: [contact feasibility diagnosis](contact-feasibility-diagnosis-v1.md).


2026-09-30: [Godot CylinderShape3D](https://docs.godotengine.org/en/stable/classes/class_cylindershape3d.html) identifies a physics cylinder with radius/height and warns about known cylinder collision bugs. Strep adds analytic cylinder authoring/export with verified baked playback; physics release remains explicitly unavailable until its own backend/collider study. See [cylinder scene evidence](cylinder-scenes-v1.md).


### Partner approach waypoint planning (2026-09-30)

CMU's [goal-set constrained trajectory optimization](https://publications.ri.cmu.edu/manipulation-planning-with-goal-sets-using-constrained-trajectory-optimization) and Berkeley's [TrajOpt documentation](https://rll.berkeley.edu/trajopt/doc/sphinx_build/html/) were checked as primary planning references. They motivate separating task constraints from collision avoidance and testing alternate configurations; no planner implementation or robotics performance claim is imported. Strep independently implements and tests rigid two-bone swivels, then checks actual decoded character meshes. See [waypoint evidence](paired-swivel-waypoint-v1.md). No model, data or dependency acquired.


### Interaction availability recheck (2026-09-30)

Primary repository documentation and licenses for PhysiGen, Human-X Interaction, GNOCHI and InterGen were inspected at captured revisions. Missing pipeline/checkpoint releases and noncommercial terms remain material distinctions; no replacement is qualified by this limited survey. Source links, exact revisions, local manifest and next-experiment decision are in [interaction research v4](interaction-research-v4.md). No model, dataset, body asset or dependency acquired, and no third-party code executed.


### Interaction constraints and replacement availability recheck (2026-10-01)

[NVIDIA's constraint concepts](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/constraints.html) still describe sparse pose/end-effector guidance and conversion from SOMA77 to SOMA30 before model conditioning. This supports keeping joint-constraint accuracy separate from full-mesh contact validation; it does not establish scene-aware generation.

The [Uni-Inter author repository](https://github.com/Darkdawner/Uni-Inter) still lists CC BY-NC-SA 4.0 and describes inference using a checkpoint obtained after training. Its [paper](https://arxiv.org/html/2511.13032v2) presents joint human/object/scene conditioning, but supplies no evidence that this specific Strep rig/contact problem is solved. The earlier decision remains unchanged: no product integration, model/data acquisition or third-party execution from this recheck. Continue measured geometry diagnosis before choosing a replacement or new training programme.


### Initially intersecting surfaces (2026-10-01)

The authors' [Untangling Surfaces via Shape and Mesh Repulsion project](https://simulation-intelligence.github.io/Mesh-Untangling/) combines a global shape energy with local mesh penalties to remove existing intersections. This is relevant precedent for an already intersecting source, not evidence that Strep's rig-constrained contact or temporal problem is solved.

The [official repository](https://github.com/Simulation-Intelligence/Mesh-Untangling/tree/8cc1557f23562803c347b95ec24b7c445afe1d54) documents Linux, NVIDIA CUDA/cuDSS and C++20 requirements and an OBJ deformation/recovery pipeline. Its LICENSE is Apache-2.0; its README separately flags CGAL-linked binary terms and asset-specific licensing. No third-party code executed, dependencies installed or meshes acquired. Inference for Strep: preserving every separated triangle pair is a conservative regression policy, not a general untangling algorithm. Any proposed adaptation needs a separate rig-space prototype and full contact, angle, mesh and motion validation; free vertex deformation must not silently change the supplied character.


### Pinned hand representation (2026-10-04)

[The local NVIDIA skeleton definitions](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/definitions.py) initialize SOMA77 local rotations from the relaxed-hand asset, then overwrite the 30 mapped joints. Static inspection counts 47 unmapped entries, including 44 finger entries: 38 articulated joints and six terminal entries. The mapped finger-named entries are thumb and middle endpoints on each hand. Unmapped local rotations remain at the supplied rest pose; wrist and body motion can still move their world poses. The [name mapping](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/base.py) and the finite 77-by-3-by-3 rest asset are inspected without importing Torch or running Kimodo.

Inference for Strep: tuning the existing body representation alone cannot introduce independent outputs for those missing articulated finger joints. A hand editor or an extended generator needs an explicit representation and rig/geometry checks. This is not proof that the omission causes the present contact failure, that a grip is infeasible, or that a learned editor will work. Source/rest hashes and both corrected inspection failures remain locally preserved under `reports/kimodo-hand-representation-audit-v3` and its repair archives; no model/data acquisition or product integration follows from this audit.


### Native rig transfer reference - 2026-10-05

Checked the primary [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) for local TRS, parent-composed joint transforms, quaternion interpolation and Float32 animation storage. These format rules support decoded/native-key fidelity checks; reference-pose calibration and root-displacement scaling are Strep implementation policies, not motion-quality guarantees supplied by glTF. No third-party models, data, code or dependency acquired. Methodology and generated fixture results: [native rig transfer](native-rig-transfer-v1.md).

### Material surface witnesses - 2026-10-07

Checked Trimesh's primary [proximity API](https://trimesh.org/trimesh.proximity.html) for nearest point, distance, original triangle identity and its inside-positive signed-distance convention, including its near-surface tolerance region. Checked the [triangle API](https://trimesh.org/trimesh.triangles.html) for barycentric conversion. Existing Trimesh 5.1.0 is retained; local proximity/triangle source hashes bind the generated-fixture experiment. Strep records complete original crossing and vertex-containment proposal populations, then checks actual stored motion and mesh outputs separately. These numerical primitives provide no rig-constrained motion or quality guarantee. No model, dataset, character payload or dependency acquired. See [material witness methodology and failures](material-witness-guides-v1.md).

### Returned solver iterates - 2026-10-07

Checked Clarabel's primary [Python interface](https://clarabel.org/stable/python/getting_started_py/) for returned `solution.x`, primal/dual/slack arrays and separate termination statuses. `InsufficientProgress` indicates termination for lack of progress; it does not assert an optimum or infeasibility. Strep inspects an explicitly bound finite iterate through a separate strict diagnostic, preserving the original status and export/geometry gates. The local 0.11.1 runtime, model and original solver settings remain unchanged. No model, data, asset or dependency acquired. See [finite-iterate methodology and measured failures](finite-guide-iterates-v1.md).

### Interaction and rig-model recheck - 2026-10-10

The [dated model screen](interaction-model-screen-2026-10.md) records current author repositories/model cards for UniMate, InteractMove, InterMask, InterPose and InterAct, separating code, weights and upstream dependencies. UniMate's author repository now links released checkpoints and custom-rig preprocessing; its checkpoint card declares CC BY-NC 4.0 and contact limitations. A stale fork is not used as release evidence. Other candidates' checkpoint/data/asset permissions remain incomplete or explicitly non-commercial. No model/data acquisition, new dependency, training or third-party execution follows. Continue the original native contact study and independent replay, then compare a justified permitted editor or scene-conditioned initializer against the unchanged baseline.


## 2026-10-11: actual Kenney conversion and rejected rig intake

Pinned Godot 4.7.2 conversion completes without bundled animation FBXs. The generated GLB has 61 nodes, one skin and no animations; engine metadata reports 1,029 mesh vertices and 1,604 triangles. Strep rigid-transform intake rejects its non-unit root and limb transforms. No transfer cases run. A failed replay helper import is preserved; its corrected version confirms the rejection and zero clips, without numerical motion replay. See [actual rig-intake evidence and next work](rig-intake-kenney-v1.md). Original acquisition/license records remain unchanged. Conversion does not prove FBX/GLB geometry equivalence, retargeting, held-out generalization or release quality.


## 2026-10-11: explicit Kenney derivative and seven development transfers

A separate static-rig derivative preserves the converted GLB default shape with about 0.205 micrometres peak reference error, confirmed with separate quaternion/hierarchy and blended skin calculations. It passes unchanged rigid-transform intake. Seven existing seed-77 development motions transfer and independently replay with one fixed profile, while crawl, kick, get-up and run/roll/stand retain substantial ground penetration. The original rejection and asset stay saved; no raw asset payload is published. See [adaptation methodology, complete transfer comparison and failures](rig-scale-adaptation-v1.md). This is reused development data, not a held-out reservation, FBX conversion equivalence, new model generation/training, engine playback or human/release approval.


## 2026-10-15: Uni-Inter author-source and artifact screen

The [dated source screen](uni-inter-source-screen-2026-10-15.md) pins author commit `0d5248c9948939d47382f482b06f6e86b037b012`. Its repository LICENSE is CC BY-NC-SA 4.0; commercial product permission is not established. The inspected tree contains no motion checkpoint files and its GitHub releases endpoint is empty; this does not prove no checkpoint exists elsewhere. Its dataset-based 22-joint inference writes GIFs, and the inspected NTU path predicts one person conditioned on the other recorded motion. No third-party code is executed, installed or incorporated, no weights/data are acquired, and no training is admitted. The unchanged Kimodo baseline and original evaluation contracts remain in place.

## 2026-10-16: corrected Kimodo checkpoint release

NVIDIA's [v1.2 model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2)
announces corrected training splits after some benchmark test sequences leaked
into v1.1 training. It reports reduced skating but retains single-skeleton and
scene-object-awareness limits. Keep v1.1 as historical baseline; benchmark
comparability and our own trial performance are separate questions.

Public model revision `0e3c89024d896064b6851201373f7834784a386b` and author
code revision `e1c219c99b4b94ba48be1fb6a1cbc64ecee4c954` are pinned in
`reports/kimodo-v12-source-screen-2026-10-16`. The checkpoint's LICENSE bytes
match the installed v1.1 license; the linked
[NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/)
was rechecked. Raw BONES-SEED training permission does not follow from a model
license and remains separately restricted.

The exact public checkpoint is acquired into a separate ignored directory,
with all ten files checked against pinned Git/LFS identities and stored-byte
hashes. Weight SHA-256 is
`fdcef624140a12c0a4840192ce0b75cafb4e73228a893da3864b4a990d3e919e`;
payload size is 1,133,177,724 bytes. The acquisition guard completes in 123.969
seconds at 42,909,696 sampled bytes, with 124 observations independently replayed.
The existing model manifest, v1.1 files, vendor source and default remain
unchanged. No raw training data, new third-party code execution, new-model
inference or training occurs. Acquisition is not model/runtime/quality approval;
compatibility and a controlled comparison remain separate work.

The first compatibility attempt stops at a missing YAML dependency in the
minimal source-test environment before reading model metadata; its failed
guard remains recorded (16.187 seconds, 18 observations). The retry uses the
existing project environment, Python 3.10.21/NumPy 2.2.6/PyYAML 6.0.3. It verifies
that parsed configurations match and all six normalization arrays have equal
shapes/dtypes and identical values. Raw checkpoint keys differ. A further
complete check applies the existing upstream `denoiser.backbone.` removal rule:
all 408 mapped keys, shapes and F32 dtypes match, without collisions. Every one
of the 408 tensor payloads differs, so this is a real weight change rather
than only a renamed container. All F32 values in both checkpoints are finite.

Those inspections complete in 17.234 seconds/43,573,248 sampled bytes/19 replayed
observations and 20.328 seconds/48,869,376 bytes/22 replayed observations. They
remain under `reports/kimodo-v12-compatibility-v1`, `-v2` and `-v3`. File/metadata
compatibility does not prove CUDA loading, sampling or better motion. No model
is constructed and no neural forward is executed. The pinned vendor registry
still lacks v1.2; a separate explicit loader qualification and matched
development comparison are required before considering a default change.

Subsequent local work completes actual v1.2 CUDA construction and a matched
28-clip v1.1/v1.2 development comparison, using the original pinned vendor
rather than updating upstream code. All 14 newly generated v1.1 outputs exactly
reproduce their historical arrays. v1.2 has mixed proxy results, including worse
crawl floor depth and better run/roll/stand depth. This neither verifies nor
contradicts the publisher's separate benchmark under different evaluation
conditions. See [the version comparison](kimodo-version-comparison-v1.md) and
its published prompt/seed protocol. Historical default and files remain intact;
no raw training data or model training is introduced.

## 2026-10-16: scene-aware alternatives after placement failures

Primary-source intake is saved under the ignored
`reports/interaction-backend-screen-2026-10-16/`, with public metadata,
revision-pinned READMEs, available license text and SHA-256 receipts. No model
weights, body models, raw datasets or third-party execution were acquired.

- [Uni-Inter's paper](https://arxiv.org/html/2511.13032v2) describes joint
  prediction conditioned on a shared interaction volume spanning people,
  objects and scenes. The available [repository at 0d5248c](https://github.com/Darkdawner/Uni-Inter/tree/0d5248c9948939d47382f482b06f6e86b037b012)
  provides a 4D diffusion implementation, preprocessing and inference following
  training; its README documents four-GPU distributed training. Its archived
  [LICENSE](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/LICENSE)
  states CC BY-NC-SA 4.0. It remains research precedent, not an adopted commercial
  backend. A ready checkpoint and laptop inference fit were not established.
- [ReMoGen at f2b667c](https://github.com/4DVLab/ReMoGen/tree/f2b667c895998370dcc60fb5921ff474ad78fe7a)
  documents released checkpoint download scripts, partner/scene adapters and
  autoregressive reaction generation with SMPL-X. Those rollouts could be
  studied for offline baking; they are not a change to Strep's asset-authoring
  objective. Its documented environment uses Python 3.8, Torch 2.1/CUDA 11.8 and
  PyTorch3D. The public repository API returned null license metadata and its
  license endpoint returned 404. Suitable code/weight/body-model permissions
  and 8-GB inference fit are unverified; no integration is approved.
- [InterAct at 96180a3](https://github.com/wzyabcas/InterAct/tree/96180a34f7b516e7f3520b853c19ea8679b8204f)
  documents pretrained text-to-object-interaction checkpoints and contact-guided
  inference. Its README requests non-commercial dataset access and separate
  source-dataset/body-model terms; its pipeline requires SMPL-family assets and
  `pointnet2_ops`. Dataset access statements do not establish commercial rights
  for the checkpoints. The PDF license was located but not parsed in this
  screen, and full checkpoint terms and laptop execution remain unqualified.

These are capability and intake observations, not measured comparisons to
Kimodo or legal conclusions about every component. Continue the existing
licensed baseline and explicit deterministic scene corrections while evaluating
alternatives against the same rig/contact/export and human-review requirements.

## 2026-10-17: upstream constraints rechecked during scene-feedback work

NVIDIA's current [skeleton documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/skeleton.html)
still distinguishes the reduced SOMA30 prediction skeleton from SOMA77 exports,
with most hand/finger detail removed internally. The [constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/constraints.html)
says SOMA77 constraints are reduced before conditioning and describes wrist/hand
end targets. This corroborates the earlier pinned local representation audit;
it is not a new model installation or evidence that finger omission caused a
particular collision. The local target codec continues rejecting omitted-joint
rotations that SOMA30 cannot represent rather than silently dropping them.

The current [best-practice guidance](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html)
favors sparse conditioning apart from root paths, warns about conflicting
constraints and recommends post-processing for precise contacts. Strep's many
mesh inequalities are in its separate native asset editor, not thousands of
new conditioning frames sent to Kimodo. No inference or training runs in this
feedback study. A dedicated hand editor or expanded representation remains a
research option, not an approved trained capability. The existing Uni-Inter
intake above remains precedent; rereading its paper does not establish new
checkpoint, commercial-use or laptop-runtime qualifications.

## 2026-10-17: contact correction and continuous validation

The primary [IPC project](https://ipc-sim.github.io/) formulates contact through
a barrier and an optimization method for deformable simulation. The
[Rigid IPC paper](https://ipc-sim.github.io/rigid-ipc/assets/rigid_ipc_paper_350ppi.pdf)
explicitly requires a non-interpenetrating initial configuration and validates
curved rigid-body trajectories through conservative collision queries. Strep's
current candidate already contains intersections, and joint quaternion
interpolation followed by skinning is not a straight vertex trajectory.
Therefore an IPC citation or a linear vertex query would not certify this
native clip. This is an inference about applicability, not an implementation
or guarantee transferred from the paper.

The official [IPC Toolkit](https://github.com/ipc-sim/ipc-toolkit) exposes
distance derivatives, barrier terms, and linear/nonlinear continuous collision
queries with C++ and Python interfaces. Its README identifies an MIT code
license and explicitly says it is not a complete simulator or solver. No new
dependency is installed, and no bundled model/data permissions follow from that
code license. A possible follow-on experiment must first restore sampled
feasibility, implement the actual native interpolation trajectory and its
conservative bounds, then compare continuous checks against retained discrete
failures. A feasible seed, supported trajectory interface, native derivative
composition and Windows memory/runtime behavior all require evidence before
adoption. Current sampled mesh checks and strict source-relative bounds remain
the acceptance rules for the present trials.

## 2026-10-18: triangle-pair projection guidance

David Eberly's primary [Intersection of Convex Objects: The Method of Separating
Axes](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf),
sections 2, 5 and 9, explains separation through projected vertex intervals and
the additional in-plane edge directions needed for coplanar triangles. The
document lists CC BY 4.0. Strep's implementation is independent code; no listed
pseudocode or external collision implementation is copied or installed.

The native editor uses these ideas to propose a fixed direction for each
explicitly bound triangle pair. It retains all nine left/right vertex
combinations and composes both sides' supplied derivatives. The direction is
frozen during differentiation. These floating directional rows are guides:
failure does not establish collision or infeasibility, and success is not an
exact whole-mesh or continuous-time certificate. Independent full-mesh and
saved-motion checks still govern comparison. This adds no model checkpoint,
training data or runtime dependency, and changes no model/data license terms.

## 2026-10-18: moving rigid coordinate frames

Russ Tedrake's primary MIT [Robotic Manipulation, Basic Pick and Place](https://manipulation.mit.edu/pick.html)
describes composing and inverting rigid frames and expressing points relative
to them. Strep independently applies the product rule to the inverse point
transform, including supplied point, frame-position and frame-rotation
derivatives. No Drake implementation is copied or installed. This is a
coordinate-map building block; source permissions, scene feasibility and
nonlinear motion/contact validation remain separate. The study tests whether
prop-relative projection directions avoid restrictions introduced by freezing
directions in world space. It adds no model, training data or runtime dependency.

## 2026-10-18: smooth complete interior-depth guidance

Boyd and Vandenberghe's primary [Convex Optimization](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf),
section 3.1.5 (printed page 72), bounds log-sum-exp relative to the largest
input. Strep independently composes a corrected soft minimum of all convex
facet slacks with softplus to obtain smooth interior-depth guidance. Its
real-arithmetic error budget is explicit; floating geometry and motion
acceptance remain separate. No book/example implementation is copied. The
book remains copyrighted by Cambridge University Press; web availability
does not make its text or example code project assets. Existing NumPy and
Trimesh are reused; no checkpoint, training data or dependency is acquired.

## 2026-10-18: local vector-norm constraints for sampled rates

Lobo, Vandenberghe, Boyd and Lebret's primary
[Applications of Second-Order Cone Programming](https://stanford.edu/~boyd/papers/pdf/socp.pdf)
(1998), section 1.1, equations 1–2, describes Euclidean norms of affine maps
as cone constraints. This informs the next local rate-vector model after
measured angular-rate failures pass scalar tangent guards. Any affine
approximation remains separate from nonlinear rig and Float32 validation;
the paper does not establish feasibility or correctness for Strep's motion.
No paper implementation is copied, no solver/dependency is installed and no
data or checkpoint is acquired. The paper remains copyrighted by Elsevier.

## 2026-10-18: solver accuracy versus original-unit norm admission

Clarabel's primary [solver settings](https://clarabel.org/stable/api_settings/)
distinguish full and reduced feasibility targets. Its version-pinned
[0.11.1 convergence code](https://github.com/oxfordcontrol/Clarabel.rs/blob/v0.11.1/src/solver/implementations/default/info.rs#L149-L153)
normalizes primal residuals by problem/variable norms. Thus a solver status
and its relative residual target do not replace Strep's per-cone admission
or nonlinear raw/saved gates. The measured key-63 failure motivates a stricter
solver target, not a relaxed physical bound. Strep's existing earlier kernel
stays replayable; a versioned precise kernel permits targets from 1e-14 through
1e-10, defaulting to 1e-12, and keeps the previous admission limits unchanged.
No upstream implementation is copied; the existing installed Clarabel 0.11.1
solver is reused with its own terms. No dependency, checkpoint or data is acquired.

## 2026-10-21: diagnosing containment signs near moving surfaces

The primary [Trimesh proximity documentation](https://trimesh.org/trimesh.proximity.html)
describes nearest-surface and signed-distance queries. Its current web docs are
5.1.1; the local diagnostic remains on the existing pinned 5.1.0 dependency and
records the installed implementation hashes. Strep's existing volume record
explicitly states that self-intersections have not been checked; a positive
volume/topology check alone is not a geometric self-intersection certificate.

Jacobson, Kavan and Sorkine-Hornung's primary
[generalized winding-number project](https://users.cs.utah.edu/~ladislav/jacobson13robust/jacobson13robust.html)
(SIGGRAPH 2013) informs an independent solid-angle diagnostic alongside the
existing signed-distance and ray-containment queries. The diagnostic compares
these measurements on unchanged meshes and checks inside/outside box controls,
reversed orientation and translation. It does not replace production acceptance,
choose a new inside/outside policy for intersecting shells or certify the full
animation. No paper implementation, asset or training data is copied, and no
new dependency or model is installed.

The version-pinned [Trimesh 5.1.0 proximity implementation](https://github.com/mikedh/trimesh/blob/5.1.0/trimesh/proximity.py)
uses the nearest triangle's normal when the query projects within that triangle
and ray containment otherwise. This branch distinction informs the next
investigation after signed-distance results disagree with ray and winding
measurements on saved poses. It does not establish mesh validity or justify
switching production semantics without new tests and baseline evaluation.
