# Primary-source ledger

Checked 2026-09-24 unless marked otherwise. Preserve license files with assets and review the complete terms before distribution.

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
| [CMU mocap](https://mocap.cs.cmu.edu/) | Handoff reports commercial inclusion with raw resale prohibition; website fetch failed during this session. Exact training use and attribution remain unverified; no CMU data acquired. |
| [Uni-Inter](https://arxiv.org/abs/2511.13032) | Research precedent carried forward from handoff; not re-reviewed or integrated here. |
| [MotionFix](https://motionfix.is.tue.mpg.de/) | Clip-editing precedent carried forward from handoff; not re-reviewed or integrated here. |

`benchmarks/sources.lock.json` records public revision identifiers, not downloaded weights. Before running, download those exact revisions, verify checksums, and freeze package versions. Code currently resolves Hugging Face names without a revision argument, so using a model display name alone is insufficient for an immutable run.


## 2026-09-26: independent rig assets

- Quaternius Universal Base Characters: https://quaternius.com/packs/universalbasecharacters.html and https://quaternius.itch.io/universal-base-characters . Free Standard archive acquired via official page; included license CC0-1.0. Original archive, selected source files, SHA-256 and explicit missing-texture substitutions retained in assets/characters/quaternius-base. No raw motion training dataset acquired.
- RiggedFigure: KhronosGroup/glTF-Sample-Assets revision c6a6bd13ab2b3c685c7903d03561b8a9392f38b8, Models/RiggedFigure; pinned README credits Cesium under CC BY4.0. Shares existing rig family.
- RobotExpressive: mrdoob/three.js revision1af6de5bd8cd481993483dc6127eba668e818dfd, examples/models/gltf/RobotExpressive; pinned README credits Tomas Laulhe/Quaternius under CC0 with Don McCurdy modifications. Original preserved and unsupported; compatibility/format failures documented.


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
