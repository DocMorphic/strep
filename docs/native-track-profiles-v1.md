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
