# Strep

Offline game-animation authoring for rigged humanoid characters.

Generate editable clips from action descriptions and timed sequences, transfer motion to character rigs, edit clips and contacts, preview scenes, and prepare game-engine assets. Locomotion, parkour, ground movement, gestures, dance, combat, everyday tasks, object handling and partner interactions are evaluation categories, never a prompt whitelist.

**Active development; not release-ready.** The unchanged generation checkpoint is the baseline. Successful generation, a numerical correction or an engine import does not establish realistic motion. The [single full-project goal](docs/project-goal.md) stays active until the [release requirements](benchmarks/project-release-v1.json) are actually met.

## Current work

- [Automatic export repair in fitting](docs/native-fit-storage-v1.md): the public surface fitter loads original-bound corrected starts, repairs export-only failures and keeps authored speed limits. All 218 distinct affected local checks pass across the recorded runs. Independent reconstruction replays all 62 exports; the final humanoid clip passes native motion checks but still fails floor contact at 45.56 mm peak.

- [Stored-key surface continuation](docs/native-storage-continuation-v1.md): corrected starts retain the original source, motion limits and explicit Float32 adjustments. The [completed development trials and replays](docs/kenney-kick-stored-surface-v1.md) retain a motion-compliant export but still fail floor contact at 47.35 mm peak. Fresh screening separates storage errors from intended-motion failures. All 712 focused Python checks per OS pass; no animation approval.

- [Native rate receipt inspection](docs/native-rate-receipts-v1.md): a standard-library tool locates recorded failed joints and time stencils without loading a model. Six focused tests pass; all 22 retained timing receipts are inspected with complete counts. This is archive inspection, not new motion or geometry validation.

- [Bounded stored rotation repair](docs/native-rotation-storage-search-v1.md): the planner covers all four source-rate failures and uses permitted rotation ancestors and two/three-sample interpolation support. The [completed positional-storage study](docs/kenney-kick-position-storage-v1.md) repairs the kick's native export error with eight one-neighbor components. Complete replay passes native conditions; floor penetration still fails and the variant stays unapproved.

- [Timing capacity in Studio](docs/studio-timing-capacity-v1.md): selected tracks and interior times now preview the whole scene's control count. Oversized saves preserve prior character bounds and speed limits. The offline editor checks pass and the desktop bundle matches source; this does not approve motion quality. The [controlled timing-layout study](docs/kenney-kick-temporal-layout-v1.md) improves floor correction with additional times but accepts no changed export.

- [Candidate-centered surface repair](docs/native-surface-recentered-v1.md): an optional repair rebuilds around rejected exports while retaining original motion limits and accepted contact/geometry bounds. All 208 distinct affected checks pass locally, and 635 focused checks per OS pass on Windows/Linux. The complete-clock development trial finishes without a repair direction or accepted correction. The [feasible-origin kick and paired storage screen](docs/kenney-kick-cold-fit-v1.md) retain failures in both existing storage modes.

- [Native endpoint sampling](docs/native-endpoint-sampling-v1.md): rotation and translation previews now match scalar decoder behavior near Float32 clip edges. All 127 affected checks pass locally; the retained kick's complete-clock matrix discrepancy drops below 4.45e-15. Restoration and motion approval remain separate.

- [Root-fixed kick correction](docs/kenney-kick-root-fixed-v1.md): the full 2,017-time trial finishes without an accepted correction. Added knee/foot/toe permissions produce a passing static pose, but both actual clip mappings fail unchanged motion/floor checks. All 552 affected checks per OS pass at e7aced8; no motion approval.

- [Seven-action native export and skin-encoding audit](docs/kenney-native-export-v1.md): all 1,020 original keys on the independent Kenney rig reach scene and game packages, with failed floor and current-speed decisions preserved. The new read-only audit separates pose and packed-weight effects; 34 affected checks pass locally. No motion or release approval.

- [Rotation-speed fitting](docs/native-rotation-speed-fit-v1.md): authored joint-speed limits now constrain native scene fitting and fresh serialized-output checks. A bounded smoothing proposal must pass every original scene row before adoption. Optional limits now integrate with the [Studio correction editor](docs/studio-rotation-speed-v1.md), with 37 targeted cases and editor source checks passing. Scene and game packages now retain policies, audits and ancestor decisions. All 517 focused Python checks per OS and editor checks pass on Windows/Linux. Live UI and continuous-time/engine verification remain pending.
- [Static prop and grip API](docs/static-prop-api-v1.md): original GLB geometry and immutable triangle-based selections now import, preview, save and download through Studio routes. All 262 focused CPU checks pass on both OS platforms. Mesh-prop solver/UI integration remains pending.

- [Contact audit compatibility](docs/contact-audit-compatibility-v1.md): the broad source workflow passes all 12 Windows/Linux jobs at its tested commit. Captured proposal production and independent geometry/rate replay are complete; their failures remain visible.

- [Rig-proportion pose scaffold](docs/rig-pose-scaffold-v1.md): production and separate replay cover all 2,422 captured keys. Both complete clips still fail floor checks; crawl peak depth worsens to 0.673 m. The large crawl rotation jump already exists in captured-relative motion and cannot be removed within the unchanged edit caps. Originals remain selected, without quality or training approval.

- [Pose-target reach preflight](docs/pose-length-preflight-v1.md): box/norm/continuation fitters now reject incompatible fixed-distance targets without changing source poses or tolerances. All 48 focused checks pass. The actual fitter excludes all 2,422 uniformly scaled captured poses; separate replay checks 58,128 invariant-pair rows and every retained local pose. Rig proportions must be accounted for before support/contact fitting; no corrected animation or training target is promoted.

- [Captured reference transfer](docs/acclaim-rig-transfer-v1.md): an explicit ASF/AMC-to-rig path retains every capture frame and existing target animations/payloads. All 65 focused checks pass. Both full captured clips transfer and independently replay, but fail native-key floor checks (1,480/1,524 crawl keys; 446/898 get-up keys), with large mapped head/hand errors. Positional fitting and support correction remain necessary; no clean-target or training admission.

- [Captured ground-motion references](docs/cmu-ground-reference-v1.md): two CMU clips now preserve all 2,422 frames at 120 Hz, with 47 importer checks and complete separate transform reconstruction passing. They supply skeletal reference motion for support-pose planning; target fitting, contacts and training admission remain pending.

- [Selected body-pose guides](docs/selected-joint-guides-v1.md): the composer/request adapter can guide knees, head, pelvis and other SOMA30 joints individually. Real CPU/CUDA mask assembly and four unchanged-checkpoint clips verify condition delivery, but 0/4 clips passes the provisional guide-error screen. Body controls remain experimental; exact targets, collision and plausible motion require further work.

- [Paired ground-motion proposals](docs/ground-proposals-v1.md): all 30 crawl/get-up clips generate and transfer, but none passes the full floor condition. Separate skinning arithmetic reproduces all 75,750 target sample depths and classifications across 77.9 million vertex positions. Sparse root guides and clearance wording yield mixed results; no replacement is promoted. Next work requires explicit whole-body/contact targets or scene-conditioned editing, with genuine review.

- [Rig-transfer and ground-motion failures](docs/kenney-ground-scenes-v2.md): seven development motions transfer to a licensed Kenney test rig and independently replay, but four fail the declared floor screen. Expanded clocks retain 10,608 times and 10.9 million vertex evaluations. A [complete plane-envelope correction trial](docs/kenney-crawl-plane-envelope-v2.md) clears the earlier capacity failure, then stops at the execution limit without accepting a changed export. All 28 changed proposals violate original motion caps; the original remains selected. Three-step decoded restoration also stops without an accepted correction; 36 completed geometry probes fail. [Atomic iteration receipts](docs/native-surface-iteration-trace-v1.md) now retain solver diagnostics on future interruptions, with 224 affected checks passing. These cases measure a general authoring path; they do not restrict supported prompt vocabulary.

- [Engine-aware held-contact correction](docs/engine-hold-clearance-v1.md): the two-wrist candidate passes all 48,520 raw rotation-cap conditions while preserving the other 152 channels and static rig. Complete-body production and independent replay pass all 2,426 times; conditional force/contact replay passes all 59 assessed samples. Native-authoring playback passes, while the 30 FPS glTF import fails combined accuracy, including 12 geometry samples. The bake-rate comparison and independent complete geometry replay now finish for 60, 120 and 240 FPS. At the same finite query times, 120 and 240 FPS pass the unchanged 0.10-mm skin and 5-mm geometry limits; 30 and 60 FPS fail combined accuracy. This one fixture does not establish a universal bake rate, continuous-time fidelity or broader animation quality.

- [Complete scene engine replay and engine-aware correction inputs](docs/native-scene-engine-replay-v1.md): independent full-mesh arithmetic confirms the earlier geometry failures in both import and native-resource modes. The full-vertex diagnostic identifies unsigned-16 weight storage as the largest displacement contributor in that recorded comparison. An observed-engine skin view carries raw weights into solver contact and complete geometry calculations without rewriting the rig; nine focused checks pass. Actual-study validation matches every vertex at all 2,426 times against sum/matmul reconstruction. Completed bake-rate evidence for the subsequent corrected clip is linked above; earlier failures remain preserved.

- [Source-versus-edit floor diagnostics](docs/prompt-edit-floor-regions-v2.md): 15 focused tests pass and five retained editing takes are measured without regeneration. Dance edits introduce floor violations; jump sources already have protected violations and gain additional failures inside the editable section. All five outputs remain failed screens. Studio now distinguishes these counts for new reports and names the assumed floor; live rendering of the added message remains unverified.

- [Complete-body geometry replay](docs/protected-hold-transitions-v1.md): the departure candidate passes all 2,426 declared times against both original spheres. Independent primitive-skin/SVD replay checks all 175,196,016 triangle/object queries and every saved array under the unchanged limits. Fresh contact-force arithmetic is also independently replayed; engine, broader-action and human-quality evidence remain required.

- [Reuse complete geometry for fresh contact forces](docs/reusing-complete-geometry.md): exact full-population, source, clock and loaded-topology checks reject incomplete or changed evidence. Actual skin/contact forces are measured again, retaining geometry failures. Forty-six distinct focused checks pass across the recorded runs. Broader rig/scene evidence remains required; see the complete-body development replay above.

- [Contact and protected-hold transitions](docs/protected-hold-transitions-v1.md): the verified departure trial lowers full-clock left forearm/hand relative rate peaks from 881/1141 to 584/1094 degrees/s. All 48,520 original artist cap conditions pass; the hand hold matches exactly at all 1,159 contact times. Independent complete-forearm checks cover 54 changed times plus exact unchanged-time identity to earlier evidence for 2,372 times. A follow-up verified fit adds approximately 5 micrometres of departure clearance reserve under the same acceptance limit; this does not establish engine robustness. Broader physics, continuous dynamics, engine and human quality remain unapproved; the full-project goal stays active. [Earlier finger/hand failures](docs/middle-ring-clearance-curves-v1.md) remain preserved.

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

The [public source-check workflow](docs/model-free-source-checks.md) declares 465 Python test modules and 42 Node suites on Linux and Windows, plus separate native CPU fixture jobs. It does not need motion checkpoints or local study outputs. Inference, engine, full-system and human-quality evaluation are separate. Some additional tests need acquired model/rig fixtures or Godot; a full fresh-clone suite pass is not established.

| Path | Contents |
|---|---|
| `scripts/` | Studio, generation orchestration, editing, export and audits |
| `tests/` | Software and integration checks |
| `benchmarks/` | Protocols, acceptance requirements and source revisions |
| `docs/` | Methods, findings, limitations and references |
| `integrations/godot/` | Engine integration |
| `assets/` | Dependency manifests and character metadata |

The [development history](DEVELOPMENT-HISTORY.md) preserves earlier entry-point snapshots; [the goal record](docs/project-goal.md) retains detailed progress. Links into ignored `reports/`, `runs/` or localhost require the original local artifacts. Validated changes are committed and pushed under the [repository workflow](docs/github-workflow.md). Public visibility does not change third-party licenses or access requirements.
