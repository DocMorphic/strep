# Strep

Offline game-animation authoring for rigged humanoid characters.

Generate editable clips from action descriptions and timed sequences, transfer motion to character rigs, edit clips and contacts, preview scenes, and prepare game-engine assets. Locomotion, parkour, ground movement, gestures, dance, combat, everyday tasks, object handling and partner interactions are evaluation categories, never a prompt whitelist.

**Active development; not release-ready.** The unchanged generation checkpoint is the baseline. Successful generation, a numerical correction or an engine import does not establish realistic motion. The [single full-project goal](docs/project-goal.md) stays active until the [release requirements](benchmarks/project-release-v1.json) are actually met.

## Current work

- [Conditional object-contact forces](docs/contact-force-balance-v1.md): friction, total-force budgets and complete force/torque replay on immutable object tracks. A matched finite-span grip study verifies 157 conditional force witnesses; actual skinned grasp, human strength and whole-body dynamics remain unverified. All 82 focused checks pass.
- [Contact correction](docs/contact-search-comparison-v2.md): keep the independently verified 0.03 continuation with 14/21 attempted windows and contact passes still 0/62. The new frames 87–89 candidate has completed production checks; independent geometric replay is pending, so it has not replaced that state.
- [Solver conditioning](docs/contact-conic-conditioning-v1.md): removing 727 exact duplicate cones still fails the original checks. Failed/deferred results remain recorded, and acceptance tolerances stay unchanged.
- [Regression integrity](docs/conic-fixture-integrity-v1.md): corrected a synthetic fixture that altered solver coordinates after solving. All 135 focused checks pass; hosted CI for the fix remains separate and pending.

All fourteen release capabilities remain unapproved, with 19 inventory gaps and four unfrozen numerical gates. Broad held-out evaluation, calibrated capability/style controls, genuine human ratings and timed cleanup remain required. The owner plans developer review first; those ratings are not yet supplied.

## Use the development workspace

Development uses Windows, Python 3.10, NVIDIA CUDA/PyTorch, Node.js for viewers and a separately acquired Kimodo installation. Start with the [setup runbook](docs/baseline-runbook.md), [pinned source/model revisions](benchmarks/sources.lock.json), [source preparation](docs/source-preparation-v1.md) and [Studio workflow](docs/action-studio.md). Dated study documents describe their own checkpoints. A fully verified clean-clone installer is unfinished.

On an already provisioned workspace, start Studio from the project root:

```powershell
.venv\Scripts\python.exe scripts/action_studio_server.py
```

Open `http://127.0.0.1:8768/studio`. Offline inference requires prior acquisition of dependencies and models. Weights, gated text-encoder dependencies, character payloads, third-party checkouts, environments and generated study outputs are absent from this repository. Obtain them from their publishers under their terms; keep authentication in local credential stores.

## Authoring and evaluation

| Workflow | Entry point |
|---|---|
| Action prompts and timed sequences | [Action Studio](docs/action-studio.md) |
| Character and style controls | [Motion profiles](docs/motion-profile-v1.md), [scene actor profiles](docs/scene-motion-profiles-v1.md) |
| Rig and clip edits | [Rig joint editing](docs/rig-joint-editing-v1.md), [local edit preservation](docs/local-edit-preservation-v1.md) |
| Object and partner contacts | [Scene drafts](docs/studio-native-scene-v1.md), [character correction](docs/studio-native-scene-fit-v1.md) |
| Root motion, events and engine assets | [Game tracks](docs/native-scene-game-tracks-v1.md), [finite Godot playback](docs/native-scene-runtime-v1.md) |
| Developer ratings and actual cleanup | [Breadth review](docs/developer-packet-review-v1.md), [human review](docs/human-review-v1.md) |
| Methods, licensing and release criteria | [Research plan](docs/research-plan.md), [source ledger](docs/source-ledger.md), [release matrix](benchmarks/project-release-v1.json) |

These development workflows retain failures and their stated limits. Scene contacts require explicit geometry and targets; hypothetical force caps are not calibrated gameplay strength statistics. Image reconstruction and automatic rigging are deferred.

## Source checks

The [public source-check workflow](docs/model-free-source-checks.md) declares 427 Python test modules and 41 Node suites on Linux and Windows, plus separate native CPU fixture jobs. It does not need motion checkpoints or local study outputs. Inference, engine, full-system and human-quality evaluation are separate. Some additional tests need acquired model/rig fixtures or Godot; a full fresh-clone suite pass is not established.

| Path | Contents |
|---|---|
| `scripts/` | Studio, generation orchestration, editing, export and audits |
| `tests/` | Software and integration checks |
| `benchmarks/` | Protocols, acceptance requirements and source revisions |
| `docs/` | Methods, findings, limitations and references |
| `integrations/godot/` | Engine integration |
| `assets/` | Dependency manifests and character metadata |

The [development history](DEVELOPMENT-HISTORY.md) preserves earlier entry-point snapshots; [the goal record](docs/project-goal.md) retains detailed progress. Links into ignored `reports/`, `runs/` or localhost require the original local artifacts. Validated changes are committed and pushed under the [repository workflow](docs/github-workflow.md). Public visibility does not change third-party licenses or access requirements.
