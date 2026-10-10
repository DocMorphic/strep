# Strep

Offline game-animation authoring for rigged humanoid characters.

Generate editable clips from action descriptions and timed sequences, transfer motion to character rigs, edit clips and contacts, preview scenes, and prepare game-engine assets. Locomotion, parkour, ground movement, gestures, dance, combat, everyday tasks, object handling and partner interactions are evaluation categories, never a prompt whitelist.

**Active development; not release-ready.** The unchanged generation checkpoint is the baseline. Successful generation, a numerical correction or an engine import does not establish realistic motion. The [single full-project goal](docs/project-goal.md) stays active until the [release requirements](benchmarks/project-release-v1.json) are actually met.

## Current work

- [Complete-body geometry replay](docs/protected-hold-transitions-v1.md): the departure candidate passes all 2,426 declared times against both original spheres. Independent primitive-skin/SVD replay checks all 175,196,016 triangle/object queries and every saved array under the unchanged limits. Fresh force, engine, broader-action and human-quality evidence remain required.

- [Reuse complete geometry for fresh contact forces](docs/reusing-complete-geometry.md): exact full-population, source, clock and loaded-topology checks reject incomplete or changed evidence. Actual skin/contact forces are measured again, retaining geometry failures. Forty-six distinct focused checks pass across the recorded runs; production-character complete-body evidence remains required.

- [Contact and protected-hold transitions](docs/protected-hold-transitions-v1.md): the verified departure trial lowers full-clock left forearm/hand relative rate peaks from 881/1141 to 584/1094 degrees/s. All 48,520 original artist cap conditions pass; the hand hold matches exactly at all 1,159 contact times. Independent complete-forearm checks cover 54 changed times plus exact unchanged-time identity to earlier evidence for 2,372 times. A follow-up verified fit adds approximately 5 micrometres of departure clearance reserve under the same acceptance limit; this does not establish engine robustness. Full-body, continuous dynamics, engine and human quality are unapproved; the full-project goal stays active. [Earlier finger/hand failures](docs/middle-ring-clearance-curves-v1.md) remain preserved.

- [Complete action retrieval](docs/full-development-retrieval-v1.md): 390 clips across 72 cases/twelve families compete against 78 descriptions. Intended descriptions rank first for 295 clips; all 30,420 score cells independently replay. Twenty-seven source checks pass. The [fixed contact sweep](docs/contact-windows-90-101-v1.md) independently verifies all 21 windows with none remaining; original physical contact passes remain 0/62. The [new central hand-material study](docs/central-hand-contact-v1.md) tests explicit surface references without relabeling that failed fixture.

- Earlier [small-bank action retrieval](docs/text-motion-retrieval-v1.md): all 52 original development clips across twelve families are scored; 48 rank their intended description first. Handshake-role confusions remain visible. Eighteen checks and all 676 score calculations pass; physical/human quality remains unapproved.

- [Saved proposal history](docs/conic-margin-hydration-v1.md): primary-only rejected attempts retain their own solver phases when a later fallback solves twice. All 261 focused numerical/native fixture checks pass; strict original full affine replay now passes; fresh contact continuation remains separate.

- [Supplied-GLB body demands](docs/rig-articulated-dynamics-v1.md): explicit COM/body-axis tracks and immutable articulated diagnostics now sample original rig clips. All 64 focused checks pass; actual humanoid body profiles, reaction allocation and calibrated capacities remain unverified.

- [Scene mechanics study](docs/scene-mechanics-study-v1.md): full supplied-humanoid/sphere geometry independently replays, while original forces/grips fail all 59 assessed samples. Separately rotated equatorial targets admit 59/59 conditional force witnesses under identical budgets; actual new hand contact and animation remain unverified.

- [Explicit joint demand](docs/articulated-motion-dynamics-v1.md): rigid-body-tree forces/torques, original connected anchors and floating-root balance under supplied body properties and external wrenches. All 38 focused checks pass. Human capacities, rig-to-body conversion and contact allocation remain unverified; [the model decision record](docs/scene-model-next-steps-v1.md) sets the next comparisons.

- [Supplied-rig scene forces](docs/scene-contact-forces-v1.md): actual skin contact and complete sampled geometry now accompany explicit object COM/inertia, friction and force budgets. All 95 focused checks pass. Hypothetical caps remain separate from calibrated human strength and whole-body dynamics; [the earlier force study](docs/contact-force-balance-v1.md) remains scoped to conditional witnesses.
- [Contact correction](docs/contact-windows-111-116-v1.md): independently verified frames 111–113 join the 0.03 continuation; the 114–116 attempt is rejected. Coverage advances to 17/21 attempted windows with four remaining. Existing passing checks and poses outside each edited window are preserved; contact passes remain 0/62.
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

The [public source-check workflow](docs/model-free-source-checks.md) declares 431 Python test modules and 41 Node suites on Linux and Windows, plus separate native CPU fixture jobs. It does not need motion checkpoints or local study outputs. Inference, engine, full-system and human-quality evaluation are separate. Some additional tests need acquired model/rig fixtures or Godot; a full fresh-clone suite pass is not established.

| Path | Contents |
|---|---|
| `scripts/` | Studio, generation orchestration, editing, export and audits |
| `tests/` | Software and integration checks |
| `benchmarks/` | Protocols, acceptance requirements and source revisions |
| `docs/` | Methods, findings, limitations and references |
| `integrations/godot/` | Engine integration |
| `assets/` | Dependency manifests and character metadata |

The [development history](DEVELOPMENT-HISTORY.md) preserves earlier entry-point snapshots; [the goal record](docs/project-goal.md) retains detailed progress. Links into ignored `reports/`, `runs/` or localhost require the original local artifacts. Validated changes are committed and pushed under the [repository workflow](docs/github-workflow.md). Public visibility does not change third-party licenses or access requirements.
