# Original-bound clearance refinement in Studio

Studio now offers **Refine clearance** alongside the existing **Adjust contacts**
objective. Clearance refinement requires a native/contact-feasible starting
motion, explicit character edit bounds and declared scene geometry. It changes
the selected native tracks within the original motion limits. The original
assets remain selected until the proposal passes review and is explicitly staged.

The new `strep-studio-native-scene-fit-v3` request retains the original scene,
contact targets, edit permissions and authored joint-speed limits. It preserves
both boundary poses and uses the decoded surface fitter with bounded export
repair. The UI exposes 1–8 repair stages and 1–64 probes per stage (defaults
8/16). These are search limits, not quality settings or guarantees of repair.
Existing contact-mode v1/v2 requests keep their earlier behavior.

A completed clearance job can be loaded for continuation. Its corrected native
keys and repair state are bound to the original asset and source-cap arrays;
they do not become a fresh source with looser motion limits. Continuation rejects
changed scene/contact targets, geometry, permissions, speed limits or fitting
mode. A geometry failure may be continued if the native/contact conditions pass.
A contact-infeasible start stops with its failed native evidence retained.

Review validates the complete saved export-repair population, including failed
probes, their arrays and assets, selected corrections, original authoring policy,
final state and any reused repair. Modified evidence rejects review. Optional
speed checks freshly decode the final corrected keys. These archive checks do
not independently recompute every geometric measurement; motion and geometry
decisions are produced by the fitter's separate full audits.

The editor restores mode, budgets, original bounds and speed limits when loading
a continuation. Staging requires passing native conditions and declared geometry,
plus passing speed limits when authored. Saving, completion or staging does not
approve realism, engine fidelity, training use or release. Failed floor results
remain visible; there is no automatic replacement of the source clip.

## Validation

All **170 distinct related Python checks** pass across the recorded local runs:
the initial 169-check run includes the new 28-case Studio storage
suite plus existing Studio fitting, authored-speed integration, speed fitting and
native storage fitting suites. Cases include actual synthetic GLB jobs and their
continuations, retained speed policies, original cap identity, altered source
evidence, rejected rebasing, failed floor continuation and failed contact starts.
All 449 recorded resource observations independently replay under the unchanged
resource policy. The earlier isolated 26-case run also passes and its 147 resource
observations replay; it precedes the last two failure cases.

An additional focused regression passes with two closed skinned fixtures,
editing only the second actor and continuing its state. It distinguishes
scene-indexed final assets from edited-actor-indexed search assets and retains
both original actor snapshots and source caps. All 55 resource observations
replay. Its earlier driver-lock failure (29 observations) and open-surface
fixture failure (43 observations) remain recorded and independently replayed.
The final Studio storage suite contains 29 cases; no new full 170-case rerun is
claimed. This is software/provenance coverage, not a human interaction study.

The offline Node editor suite passes objective/budget requests, restoration,
failed-result staging and existing timing/stale-response behavior. The generated
desktop HTML is rebuilt from source. No live browser, HTTP service, renderer or
new engine playback is claimed by these checks.

The [focused workflow at `7f50b21`](https://github.com/DocMorphic/strep/actions/runs/38191029115)
passes all six Windows/Linux jobs: **756 Python checks per OS** (689 contact/rig,
35 lineage, 32 game packages), 23 subtests and the offline editor. That revision
precedes this Studio integration. The current declared source inventory is
470 Python test modules / 42 Node suites; these totals are not a new complete
hosted-inventory result.

An actual offline Studio trial starts from the retained **original** humanoid
kick, with 72 controls, one clearance iteration and 8/16 repair effort. It
finishes at 686.031 s execution within the unchanged resource policy. All
694 observations independently replay. The recorded search retains 76 native
exports: start (1), rejected full step (1), failed repair searches (23/26),
accepted smaller candidate (24), and fresh final replay (1). Failed candidates
remain saved; final evaluation reuses the checked repair rather than repeating
the search. The final state has six explicit stored-component corrections.

All **107,527 native conditions pass**, with the original cap arrays and rate
clock unchanged. Complete floor geometry still fails at **233 of 2,017 times**,
with **49.271426 mm** maximum penetration (original start: 49.727615 mm).
The result is retained for continuation, cannot be staged, and receives no
quality/training/release approval. This fresh-start trial differs from the earlier
[automatic fitting](native-fit-storage-v1.md) trial with an explicit corrected
start; its geometry result must not be substituted for that earlier result.

A separate final numerical replay reconstructs the export byte-for-byte,
reproduces all native residuals/worlds, original source caps/clock and zero root
error, and freshly recomputes every floor sample with identical results.
It completes at 27.375 s execution and all 45 resource observations replay.
Failed search probes receive complete hash validation in this replay, not
independent numerical reconstruction. Raw trial/replay evidence stays under
`reports/studio-kenney-clearance-v1` and
`reports/studio-kenney-clearance-replay-v1`. Neither run involves a renderer,
live HTTP/browser, model generation or engine playback.

Broad held-out action, rig, object and partner coverage, continuous-time dynamics,
actual engine fidelity and human review/cleanup remain release requirements.
