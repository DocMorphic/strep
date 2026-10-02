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

[Studio now offers between-key refinement](docs/studio-sampled-support-v1.md) with bound starting/final proposals and unchanged input-retention feedback. The [crawl hand/shin diagnostic](docs/crawl-body-contact-probes-v1.md) records the existing mesh-contact workflow's failed first pilot and its next trajectory experiment.

[Coupled mesh-contact fitting](docs/crawl-body-contact-coupled-v1.md) now anticipates explicit hand/body targets. Its first crawl candidate still fails contact and floor checks and retains the input; actual Godot import reproduces those failures.

[Floor-guarded contact feasibility](docs/crawl-body-contact-feasibility-v1.md) restores the crawl floor screen and preserves it while pursuing contact targets. The hand targets still fail, with the original retained; between-frame and actual Godot checks preserve this distinction.

[Guarded contact trials](docs/crawl-body-contact-guarded-trials-v1.md) reduce the same crawl's worst target error, but regress an already passing contact and still fail acceptance. Dense playback reveals a between-key floor violation; the mesh-fitting export path now checks decoded subframes before accepting a candidate.

[Playback floor guards](docs/crawl-body-contact-playback-guards-v1.md) now retain the floor limit during sampled playback and protect an already passing contact at authored keys. Other contacts, the full-frame hold and two intermediate serialized contact checks still fail; the original remains selected.

[Explicit contact clocks](docs/mesh-contact-clock-v1.md) distinguish authored-key targets from full-frame holds and independently reject exported contact failures. The [completed full-frame crawl study](docs/crawl-body-contact-frame-hold-v1.md) preserves the sampled floor and passing hold across all 55 independently decoded retained proposals. Three other contacts still fail, and the original remains selected.

[Playback contact fitting is now available in Studio](docs/studio-mesh-playback-v1.md) for finite clips, with explicit contact timing, saved fitting budgets, decoded diagnostics and preserved failed candidates. Loops retain the existing cycle fitter; passing sampled geometry does not approve motion quality.

[Individual interval timing](docs/mesh-interval-clocks-v1.md) now combines sustained holds and authored-key targets in one clip. Saved choices survive interval edits and deletion; independent checks on three existing crawl rigs reproduce the failures without substituting contact meanings.

[Contact timing through edits](docs/mesh-contact-timing-edits-v1.md) preserves surviving choices through trim, speed, pose and marker edits. Joins, loops and mirrors retain timing with review targets; blended or reflected targets still need re-authoring and fitting.

[Bone-region drafts](docs/rig-patch-selection-v1.md) help select contact vertices on supplied rigs, with optional child bones and a box at the displayed pose. Explicit preview/apply and oversized-region rejection preserve author control; deformation weights do not establish anatomical contact surfaces.

[Between-key support refinement](docs/native-support-sampled-repair-v1.md) repairs the measured dance/get-up contact-bound failures with exact replay and actual engine checks. All final motion-rate selections still fail and inputs remain retained; the option is available in Studio and the CLI.

[Explicit Studio rig preparation](docs/studio-support-preparation-v1.md) keeps original and derived clips separate and measures tiny static-scale changes before fitting. [Broader support diagnostics](docs/native-support-action-breadth-v1.md) cover six existing development actions on three assets; failed authoring, support and rate checks remain visible.

[Native foot-support intervals](docs/native-support-intervals-v1.md) now connect to [Studio authoring and native previews](docs/studio-native-support-v1.md), with explicit rig mappings, static support planes and unchanged free phases. Failed and unreachable corrections retain their inputs and diagnostics. An experimental [joint support/rate search](docs/native-support-joint-rates-v1.md) reduces diagnostic error but still fails the rate screen, including at a larger recorded budget. A bounded [knee-plane/swivel search](docs/native-support-swivel-v1.md) adds native bend-plane freedom, but its completed four-trial study also fails the unchanged rate screen. A [bounded foot-orientation search](docs/native-support-orientation-v1.md) now saves replayable controls; four actual GLBs reproduce byte-for-byte, but combined rate acceptance still fails. A [serialized feasibility repair](docs/native-support-feasibility-v1.md) lowers worst normalized violations with preserved exports and controls; its best larger-budget trial still fails seven rate rows. An opt-in [quantized-key repair](docs/native-support-quantized-v1.md) preserves chained evidence and exact replay; all four seeds still fail acceptance. A bounded coordinate diagnostic reduces the closest seed to three failing speed rows. [Coordinate repair is now integrated into audited jobs](docs/native-support-coordinates-v1.md); its four warm starts use one source clip and rig. One of four completed trials now passes the sampled job screen and replays exactly, but its stricter absolute-peak guard still fails and stationary sole contact remains unverified. General feasibility and quality approval remain open.

[Native knee smoothing](docs/native-leg-smoothing-v1.md) reduces the added leg-rate excess on the matched floor-correction case while retaining sampled floor, hand contact and native engine timing. An imported-skin stance audit also bounds the foot regions' lowest points to 5 mm at all 642 samples per actor. Original rate limits and full-clip absolute peak guards still fail; the input, minimal lifts and smoothed lifts are available as an unapproved Studio comparison.

A [checkpoint selector for contact fitting](docs/checkpoint-guard-contact-v1.md) preserves feasible intermediate proposals after float32 serialization. On the matched case, it lowers actor A's selected objective by 77.31% over the previous export without changing the optimizer trajectory. All 53 sampled mesh checks and source-anchored peak guards pass, but original rate limits still fail, failure counts are mixed, and several peaks regress against the previous alternative. Six comparison GLBs pass offline loader checks. [Native engine validation](docs/native-engine-contact-v1.md) now exposes millimetre errors from default fixed-rate import. Saved/reloaded native-key Godot resources repair sampled poses and event contact, but ordinary AnimationPlayer seeking still snaps one near-end time. A separate [native-track authoring seek](docs/native-authoring-seek-v1.md) passes the unchanged pose and clock audit at all 642 samples per actor; runtime playback and event dispatch remain separate. [Imported skin and GPU checks](docs/native-skin-gpu-v1.md) now pass 84 sampled views with six detected bad-bind controls. Quantized imported weights still meet the authored contact and all 53 discrete mesh checks; floor and motion-rate failures remain. [Native comparisons in Studio](docs/studio-native-contact-review-v1.md) now preserve exact event times and export asset-bound developer observations. Browser rendering, human quality and release approval remain unverified.

A [leg-only native floor correction](docs/native-leg-floor-v1.md) removes up to 10.664 mm penetration at all 642 full-clip samples per actor while retaining root and hand motion. Actual native authoring/GPU checks pass, but knee-rate regressions increase original cap failures. Studio retains it as an experimental comparison with those failures visible.

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

The [Kimodo adapter feasibility audit](docs/kimodo-adapter-feasibility-v1.md) now verifies finite gradients for small frozen-base adapters on the acquired checkpoint within the local GPU's memory. It performs no training updates and establishes no motion-quality improvement; reviewed licensed correction data and an evaluated trainer remain necessary.

[Native target and denoising checks](docs/kimodo-denoising-targets-v1.md) now verify motion reconstruction and 54 conditional gradient cases across seven developed actions. A source-bound developer-review packet records 220 contact disagreements; its examples remain unapproved for training. Separate CPU adapter/target tests now run in CI without model weights.

[Adapter save and resume](docs/kimodo-adapter-lifecycle-v1.md) now reproduces interrupted numerical updates exactly on the frozen Kimodo base, including optimizer state and Torch random inputs. The local canary uses synthetic targets; it establishes no motion-quality improvement or training-data approval. Checkpoint lifecycle tests join the separate CPU CI jobs.

[Reviewed correction preparation](docs/kimodo-training-corpus-v1.md) now requires source-bound human decisions, complete contact labels and correction-specific rights evidence before producing development targets. Reserved release prompts/seeds and source-group split leakage are rejected. The existing review packet remains unreviewed; no real targets have been admitted or motion model trained.

[Native correction packing](docs/native-correction-packing-v1.md) exports an authored NPZ window and a complete on/off foot-contact schedule into that correction format without custom Python. Model suggestions stay separate from unknown annotation fields, and exported files remain unapproved until actual review and rights evidence are supplied.

[Verified corpus reading](docs/kimodo-corpus-reader-v1.md) checks pinned manifests, review/evidence files, development splits and exact re-encoding before exposing targets to a trainer. New V2 manifests bind submission and reservation files explicitly; no real corpus has passed admission and no animation-quality improvement is claimed.

[Studio developer correction review](docs/studio-correction-review-v1.md) now records segment decisions, explicit contact intervals, measured cleanup time and source-bound permission evidence. Original grey reference playback is separate from externally authored candidate review; saving does not admit training data or approve release quality.
