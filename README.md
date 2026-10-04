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

[Explicit contact revisions in Studio](docs/native-contact-revision-v1.md) now stage source and partner patches, show original/new references and endpoint positions, recheck sources before Apply, and retain the original draft and all authoring bounds. Four development replays and an actual eight-stage CPU Godot fixture preserve provenance and failed decisions. This authoring workflow does not correct the retained motion-quality failures; character-only asset building remains open.

[Contact-region review](docs/native-contact-region-review-v1.md) preserves original motion and targets while measuring declared mesh regions at every contact time. Four development reviews show that a passing high-five point condition can still place the point 51.7 mm inside the region's supporting plane. Persistent alternatives remain explicit author choices; they do not establish anatomical contact, collision freedom or motion quality.

[Decoded source-bound restoration](docs/native-scene-decoded-restoration-v1.md) tightens proposal caps using measured serialization and nonlinear errors, while retaining the original final motion limits. A retained high-five now accepts four safe sampled steps and reduces hand separation from 206 mm to 178 mm; the 30 mm contact target still fails.

[Source-bound continuation](docs/native-scene-resume-v1.md) resumes a completed native scene proposal by replaying its controls against the exact original actors and limits. Sixteen further accepted steps reduce the retained high-five separation from 178 mm to 77 mm while preserving sampled source rates; the 30 mm contact target still fails. It checks byte-exact exports and decoded source safety before further fitting; it does not rebuild motion caps from an edited clip or restore optimizer internals.

[Explicit scene placement](docs/native-scene-stage-v1.md) keeps native clip bytes and fixed world planes unchanged while translating actors, props and world targets together. Further continuation passes the retained high-five point-contact target, but complete meshes expose hand intersection. A separate common scene rise repairs sampled floor conditions while retaining that collision failure; no candidate receives quality or release approval.

[Weight-conditioned export](docs/native-skin-export-v1.md) retains original animation, geometry and bindings while preparing a separate mesh for Godot's weight storage. Both headless import modes now pass the unchanged sampled skin-fidelity limit against the original mesh; hand intersection still fails. That study also introduces complete partner-surface proposal rows and an affine scalar-to-norm lift for geometry-aware correction.

[Surface-guided correction](docs/native-surface-correction-v1.md) now connects those rows to bounded native fitting with all original motion/contact conditions protected. Two restored steps reduce point separation and maximum hand penetration, while crossing and deep-containment counts increase. Complete decoded geometry remains a failure; originals stay selected and no quality approval is inferred.

[Surface-facing acceptance](docs/native-surface-contact-v1.md) now checks oriented normals and the facing side of authored partner, world and object contacts. A source-bound optional fitting filter catches backward-facing contacts even when point distance passes, and resume cannot silently drop that filter. The retained high-five seed needs contact-patch review; this audit does not identify anatomical palms or prove collision freedom.

[Contact-normal guidance](docs/native-contact-guidance-v1.md) adds those authored conditions to surface-vector proposals while protecting original motion/contact limits. Its initial retained half-step reduces point separation and penetration slightly, but opposition angle and crossing counts worsen. [Individual contact protection](docs/native-contact-guards-v1.md) now prevents each failed orientation/side condition from increasing and keeps passing conditions passing. Geometry count tradeoffs remain visible; all quality and release checks remain unapproved.

[Separate geometry bounds](docs/native-geometry-guards-v1.md) address a diagnosed contact/geometry objective tradeoff. Two restored steps reduce worst penetration and crossings while preserving original motion and individual contact bounds, but deep-vertex count increases. Surface and geometry checks still fail; the raw continuation, rejected proposals and full-mesh results remain retained.

[Primitive surface guides](docs/native-object-guides-v1.md) extend native fitting to declared boxes, spheres and cylinders, including whole-triangle intersections and enclosed objects. A deliberate humanoid sphere offset produces 333 verified guides and fails geometry; the unchanged hold fails 53 original native conditions. A synthetic solver trial retains no step. These are measured development failures, not solved object manipulation.

[Individual held-contact repair bounds](docs/native-contact-repair-v1.md) prevent aggregate improvements from hiding worse point or speed conditions. The paired sphere trial exposes 27 hidden contact regressions in the earlier path; the guarded path retains no step and preserves the original 53 failures. Decoded anchoring and restoration keep saved GLBs authoritative, with no motion-quality approval.

[Bounded two-grip object fitting](docs/native-object-hold-fit-v1.md) adds an explicit object-trajectory proposal while preserving every actor GLB byte. Saved interpolation, unchanged contact limits, object-edit budgets and complete sampled scene geometry decide its numerical result. Physical attachment, engine playback and animation-quality approval remain separate requirements.

[Native object asset export](docs/native-object-assets-v1.md) records Float32 timestamp collisions and rechecks the actual GLB at original contact times. A matched Godot trial fails with default import but passes object pose/contact checks through a saved native Animation resource. Imported actor skin, complete scene geometry and runtime playback still need separate validation.

[Combined imported scene checks](docs/native-object-scene-engine-v1.md) pass the retained sphere hold using full imported character skin and actual native object-resource poses at 1,266 times, followed by the expanded 2,201-time population and full original-method replay. A reusable CLI prepares a source-bound common clock and preserves failed default imports. Runtime behavior and motion-quality approval remain open.

[Combined evidence replay](docs/native-object-scene-replay-v1.md) rederives all imported skin/contact/object observations and checks complete saved geometry reductions. It preserves numerical failures and rejects inconsistent results, including changed observations with updated receipts. Geometry queries and human-quality approval remain separate.

[A single native scene job](docs/native-scene-authoring-job-v1.md) connects supplied-rig contact measurements, optional explicit bounded object edits, exports, common clocks, engine observations and replay. It retains numerical failures and preserves source selection. Prompt generation, rig transfer, physical interaction and human approval remain separate requirements.

[Studio scene authoring](docs/studio-native-scene-v1.md) connects selected clips, picked mesh patches, object geometry and explicit edit bounds to that job. Saved drafts and source-bound asset packages preserve character bytes, clocks and measured failures; motion-quality and release approval remain separate.

[Native game tracks](docs/native-scene-game-tracks-v1.md) add complete root references, contact intent and explicit gameplay markers to completed scene packages. A finite Godot dispatcher checks exact marker timing; motion remains embedded in unchanged character clips, with physics and animation-quality review still required.

[Native root runtime](docs/native-root-runtime-v1.md) evaluates saved native resources with motion embedded or moved onto the actor once. Headless checks preserve joint poses; the finite scene checks below additionally measure raw skin after mesh-node transforms.

[Finite scene playback](docs/native-scene-runtime-v1.md) combines saved actor/object resources, root extraction and confirmed gameplay intent on one clock. Callbacks observe all participants at marker time, including skipped frames; preview stays separate from gameplay. Portable Godot packages retain source bytes, with physical interaction, transition/loop integration and human review still open.

[Actor-only contact scenes](docs/native-actor-scene-assets-v1.md) now carry world/partner contacts through authoring, complete imported evidence replay, portable game tracks and finite Godot playback without a synthetic prop. Original clips and failed contact conditions remain preserved; motion quality and release approval stay separate.

[Streamed observation storage](docs/native-observation-archive-v1.md) preserves numeric arrays exactly without retaining previous frames. The expanded actor/object comparison and original-method replay pass at all 2,201 times. [Complete scene producer integration](docs/native-geometry-stream-v1.md) retains all clocks, triangles and precision, with bound archive receipts and preserved partial failures. Motion-quality and release gates stay open.

[Stored-key scene proposals](docs/native-scene-storage-proposals-v1.md) add hard source-motion constraints, continuous proposal derivatives and finite Float32 translation-cell probes. A synthetic body-contact correction passes native checks after five iterations; the matched four-iteration result still fails. This does not establish realistic motion or release readiness.

[Native scene engine diagnostics](docs/native-scene-engine-v1.md) now verify complete imported skin functions and triangles, explicit animation selection, actor/partner contacts and engine object poses. Eight matched humanoid imports complete but retain contact, floor or skin-position failures; 299 focused tests pass. Headless CPU reconstruction and manual authoring seeks do not establish GPU, physics or real-time playback quality.

[Bounded native scene proposals](docs/native-scene-fitting-v1.md) now edit explicitly permitted rotation or translation tracks against body, object and partner targets. Source motion limits, native clocks, protected keys and rig geometry remain checked. Three finite-budget trials still fail; improved hand separation does not approve motion quality, and originals remain selected pending scene and engine checks.

[Native body, object and partner contact audits](docs/native-scene-contacts-v1.md) now measure explicit points on supplied rigs against world targets, moving primitives and another character. Exact touches and held contacts keep separate timing contracts; original source files remain unchanged. Retained interaction replays expose a right-hand hold-speed failure despite passing sphere-grip positions. This is measurement support for broader corrections, with no motion-quality approval.

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

[Studio developer correction review](docs/studio-correction-review-v1.md) now records segment decisions, explicit contact intervals, measured cleanup time and source-bound permission evidence. Original grey reference playback can be compared with a checked native candidate preview. [Native motion cleanup](docs/native-timed-authoring-v1.md) now saves timed joint/root edits directly in Studio, with cumulative bounds, new candidate versions and undo. [Foot-support fitting](docs/native-review-support-v1.md) now also accepts these checked native candidates and returns native versions with independent serialized screens. An opt-in [joint support/rate search](docs/studio-joint-support-v1.md) exposes bounded knee-plane and foot-orientation changes with saved proposal controls and unchanged final gates. A [decoder-aligned warm repair](docs/native-support-clock-repair-v1.md) follows up on the measured clock mismatch. Its [bounded coordinate follow-up](docs/native-wave-coordinate-v1.md) preserves all final gates and reports four rejected proposals. [Native conversion and foot-drift diagnostics](docs/native-contact-diagnostics-v1.md) now keep the actual native selection and its markers separate from a fitter pass. An experimental [editable-native round-trip repair](docs/native-support-roundtrip-v1.md) checks both representations before independent native acceptance. [Explicit planar foot planting](docs/native-foot-plant-v1.md) now targets fixed source patch positions and speeds, retaining the input when a proposal fails the original motion bounds. An experimental [joint planted-motion search](docs/native-joint-plant-v1.md) varies native leg rotations together and checks raw plus shadow-native contacts and motion rates; the closest wave still fails three rate rows. Contact labels and human review must be recorded again after geometry changes; saving does not admit training data or approve release quality.

[Explicit planted-contact correction in Studio](docs/studio-native-plant-v1.md) now exposes source-anchor and speed limits with joint/coordinate search and independent editable-native acceptance. One development wave passes the configured gates; rejected alternatives, actual selected markers and provenance stay visible. This remains sampled development evidence, not human realism or general release approval.

[Imported foot-contact validation](docs/native-engine-contacts-v1.md) now checks actual Godot animation samples and imported skin bindings through independent CPU skin reconstruction. The Studio wave passes its sampled contact limits; the earlier CLI wave exposes a near-coincident endpoint speed failure, and rejected kick/crawl proposals remain failures. Small import position error is separate from contact precision, GPU appearance and release quality.

[Fixed game-frame contact sampling](docs/native-game-frame-contacts-v1.md) adds twelve declared rate/phase clocks and preserves the original failures. It catches a Studio phase overshoot; a stricter proposal follow-up then passes actual native conversion and all imported clocks under unchanged public limits. New Studio planting jobs reserve a small amount below the requested speed while retaining public audits and older saved jobs.

[Contact validation across actions and rigs](docs/native-contact-rig-breadth-v1.md) now audits frozen populations without changing selections. An 18-case, six-action, three-character study completes 11,610 imported observations; every requested planted-contact comparison still fails. Static normalized vertex colors now survive the planted-motion preservation check with their stored values and encoding intact.

[Matched planting-rate diagnosis](docs/native-plant-rate-diagnosis-v1.md) separates contact search from the original motion-rate guard. Removing translation-rate constraints improves native contact in one run/roll/stand case, but original rate and imported contact checks still fail. The diagnostic keeps selections and public limits unchanged and localizes the largest acceleration excess at the stance exit.

[Native game-frame planting options](docs/native-frame-plant-v1.md) add all twelve fixed frame clocks to the proposal model and an optional exterior-key ramp seed. Three matched corrections still fail the original contact/rate/import checks and retain their inputs. These CLI options preserve the existing default Studio path and all release requirements.

[Support articulation and convergence diagnosis](docs/native-support-articulation-v1.md) reports protected animated toe influences across 18 existing clips. Doubling one matched search to sixteen iterations improves contact errors but still fails the original native and imported checks; the input and all release gates remain unchanged.

[Explicit additional foot rotations](docs/native-toe-plant-v1.md) now have a separate source-bound permission contract, cumulative angle limits, raw/shadow audits and actual imported-contact checks before selection. A matched real-rig trial still fails and retains its input; synthetic fixtures verify both input retention and changed-clip selection without implying human-motion quality.

[Reviewed native corpus training](docs/kimodo-corpus-trainer-v1.md) now connects verified targets to sequential frozen-base adapter updates, isolated development validation and bound resume. A tiny CPU fixture reproduces fresh-process continuation exactly; the real CLI rejects the unreviewed packet, and no real motion training or quality improvement is claimed.

[Optional vector scene proposals](docs/native-scene-vector-proposals-v1.md) preserve vector norms when proposing body, object and partner edits, with sparse Jacobians, explicit derivative settings and unchanged decoded checks. A matched body fixture improves, while sphere-grip and high-five trials still fail and retain their originals. This is correction development, not a trained model update or release-quality approval.

[Native scene geometry diagnostics](docs/native-scene-geometry-v1.md) query complete actor triangles against analytic boxes, spheres and cylinders, partner surfaces and explicit world planes. Source-bound audits can accompany correction proposals; containment, missing geometry and sampled failures remain separate. Passing these observations does not approve continuous collision, engine playback or animation quality.
