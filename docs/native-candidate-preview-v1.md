# Native candidate comparison in Studio

The developer correction-review panel can now show the selected candidate's
actual geometry on the original grey SOMA character. **Build candidate preview**
creates a checked GLB; **Preview version** switches between it and the original
reference. Building or viewing a preview never fills human judgments, contact
labels, measured cleanup time or permission fields.

## Geometry and provenance

`scripts/native_candidate_preview.py` derives fixed native bone offsets from
the original motion and independently reconstructs its global joint positions
and rotations. That reconstruction must agree within `1e-5` before the offsets
can be used. The candidate must contain proper SOMA77 local rotations and root
positions; unsupported hierarchies, inconsistent source geometry and nonfinite
skin data are rejected.

The exporter keeps the original mesh, skin, materials, textures, inverse bind
matrices and binary payload unchanged. It replaces pose channels for the selected
window using the candidate's local rotations and root positions. All eight skin
influences are retained without truncation or normalization. Rotations use
continuous quaternion signs and glTF LINEAR interpolation. The cropped clip
starts at zero; its last key is at `(frame_count - 1) / 30` seconds.

Every serialized key is decoded and compared against independently assembled
joint transforms and skin vertices. Joint-position, rotation-element and skin
errors must each remain below `1e-5`. This checks serialization and rig geometry;
it does not establish natural motion, physical contacts or prompt correctness.

The API requires the selected draft hash, item, candidate hash and explicit
window start. Sources and core implementation files are rehashed before
publication. Results, exported GLBs, failures and core method copies are saved
under `reports/native-correction-previews/`. Only completed, hash-matching
`candidate.glb` files are served. Arbitrary namespace files and changed output
files are refused. Existing host/origin checks, request limits and the shared
worker lock apply.

## Studio behavior

Original and candidate clips have separate source clocks. The review playhead
maps both to the same segment-local frame index, so contact intervals refer to
the selected segment rather than an unrelated full-motion clock. Changing a
candidate clears its stored preview and human claims. Late exports for a closed
panel or stale selection do not replace the displayed version. Preview creation
does not guess a contact schedule or admit a correction into training.

The initial reference remains the original. Select or build the candidate to
review its actual exported poses. The existing 32 MiB native NPZ and 2–300-frame
window limits remain. This version supports the standard source SOMA body and
native bone layout; other rigs still use the separate rig-transfer pipeline.
Candidates are authored externally at present. A direct native cleanup editor
remains useful next work.

## Observed verification

The focused CPU selection passes 166 tests, including eight converter checks and
24 backend/handler checks. The UI fixture verifies exact selection binding,
version switching, separate clocks, changed-candidate invalidation, stale
responses and unchanged human fields. The broader 169-file selection passes all
1,648 Python tests and 15 JS suites. Tests use synthetic poses where stated;
they do not substitute for visual or human review.

The retained canary `reports/native-candidate-preview-canary-v1` uses all nine
existing segments across seven developed actions: jump/land, crawl, dance, wave,
kick, get up and the three-part run/roll/stand sequence. It exports 1,020 frames
with a numerical 0.01 m root offset and a smooth three-degree forearm variation.
These are numerical demonstrations, not animator-approved corrections or
training supervision. Original source and declared method hashes remain intact.

Godot 4.7.2 imports all nine candidate GLBs with 77 bones, a skinned surface and
non-looping animation. All 1,020 native-time samples agree with CPU transforms;
the maximum measured joint-position error is about `3.19e-6` m and the maximum
basis-element error about `1.93e-6`. Godot may reorder or deduplicate mesh
vertices, so this import audit does not claim an exact imported vertex ordering.
The separate CPU exporter checks use all eight influences.

The engine run is headless. Browser appearance, GPU skin deformation, physical
contacts, animation quality, learning improvement and cleanup-time savings are
not established. No real human submission or new motion-model update was
produced. The preceding trainer commit `6d25d3d` passed all four Windows/Linux
jobs in hosted run `37020780644`. All 14 release capabilities remain unapproved;
the full project goal remains active.
