# Temporal track controls for constrained motion correction

The finite smoothing study reduced errors near a hand interaction but introduced
new failures. A single strength forces every joint to use the same adjustment.
`scripts/native_track_profiles.py` instead gives each declared node one amplitude
for its complete, supplied temporal direction. It is a search representation for
the existing correction pipeline; it does not change the motion generator or
provide new character-stat controls in Studio.

For original-relative cumulative controls `C`, direction `D` and node amplitudes
`a`, the proposal is `C[t,j,:] + a[j] * D[t,j,:]`. Every node remains a column,
including a zero direction. The complete source clock and control grid remain;
the caller explicitly declares editable and frozen keys. Endpoints must be frozen,
and nonzero direction outside the editable set rejects the entire input. No key,
joint, direction or constraint is silently removed to meet a storage limit.

Amplitudes have a declared search box of `[-1,1]`. This box is not an authoring
permission. Original native rotation balls remain separate mandatory constraints.
Values outside a ball are available for diagnostics but rejected on export;
there is no clipping or quaternion/source rebasing. All returned arrays and
reports are owned snapshots. Bounded endpoint and native-row requests retain
all profile columns or reject the entire request before allocating the matrix.

`TrackProfilePoseRows` composes these controls with the existing original-bound
key/pose/norm adapter. Temporary local key variables transport only the exact
bracket endpoints at the requested time. They grant no permission to edit those
keys elsewhere. The output retains every original rotation and joint-displacement
norm vector, its original radius, complete hierarchy and every profile derivative
column. Original source, clock, seed, node order and complete bracket/node pairs
must match. Changes to the bound original pose context are rejected.

Raw pose derivatives include transverse vector components; an apparently zero
scalar norm gradient does not establish nonlinear invariance. Encoded evaluation
is value-only interpolation, not an independent saved-file certificate. Saved
clips, all original motion constraints, dependent prop permissions, contacts,
full changed-time geometry and independent replay remain required before adopting
a correction. A locally feasible solver result is still only a proposal.

This representation can supply a compact constrained temporal search for the
measured interaction failure. It does not establish natural motion, action
correctness, engine playback, animator cleanup savings or release readiness.
The full-project goal and release criteria remain unchanged.

## Source checks

The final focused run passes **137 tests**: 31 new profile cases and 106 existing
key-basis/pose/norm regressions. The new cases check complete native grids and
last-column derivatives, zero directions, frozen bytes, exact zero-amplitude
identity (including signed zero on an active direction), immutable inputs,
native-ball rejection, mismatched original contexts, whole-budget rejection,
four pose-time modes and independent saved-GLB sampling. No test fabricates
human ratings or animation acceptance. The initial 136-test run and its source
snapshot are preserved; the added signed-zero regression covers the corrected
zero-adjustment behavior. Final local resource replay: 47.969 s,
193,818,624-byte peak process tree RSS and 49 observations. These are model-free
CPU source checks under the existing memory guard.

The 31 new cases also passed on hosted Ubuntu and Windows at
`24fd7dbb772b50df146c105acdd0addb842f8b60`
([run 39112291047](https://github.com/DocMorphic/strep/actions/runs/39112291047)).
The final local checkpoint includes a version-bound negative control: the old
archived helper changes a signed-zero byte on zero adjustment, while the current
helper preserves the exact seed. Earlier successful reports remain immutable
and retain their own method versions.

## Actual two-character scene

The final implementation was replayed in a fresh bounded study,
`reports/native-track-profile-actual-v2`. It retains all 22 actor-A and 23 actor-B
node columns. Four original prop variables would make a 49-column coupled model;
that model and its hard constraints have **not** been assembled or solved here.

| Observation | Result |
| --- | --- |
| Zero-amplitude cumulative controls and saved GLBs | Byte-identical to qualified reference |
| Unit-amplitude cumulative controls and saved GLBs | Byte-identical to previously rejected full smoothing |
| Fresh baseline world scalar values | All 383,617 byte-identical |
| Fresh original pose norms | All 23,880 byte-identical |
| Complete baseline native balls | All 5,400 byte-identical |
| Full-vector/world direction checks | 16 passed at four declared times per actor |
| Maximum vector direction difference | 8.40e-11 |
| Maximum hierarchy direction difference | 3.81e-11 |

The direction checks include the last profile column, a full random direction,
frozen native key 60, native key 65 at the mesh touch, and the 65.5/70.5 subkeys.
They validate these sampled chains, not every-time derivatives or a solved clip.
Saved-file identity reuses the existing reference/rejected-take evidence; this
study does not claim to rerun every one of their 944,562 original checks.

The structural census keeps all 2,017 original body-policy times, 589 evaluated
world times, 120 native keys and 120 original pair contexts. Nonzero temporal
support may affect **185 body-policy times, 53 evaluated world times and ten
native keys**. All 35,504 original triangle-pair rows per mode occur where every
profile direction is exactly zero at both original interpolation endpoints.
Their controls are therefore invariant throughout this search subspace. This is
sampled input identity, not proof of new collision clearance. A changed proposal
still needs complete affected body/scene/prop queries and independent replay;
an exact zero tangent alone would not justify inheriting those checks.

The final actual study and resource replay completed in 120.750 s with a
204,820,480-byte peak tree RSS and 120 recorded observations. It invokes no
optimizer or geometry query. The original source/author epoch, frozen 0/60/119,
qualified reference and Studio selection are unchanged. All 72 protected repairs
still pass; the 6,050 source-rate failures, two scene failures and previously
disclosed coverage/dynamics/engine/human-review gaps remain open. Neither endpoint
is a new accepted asset, and the unit endpoint remains rejected.
