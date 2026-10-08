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

The saved 0.95 m draft has now completed the full-clock body-preserving V17
experiment, with the original contact/body/speed/geometry limits and six stages.
The guard completes after 864.125 seconds, with 1,042,505,728 bytes peak process
tree RSS. It preserves the unchanged 3600-second, 7 GiB process-tree and 600 MiB
available-system-memory limits. Only the owned Studio server was temporarily
closed for memory headroom; it is restored. No training or model sampling occurs.

Independent complete native-key replay retains the following result:

| Measurement | Result | Existing limit/outcome |
| --- | --- | --- |
| Left/right maximum anchor error, 61 samples each | 5.229 / 5.157 mm | Both pass authored 30 mm; 16 / 12 samples fail working 4.99 mm |
| Maximum joint displacement against raw | 222.107 mm | Fails 220 mm at 65 joint/frame observations across frames 91–99 |
| Maximum added joint speed against raw | 1.141228 m/s | All joint intervals pass 1.5 m/s |
| Maximum candidate box vertex depth | 25.715 mm | Fails; 65 native poses exceed 10 mm |
| Native floor vertex depth, source/candidate | 8.997 / 0 mm | Original floor failure retained |
| Left/right normal diagnostic maximum | 28.519 / 18.855 degrees | 61 / 22 samples exceed provisional 15 degrees |

Displacement and added-speed results against the independent limb and previous
references agree to rounding. The worst raw displacement is `RightHandThumb1`
at frame 98. The worst box penetration is vertex 8560, entirely influenced by
`LeftHandIndex4`, at frame 72. A separate direct eight-influence LBS replay covers
all 18,056 original vertices at every source/candidate native pose and reproduces
the saved vertex-depth tracks within a 1e-12 m arithmetic comparison tolerance.
This checks replay agreement, not physical measurement precision.
The original motion under this newly authored trajectory has zero native box
vertex depth. Candidate fitting therefore introduces a box collision; meeting
point targets does not establish a usable grasp.

The body-position inequality is an augmented penalty and still misses its
unchanged limit by 2.107 mm. This result reinforces why the preflight has no
converse guarantee. `pose_change_above_22cm` and
`LeftHand_surface_slide_regression` remain in the fit flags. Both normal
diagnostics fail. No threshold is rounded or relaxed into a pass.

Studio now includes a separate **Authored-height lift** source/candidate
comparison with native body/contact replay, vertex geometry replay, fit summary
and guard receipts. It is unblinded and unapproved. This result has no complete
imported triangle/volume audit or between-key certification. The next correction
must address finger clearance, the small body/contact violations and hand
orientation before considering a checked game export. Human quality, semantic
and cleanup-time review remain required.
The object-contact close-up also now places its camera outside the focused
prop's bounding sphere. The prior camera position was inside the box at the
measured failing pose and made the prop disappear through front-face culling.
Camera framing changes no motion or measurement.
Both saved actor GLBs pass the local glTF validator with zero errors and
warnings. Desktop build checks and fractional preview checks pass after the
camera change; browser review verifies the hand and box remain visible together.
File validation and visual framing do not approve motion quality or engine
precision.
All fourteen release capabilities remain unapproved; the whole-project goal
stays active.

Local evidence: `reports/scene-placement-authoring-v1/` contains test receipts,
all horizontal/height screens, snapshot verification and browser proof. The
browser-authored context is
`reports/scene-placement-jobs/placement-894a2d19cbd74c779c279227d008b4da/`;
the guarded fitting experiment is `reports/box-lift-authored-height-v1/`.
The developer comparison is
`reports/scene-region-jobs/box-lift-authored-height-review-v1/`.
Generated motion, third-party assets and bulky receipts remain excluded from Git.
