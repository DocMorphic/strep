# Authored scene placements and necessary anchor reach

Studio's **Scene placement** panel now edits either a prop's whole path or one
existing saved pose. Position and heading edits preserve every original pose
time. Actor placement still applies to the entire clip. **Check anchor reach**
screens the current draft; **Save placement as new scene** stores a separate
collection and selects it without replacing the source.

The saved snapshot copies exact original native motion, actor GLB and license
bytes. It retains the original scene/evidence, request, complete reach results,
method sources and hashes. It recomputes native anchor distances and explicitly
marks geometry unevaluated. Previous collision, orientation and quality results
are not inherited as valid measurements of the new placement. A completed save
means an authored context exists, not that an animation passes review.

## What the check means

This necessary condition uses the unchanged source skin, all eight LBS
influences, actual source rotation operator norms, a 220 mm bound on each joint
position edit, unrestricted new proper rotations and 1 micrometre arithmetic
slack. It compares the resulting error lower bound with the original authored
anchor tolerance at every inclusive native contact key. Joint-offset anchors
use the corresponding one-joint bound. Partner targets are measured but skipped
in the impossibility screen because a coupled edit may move both actors.

The screen does not change contact fitter options. In particular, its authored
30 mm point tolerance is distinct from the V17 fitter's tighter 4.99 mm working
target. Neither a zero lower bound nor **No conflict was proved** establishes
feasibility. Anatomy, normals, full contact regions, speed, coupled joints,
geometry, physics, between-key behavior, import and human review remain separate.

Metadata and requests bind the source, skin and check implementation. The local
API rejects stale revisions, changed sources, missing identities, altered pose
times, invalid poses and oversized drafts. Frontend requests capture the current
draft; stale or edited drafts do not select an earlier response. A failed copy
retains its failure receipt and cannot become a completed collection.

## Development lift measurements

These are in-sample authored request experiments using the preserved six-second,
180-frame anatomical lift, seed 11. They do not repair the original request or
evaluate held-out prompts. All attempts and original failures remain local.

Nine declared horizontal translations combine X offsets of -0.1, 0 and 0.1 m
with Z offsets of -0.2, 0 and 0.2 m. Every translation retains proven native
anchor conflicts. The unchanged placement has the fewest: 55 combined
hand/key conflicts, with maximum left/right lower bounds of 103.431/115.247 mm
against the authored 30 mm tolerances. The other offsets retain 56–101 conflicts.
This screen does not demonstrate actual optimizer error improvement.

A separate three-height experiment keeps the initial box poses at frames 0/60
unchanged, including the original 0.2 m center height. Only the center heights
of the final poses at frames 120/179 change; rotations, X/Z, dimensions, all times,
grips, contact intervals and tolerances remain unchanged.

| Final box center height | Left/right maximum error lower bound | Keys ruled out at authored 30 mm |
| --- | --- | --- |
| 0.65 m, original | 103.431 / 115.247 mm | 22 / 33 |
| 0.80 m | 15.983 / 24.175 mm | 0 / 0 |
| 0.95 m | 0 / 0 mm | 0 / 0 |
| 1.10 m | 0 / 0 mm | 0 / 0 |

The 0.95 m height is the smallest declared change that also avoids a proven
conflict with the tighter working target. It is a new authored trajectory,
not a feasible grasp certificate. The browser saved exactly this draft as a
new scene, reloaded it and displayed fresh reach results plus the explicit
unevaluated-geometry status. An independent receipt verifies exact asset bytes,
unchanged source files, all pose/contact times and contact-fitter source binding.
No browser console errors were observed.

## Validation and remaining work

Local checks pass 62 model-free Python tests, three native fitting-handoff tests,
and all 39 declared Node suites. The native tests stop deliberately at
preprocessing and verify that a passing preflight's existing directory retains
its receipt while exact raw motion/GLB assets reach the next stage. They do not
run an optimizer. The public model-free inventory now declares 402 Python
modules and 39 Node suites, with Python shard sizes 101/101/100/100. Hosted
validation is separate from these local results.

Rotated and translated two-actor tests also verify that saved preview marker
tracks stay in each actor's local coordinates while contact distances use world
coordinates. Studio applies each actor placement exactly once. The new point-only
assessment explicitly distinguishes anchor measurements from unevaluated contact
regions and geometry.

The saved 0.95 m draft is the next full-clock body-preserving V17 fitting
experiment, with the original contact/body/speed/geometry limits and six stages.
Correction, independent imported measurements and human review remain required.
All fourteen release capabilities remain unapproved; the whole-project goal
stays active.

Local evidence: `reports/scene-placement-authoring-v1/` contains test receipts,
all horizontal/height screens, snapshot verification and browser proof. The
browser-authored context is
`reports/scene-placement-jobs/placement-894a2d19cbd74c779c279227d008b4da/`;
the guarded fitting experiment is `reports/box-lift-authored-height-v1/`.
Generated motion, third-party assets and bulky receipts remain excluded from Git.
