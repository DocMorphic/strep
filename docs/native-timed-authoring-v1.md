# Native motion cleanup in Studio

Studio's **Developer correction review → Edit native motion here** edits the
selected SOMA77 motion directly. It works on any selected native action segment;
there is no action-name whitelist. Native fingers are selectable too, although
the current denoising representation cannot encode every finger channel.

Load a review packet and select a segment. Choose a joint, enter a local rotation
vector in degrees or a world-space root offset in metres, and choose start, peak
and end frame keys. **Save edit and preview** retains a new native NPZ and builds
its checked grey-character preview. Switching segments keeps each selected
candidate. **Undo last edit** restores and previews the preceding candidate;
**Use original motion** restores the immutable source. History is an unsaved
in-memory convenience; the saved candidate files and result receipts survive
reloads and remain available through the existing candidate-path input.

The original-reference player retains its source clock. Edited candidates use
a segment-local clock starting at zero. Both transports map to the same local
frame indices. Original and candidate versions remain explicitly selectable.
Actual browser layout, GPU deformation and perceived motion quality have not
been verified by the offline checks described below.

## Rotation, timing and bounds

The three rotation components specify an axis-angle rotation vector, rather
than three Euler angles. At each key the implementation postmultiplies the
selected joint's local rotation by the exponential of the weighted vector.
Root translation adds the weighted vector in right-handed world coordinates,
with Y up. Cubic smoothstep ramps from zero at the start key to one at the peak,
then back to zero at the end key. End keys are inclusive; the peak must be
strictly inside the window. A segment needs at least three keys.

Untouched joints, root channels that receive no offset, all keys outside the
window and both boundary keys retain their exact FP32 values. Proper finite
rotation matrices and the native 30 fps clock are required. No original file
is rewritten. A request with no representable change is rejected.

Every candidate, including a candidate supplied externally, is measured against
the selected immutable original. These fixed limits apply across the entire
candidate and all joints, before and after every operation:

| Measure | Limit |
| --- | --- |
| Joint angular distance from original | 45 degrees |
| Root distance from original | 0.25 metres |
| Adjacent-key change in original-relative joint correction | 5 degrees |
| Adjacent-key change in original-relative root correction | 0.05 metres |

Repeated operations cannot reset the budget by treating the last edit as the
original. Violations are rejected, not clamped. Rotational checks allow 1e-4
degrees of numerical tolerance; root checks allow 1e-6 metres. These limits
describe authored offsets, not the character's total angular speed or root
speed. They are sampled frame-key limits, not anatomical ranges, dynamics,
subframe collision certificates or contact preservation.

## Retention and review

The `/api/correction-review-edit` request binds the draft hash, item ID,
candidate NPZ hash and matching-window start, plus the explicit edit. It uses
the existing Host/Origin, JSON, body-size, server-job and shared-worker guards.
No model inference or training is started.

Each valid authoring attempt gets a fresh folder under
`reports/native-correction-edits/`. The result retains the parent selection,
source and method hashes, method copies, declared operation and measured bounds.
Failed bounds or preview exports retain failed receipts. Successful candidates
contain local rotations, root positions and recomputed world joint geometry.
Their pose tracks must reload exactly before preview export. Source, method
and output hashes are rechecked before completion.

The preview uses the original fixed skeleton and unchanged mesh, material,
skin and all eight influences. Its serialized pose and skin checks are
described in [the candidate-preview study](native-candidate-preview-v1.md).
The authoring report additionally lists maximum world-position movement for
every joint. Movement of a hand or foot is a geometric measurement, not a
contact judgment.

An edited candidate inherits **no predicted foot-contact labels**. Studio
resets its previous contact annotation, packed correction, review decisions,
human checkboxes, cleanup seconds and rights claims. Actual measured cleanup
time must still be entered by the reviewer. All quality, training and release
approval fields remain false. Undo and original reset also require review of
the newly selected candidate. Packing and source-bound human submission remain
separate actions; neither saving geometry nor successful import admits data
for training.

## Verification

The focused CPU selection passes 197 tests. New geometry tests check local
rotation convention, world root translation, smoothstep weights, exact
untouched channels and boundaries, finite/proper FP32 input, invalid clocks,
vector and type validation, cumulative angular/root limits and correction
step limits. Backend fixtures check real candidate serialization and preview
publication, unknown contacts, source and method binding, chained edits,
retained failures and offline HTTP worker/origin/size guards. The DOM suite
checks explicit vectors, candidate installation, cleared human claims, segment
persistence, undo, original reset and ignored late responses. These numerical
fixtures do not represent human corrections or permission.

The broader 1,648-test geometry/Studio run returned 1,646 passes and two
stale generated-page equality failures. Rebuilding the served Studio page
repaired those failures; all four related desktop build checks then pass.
All 15 JavaScript suites pass. The terminal local service canary edits nine
historical development segments across seven actions, totaling 1,020 frames.
Three-degree forearm and .01 m root offsets are numerical demonstrations only.
Godot 4.7.2 imports all nine with 77 bones, one skinned surface and non-looping
clips. Every native-time joint sample matches within about 3.19e-6 metres
and 2.10e-6 basis elements. Sources, methods and candidates stay hash-bound.
These checks establish geometry and workflow behavior only. Real reviewed corrections, licensed
training data, demonstrated model improvement and the remaining scene, partner,
rig, control and human release requirements remain unfinished. The full project
goal stays active; no release capability is approved by this change.


[Native foot-support fitting](native-review-support-v1.md) now connects checked candidates to the existing bounded fitter, converts results back to native NPZ and rechecks serialized support/motion screens. Use of a converted result is explicit; rejected proposals remain visible and human contact labels stay unknown.
