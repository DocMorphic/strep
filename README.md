# Strep

Offline game-animation authoring for rigged humanoid characters.

Strep combines an unchanged motion-generation checkpoint with tools for character transfer, clip editing, scene/contact constraints, transitions, previews, and game-engine export. Prompts can describe locomotion, parkour, gestures, dance, combat, everyday tasks, object handling, and interactions. These examples are not an action whitelist.

**Status: active development, not release-ready.** Successful generation or engine import does not establish realistic motion. Contact reliability, calibrated character controls, broad held-out evaluation, and human review remain open work.

## What is here

- A local desktop-style Studio for free-text requests, sequences, previews, and authoring workflows.
- Python motion-processing, retargeting, editing, contact, geometry, and evaluation code.
- Godot import/playback integrations and validation tools.
- Versioned benchmark specifications, research protocols, source/model revisions, and tests.

The first implementation targets rigged 3D humanoids. Single-image reconstruction and automatic rigging are deferred. Training a new model is a possible response to measured limitations; no newly trained Strep checkpoint is being published here.

## Current evidence and limitations

The latest [mesh regression repair](docs/mesh-regression-cuts-v1.md) adds constraints for all 272 new crossing pairs found by the [full-interval audit](docs/rejected-coupled-mesh-v1.md). One internal step reduces the worst violation by 56.68%, but old witness and new projection failures remain. Every tested step of the next direction violates motion limits, so output clips stay unchanged.

The development breadth study generated 390 actor clips across 72 cases, 12 action families, and five seeds. Those categories measure coverage; they do not prove support for every requested motion. Release acceptance remains open in [the release matrix](benchmarks/project-release-v1.json).

An earlier sustained knee-contact experiment imported all 180 frames into Godot, but failed contact near the start and release of the hold and exceeded the sampled 5 mm floor-clearance limit. Its [method and limitations](docs/knee-held-contact-v1.md) are retained. [Box/sphere scene geometry](docs/primitive-scenes-v1.md) spans contact calculations, previews, GLB export and baked playback. [Sphere physics release](docs/sphere-release-v1.md) now passes targeted engine and import checks; the saved example still fails grasp and settling checks. [Grasp fitting studies](docs/sphere-finger-fit-v1.md) still fail strict contact and full-hand collision checks, including after explicit floor placement and bounded finger edits. These are development results, not animator approval.

The [bounded region-grasp correction](docs/sphere-region-upper-return-v1.md) passes sampled contact, geometry, edit-limit and motion-regression comparisons for one authored sphere interaction. This uses an explicit new region condition; it does not solve the original fixed-point grasp or establish general interaction quality.

[Scene region authoring](docs/scene-region-authoring-v1.md) now preserves explicit hand patches and measures distributed contact against boxes and spheres. [Experimental region fitting](docs/scene-region-fitting-v14.md) now produces independently audited candidates: a short sphere repair passes sampled contacts, while box variants still fail. [Studio region editing](docs/studio-region-fitting-v1.md) now saves fitting jobs and separate input/candidate previews with explicit failure reports; [visual grip placement](docs/studio-grip-picking-v1.md) adds draft target previews and picking on moving boxes/spheres. Live browser validation remains pending. Existing point-only solvers reject region requests.

[Root cleanup across eight actions and three rigs](docs/breadth-root-cleanup-v1.md) reduces total root-acceleration energy in 21/24 existing corrected clips while retaining the measured contact/geometry bounds. All 24 selected outputs pass engine imports; only 9/24 return to their original root-peak levels, so this is partial recovery.

[A peak-restoration follow-up](docs/breadth-peak-restore-v1.md) finds three additional alternatives and identifies nine cases where root-only correction cannot satisfy the original peak alongside the declared geometry constraints. Coordinated joint correction remains needed.

[Coordinated root/leg correction](docs/coupled-breadth-conic-v1.md) now retains numerical improvements across all nine diagnosed root-only conflicts after repairing physical step checks. Earlier failures remain recorded. None of the nine original root peaks is restored; full-clip quality remains unresolved.

[Whole-clip correction](docs/coupled-clip-sequence-v1.md) extends this work across 29 selected windows while sharing each clip's original edit budget. Nine exported candidates pass the numerical comparison; original root peaks and usability requirements remain unresolved.

[Between-key floor constraints](docs/half-floor-pilot-v1.md) unlock a further 1.18% numerical improvement in one previously blocked backpedal window, with independent geometry and 600 engine frame checks passing. The original root peak and all seven failing regions remain unresolved; broader replication is still needed.

[Replication across all nine cases](docs/half-floor-population-v1.md) finds an additional benefit in two cases and matching scores in seven, with 6,360 engine actor-frame checks. Studio now includes the full 36-version developer comparison. Original root peaks remain unresolved; no motion-quality approval is inferred.

[Paired corrections in Studio](docs/paired-studio-workflow-v1.md) now preserve exact before/after body and finger motion through saved-scene speed changes and trimming. Four paired versions pass 1,455 shared-scene Godot observations. Fractional collision-sample jumps are repaired; partner and floor failures remain visible.

The owner will perform developer review first. Independent animator review and timed cleanup evidence remain release requirements.

[Between-pose skin bounds](docs/skin-motion-intervals-v1.md) now account for native rotation interpolation and the full rig hierarchy when bounding vertex movement. A three-interval development audit bounds surface separation in one interval and leaves two unresolved. This supplements sampled collision measurements; continuous collision freedom and motion quality remain unproven.

[Adaptive interval checks](docs/adaptive-skin-intervals-v1.md) now combine subdivision, triangle crossings and containment observations. A retained character pose has an independently confirmed surface crossing while both full-vertex depth tests report zero. Full native-clock follow-up records 63 intervals with surface-separation bounds, ten with observed crossings and one unresolved; none of these results approves motion quality.

[Directional motion bounds](docs/skin-taylor-bounds-v1.md) resolve all sixteen previously uncertain subintervals on the same saved paired motion, checking 10,836 triangle pairs. The ten confirmed crossing intervals still require motion repair. This improves between-pose evaluation without changing animations or quality thresholds.

[Triangle-based repair](docs/triangle-hand-repair-v1.md) now targets actual surface crossings under the original motion limits, with a broader editable approach window. Its first trial accepts no change. A separately verified crossing at the protected contact involves finger-dominated triangles, motivating a finger-posture experiment with explicit palm/contact preservation.

[Finger-only correction](docs/finger-triangle-repair-v1.md) now preserves native timing, body/wrist motion and measured palm geometry. Its first trial also accepts no change. A saved-model diagnostic points to older signed vertex constraints as a major restriction; fresh geometry must validate any proposed alternative. The source palm markers remain 22.6 mm apart, so contact quality is still unproven.

[Visual hand-region selection](docs/studio-hand-selection-v1.md) now connects selected hand triangles to saved contact-fitting requests, alongside object grip picking. Mesh identity, all eight skin weights, edit bounds and exported geometry are checked; this currently covers canonical SOMA scenes and is not general grasp or animation-quality approval.

[Decoded finger diagnostics](docs/finger-proposal-replay-v1.md) confirm that a lower solver objective can still worsen actual mesh intersections. The quarter-step proposal passes motion/palm limits but remains rejected: 196 older witness bounds fail and sampled crossing counts rise from 3,344 to 3,346. All 876 minimal source tests pass.

[Mesh checks before accepting corrections](docs/sampled-surface-guard-v1.md) now reject new sampled triangle crossings and deeper directional penetration after the existing motion/contact checks pass. The saved rejected proposal fails at six of fourteen times. All 888 minimal source tests pass; this guards future repairs and does not establish improved animation quality.

[Combined arm/finger repair](docs/coupled-window-repair-v1.md) now targets every observed crossing across fourteen times. The control audit proves that finger-only edits leave 647 pairs unaffected. The combined trial retains the original animation after sixteen constraint failures; exact replay identifies acceleration limits and a precision difference in the unrounded baseline. All 910 minimal source tests pass; interaction quality remains unresolved.

[Serialized feasibility restoration](docs/serialized-feasibility-restoration-v1.md) reduces a rejected candidate's constraint deficit, but still accepts no changed animation. Mesh checks now cover the complete edit interval when a numerically feasible candidate exists. Exact replay points to post-contact finger acceleration as a remaining issue; all 926 minimal source tests pass.

[Independent finger return controls](docs/release-finger-controls-v1.md) produce an internal candidate that passes the original motion-rate and palm limits. Seven surface-witness constraints still fail, so no changed animation is accepted. All 936 distinct minimal source tests pass.

[Witness repair with hard motion limits](docs/hard-motion-witness-restoration-v1.md) narrows the remaining internal failures to three approach constraints. Exact replay and refinement still accept no changed animation; all 955 minimal source tests pass.

## Using this source snapshot

Development currently uses Windows, Python 3.10, NVIDIA CUDA/PyTorch, Node.js for viewer dependencies, and a separately acquired Kimodo installation. Read the [baseline setup runbook](docs/baseline-runbook.md), [pinned source/model revisions](benchmarks/sources.lock.json), and [Studio workflow](docs/action-studio.md). Those documents include historical experiments; a fully verified clean-clone installer is still unfinished.

Model weights, gated text-encoder dependencies, character payloads, third-party source checkouts, environments, and generated study outputs are intentionally absent from this repository. Obtain required dependencies from their publishers under their respective terms. Authentication belongs in the local credential store, never source code.

[Source preparation](docs/source-preparation-v1.md) now fetches and verifies the pinned Kimodo commit before package installation, preserves existing vendor edits, and saves new environment captures under ignored reports. This repairs one clean-clone setup gap; full setup validation remains unfinished.

On an already provisioned development workspace, start Studio from the project root:

```powershell
.venv\Scripts\python.exe scripts/action_studio_server.py
```

Then open `http://127.0.0.1:8768/studio`. Offline inference requires prior acquisition of the pinned dependencies. This repository is not a bundled model download or a hosted generation service.

A [model-free source-check workflow](docs/model-free-source-checks.md) now runs geometry/contact certificates, the Studio build and offline editor tests on Windows and Linux. It needs no model or saved study artifacts; this is not full inference or animation-quality validation.

Some tests require the separately acquired model, rig fixtures, or Godot executable. A full-suite pass on a fresh clone has not been established. Small geometry checks can be run in a provisioned environment with:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_object_geometry.py tests/test_object_geometry_mesh.py -q
```

## Project map

| Path | Purpose |
| --- | --- |
| `scripts/` | Studio, generation orchestration, editing, export, and audits |
| `tests/` | Focused software and integration checks |
| `benchmarks/` | Versioned protocols, release requirements, and source revisions |
| `docs/` | Methods, findings, limitations, and research references |
| `integrations/godot/` | Engine usage and integration notes |
| `assets/` | Dependency manifests and character metadata; payloads acquired separately |

See the [full project goal](docs/project-goal.md), [research plan](docs/research-plan.md), [source ledger](docs/source-ledger.md), and [historical development notes](DEVELOPMENT-HISTORY.md). Historical links into `reports/`, `runs/`, or localhost require the original local artifacts and are not included in this source snapshot.

Completed changes are committed and pushed as development continues. See [the repository workflow](docs/github-workflow.md). Third-party licenses and access requirements remain separate from this repository's public visibility.
