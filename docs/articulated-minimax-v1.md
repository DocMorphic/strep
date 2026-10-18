# Bounded articulated tracks and complete minimax proposals

Development components, 2026-10-18. These author controls and propose a local
step; they do not approve motion or narrow the whole-project release goal.

`scripts/articulated_track.py` applies explicit local rotation-vector edits and
optional root translations to a complete supplied clip. Rig joint indices,
rotation budgets, temporal basis and protected frames come from the caller.
There is no action-name, humanoid-joint-name or anatomical mapping whitelist.
The source rotations are owned copies and must already be consistent with SO3.
The module does not repair a rig, infer joint limits or evaluate forward kinematics.

Rotations use matrix exponentials, preserving the rotation representation.
Every unselected local joint stays unchanged, and protected frames have exact
zero temporal support. Per-frame vector norms are checked before applying an
edit; excessive controls reject without clipping or normalization. A convex
temporal basis makes bounded knot-vector controls sufficient for complete
per-frame bounds. The explicit complete frame assessment stays available.
Actual serialized geometry, kinematics, motion and author limits still require
independent checks. The normalized control assessment does not approve them.

The initial implementation supports 3–300 frames, 1–256 source joints,
1–16 selected joints and 1–8 temporal columns. Rotation budgets are positive
and at most 90 degrees; root translation is explicitly bounded up to 22 cm.
These are component capacities and author permissions, not measured human
abilities or new release thresholds. With root editing disabled, no hidden
root variables are created.

`scripts/conic_pose_minimax.py` retains every supplied signed physical row and
all normalized three-vector control balls. It minimizes the largest linearized
violation, with a small movement cost, instead of summing collision errors.
Two characters' controls can appear in the same rows. It uses the existing
pinned Clarabel backend, explicit trust bounds and a declared search reserve
strictly inside author budgets. Solver tolerances never replace strict physical
or saved-file gates, and controls are never clipped after solving.

A solver result is a proposal. Closest-feature changes, nonlinear FK, geometric
sign classification and serialization can invalidate a linear prediction.
Complete nonlinear and raw/saved checks remain mandatory. Uneditable failed
rows stay visible; a failed local model is not proof that an action is impossible.

The first source suite passes **139 cases**, including the previous 111.
New checks cover exact zero/frozen/unselected behavior, full control Jacobians,
true angle norms and SO3, complete temporal bounds, source ownership, invalid
permissions and explicit disabled root controls. Solver cases verify competing
contact rows, a mean-error tradeoff rejected by minimax, actual vector balls,
nonzero original-relative controls, both actors and a hidden last-row violation.
Malformed or over-budget inputs reject before solving.

Local evidence: `reports/articulated-minimax-tests-v1`. These checks are
engineering evidence; the next study must use the original real clips and
retain all failed constraints, exported artifacts and independent observations.

## Separate root and joint support

The original native high-five references exceed the existing 5 mm floor
diagnostic at every one of their 120 frames. Freezing the clip boundaries while
only editing the contact window cannot correct that full-clip failure. This is
a limitation of those permissions, not proof that the interaction is impossible.

Root edits can now have an explicit `root_basis` and `root_fixed_frames`, on the
same complete clock and temporal-column count. This permits a bounded whole-clip
root-height correction while keeping joint rotations protected outside a local
edit window. Omitting them preserves the shared-basis behavior. Changed root
support never implicitly overrides its protected-frame policy, and disabled
root controls reject unused permissions.

The complete suite now passes **142 cases** with the additional independent
support, no implicit permission override and unused-permission checks.
Local evidence: `reports/articulated-minimax-tests-v2`. No physical/motion
threshold, authored scene target or original release requirement is changed.

## Actual articulated-pair trial

The unchanged native high-five clips, seeds 77/88, now feed one coupled local
solve with 72 control components and 24 exact vector balls. A separate declared
diagnostic policy permits five-degree edits to eleven supplied joints per actor
inside frames 30–90, with local rotations protected elsewhere. Root translation
up to 2 cm is explicitly permitted across the complete 120-frame clock. This
does not reinterpret the earlier failed 1 mm root-only trial.

All twelve supplied physical rows participate: both full-clock floor maxima,
all three original generated-partner point contacts, world and opposing-palm
normals, both tangents and both partner collision directions at frame 60.
The existing 30 mm contact, 5 mm depth and 15-degree development screens remain
unchanged; they are not newly calibrated release thresholds.

Every directional derivative row passes the declared 0.1% technical check;
maximum relative error is 1.1662e-6. The conic model predicts zero violation,
but all three fixed nonlinear fractions fail. The best full step reduces the
maximum normalized violation from 1.696693 to 1.131154, so linear feasibility
is not reported as a successful interaction.

| Independent raw measurement | Original | Proposal |
|---|---:|---:|
| Deepest partner overlap at frame 60 | 13.483350 mm | 10.655835 mm |
| Vertices beyond the existing 5 mm partner diagnostic | 180 | 94 |
| Actual palm gap | 33.282243 mm | 35.862595 mm |

Saved-file observations agree: deepest overlap is 10.655996 mm and the palm gap
is 35.862708 mm. The proposal still fails contact, orientation and collision
requirements. Float64 optimizer floor rows clear 5 mm, but the actual raw and
saved depths land slightly above the hard boundary after quantization; those
also remain failures, with no epsilon added. Original source-preservation
comparisons stay visible separately: both actors fail physical nonregression,
and actor A also exceeds its original native motion envelope.

The proposal is exported by appending edited rotation/root accessors to the
original GLBs. Independent replay verifies every original binary byte, all
**284 unselected channels** and **1,342 protected rotation keys** remain exact.
Saved local rotation edits stay within the declared five-degree budgets
(A: 2.50000010°, B: 1.81389530°); saved root shifts of 5.430341 and 3.328204 mm
stay within the separate 2 cm permission. Meshes, materials, nodes, skins,
unselected samplers and animation clocks remain unchanged.

All four original/proposed exports replay across **8,666,880 vertex/frame
pairs**, retaining all eight weights, 36,108 faces and every complete original
floor/contact/orientation/motion observation. Maximum saved skin-component
error is 6.861e-7 m. Torch, the new control/solver and gradient modules are
excluded from this replay. **Only partner frame 60 is queried; the other 119
partner frames, edge-only, continuous, self-collision, force, engine and human
checks remain open.** No corrected asset is selected or approved.

All 142 source cases also pass on hosted Windows and Ubuntu at
`87db9a98551244a27cc0f4703d80bbd5609c64d8`
([focused run 39127753094](https://github.com/DocMorphic/strep/actions/runs/39127753094)).
Local evidence: `reports/articulated-minimax-probe-v2` and
`reports/articulated-minimax-replay-v1`. The first launch deferred without
starting a worker. After RAM recovered, the identical worker completed with
the same 2 GiB cap, 600 MiB reserve and 300-second execution limit; only the
admission window increased from 60 to 600 seconds. The actual solve completes
in 211.047 s with a 1,199,554,560-byte peak. Independent replay completes in
117.781 s with a 252,948,480-byte peak under 512 MiB.

Next use sequential nonlinear relinearization and physical-row search margins
inside the unchanged hard gates, while retaining contacts and conditions that
already pass. A single linearized maximum cannot anticipate every change in
the active closest surface. The complete partner clock, engine import and
real review/cleanup remain mandatory under the same whole-project goal.

The completed checkpoint is `reports/articulated-minimax-progress-v2`.
Its streaming audit verifies 4,751 current source, archive, asset, data and
resource bindings and the prior whole-goal receipt. Two superseded source
bindings are checked against their immutable archives and public `4b2aa0c`
revision. It completes in 33.656 s with a 61,906,944-byte peak under 512 MiB.
The first progress audit incorrectly expected a worker log for an admission
that never started a worker; it failed before metadata changed and is preserved.
The fresh audit verifies that absence explicitly. Only goal line 3 and the two
permitted release-matrix progress fields change; all 14 capabilities and every
original release requirement remain unapproved and intact.
