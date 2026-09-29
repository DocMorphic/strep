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

The development breadth study generated 390 actor clips across 72 cases, 12 action families, and five seeds. Those categories measure coverage; they do not prove support for every requested motion. Release acceptance remains open in [the release matrix](benchmarks/project-release-v1.json).

An earlier sustained knee-contact experiment imported all 180 frames into Godot, but failed contact near the start and release of the hold and exceeded the sampled 5 mm floor-clearance limit. Its [method and limitations](docs/knee-held-contact-v1.md) are retained. [Box/sphere scene geometry](docs/primitive-scenes-v1.md) spans contact calculations, previews, GLB export and baked playback. [Sphere physics release](docs/sphere-release-v1.md) now passes targeted engine and import checks; the saved example still fails grasp and settling checks. [Grasp fitting studies](docs/sphere-finger-fit-v1.md) still fail strict contact and full-hand collision checks, including after explicit floor placement and bounded finger edits. These are development results, not animator approval.

The [bounded region-grasp correction](docs/sphere-region-upper-return-v1.md) passes sampled contact, geometry, edit-limit and motion-regression comparisons for one authored sphere interaction. This uses an explicit new region condition; it does not solve the original fixed-point grasp or establish general interaction quality.

[Scene region authoring](docs/scene-region-authoring-v1.md) now preserves explicit hand patches and measures distributed contact against boxes and spheres. [Experimental region fitting](docs/scene-region-fitting-v14.md) now produces independently audited candidates: a short sphere repair passes sampled contacts, while box variants still fail. [Studio region editing](docs/studio-region-fitting-v1.md) now saves fitting jobs and separate input/candidate previews with explicit failure reports; [visual grip placement](docs/studio-grip-picking-v1.md) adds draft target previews and picking on moving boxes/spheres. Live browser validation remains pending. Existing point-only solvers reject region requests.

[Root cleanup across eight actions and three rigs](docs/breadth-root-cleanup-v1.md) reduces total root-acceleration energy in 21/24 existing corrected clips while retaining the measured contact/geometry bounds. All 24 selected outputs pass engine imports; only 9/24 return to their original root-peak levels, so this is partial recovery.

[A peak-restoration follow-up](docs/breadth-peak-restore-v1.md) finds three additional alternatives and identifies nine cases where root-only correction cannot satisfy the original peak alongside the declared geometry constraints. Coordinated joint correction remains needed.

The owner will perform developer review first. Independent animator review and timed cleanup evidence remain release requirements.

## Using this source snapshot

Development currently uses Windows, Python 3.10, NVIDIA CUDA/PyTorch, Node.js for viewer dependencies, and a separately acquired Kimodo installation. Read the [baseline setup runbook](docs/baseline-runbook.md), [pinned source/model revisions](benchmarks/sources.lock.json), and [Studio workflow](docs/action-studio.md). Those documents include historical experiments; a fully verified clean-clone installer is still unfinished.

Model weights, gated text-encoder dependencies, character payloads, third-party source checkouts, environments, and generated study outputs are intentionally absent from this repository. Obtain required dependencies from their publishers under their respective terms. Authentication belongs in the local credential store, never source code.

On an already provisioned development workspace, start Studio from the project root:

```powershell
.venv\Scripts\python.exe scripts/action_studio_server.py
```

Then open `http://127.0.0.1:8768/studio`. Offline inference requires prior acquisition of the pinned dependencies. This repository is not a bundled model download or a hosted generation service.

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
