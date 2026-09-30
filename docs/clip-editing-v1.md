# Target-rig trim, speed and local pose editing

Development evidence, 2026-09-26. The full-project goal and all release review gates remain open. No model training or new inference was needed for this change.

## Workflow

In Studio Characters, choose a motion result and its version, then **Edit timing and pose**. Choose inclusive first/last source frames and a speed multiplier, optionally add smooth local bone rotations, and apply. A new immutable job preserves the selected input, original character/motion, recipe, contact drafts and output. Input and edited preview versions use their own frame counts; switching maps the displayed frame through the saved source clock, rounded to the closest available frame and clamped outside the trim.

The interface explicitly shows the source pose until the edit is applied. Pose curves use start, peak and end source frames. The XYZ delta becomes one local rotation vector, smoothly scaled with cubic smoothstep on both sides of the peak and postmultiplied onto the source bone rotation. Unedited local poses and every local translation are preserved; world placement is retained. At most 24 curves are accepted, combined rotations cannot exceed 90 degrees, and overlapping curves on the same bone are rejected. This is deterministic pose editing, not text-driven semantic motion editing.

Speed is 0.25–4x. Output stays at 30 fps, includes both trim endpoints, and cannot exceed 30 seconds. The frame count is the nearest integer number of output intervals, with half ties rounded up; the exact effective speed is reported. Geometry, predicted-contact intervals and authored-contact intervals share this frame mapping. Intervals use half-open discrete membership; intervals missed by downsampling are explicitly listed in the audit. Authored world targets stay fixed and must be reviewed after edits. Root tracks describe the mapped pelvis, not engine root extraction.

## Reproduced evidence

| Job | Input / edited frames | Edit |
| --- | --- | --- |
| `20260926-204805-38b5db10` | 61 / 21 | Original Cesium embedded animation after an earlier contact edit; trim 10–40, speed 1.5, LeftArm local Z +10° peaked at source 25 |
| `20260926-204848-eaceb96b` | 120 / 31 | Generated, retargeted Quaternius female wave after an earlier contact edit; trim 30–90, speed 2, RightArm local Z −8° peaked at source 60 |
| `20260926-205132-5726f4ae` | 31 / 31 | A subsequent contact correction on the edited wave, proving the retimed annotation clock survives another authoring job |

The imported clip was authored through the actual Studio UI. Its heel interval 21–25 became 8–10 on the edited clock. The UI showed input frame 40/60 when comparing edited endpoint 20/20, and input frame 12/60 when comparing edited frame 1/20. Contact inspection reports 3/21 frames over 5 mm floor depth, maximum 10 mm: this remains a failed floor screen. No source support predictions are invented for imported animations.

The wave retains its original model-predicted contact provenance. These are unconfirmed support annotations. Subsequent contact correction passes its limited numerical screens; that does not establish naturalness or correct dynamics after a speed change.

`verify_clip_edit_study.py` decodes saved input/output GLBs and checks all local matrices against independently calculated edit curves, root tracks, contact membership/targets, served GLB hashes and every ZIP entry. Maximum local matrix error is 7.66e-8. The two edit archives contain 40 and 42 entries. `verify_mesh_contact_study.py` independently rechecks the chained contact job's exported metrics, bounds, untouched poses, root tracks and package bytes.

Evidence lives in `reports/clip-edit-authoring-v1` and `reports/clip-edit-contact-chain-v1`. Actual Godot import evidence is in `reports/godot-clip-edit-authoring-v1` and `reports/godot-clip-edit-contact-chain-v1`: six files, 295 frames total, 19/65 bones, all skinned surfaces present; maximum position error 3.74e-7 m. All six GLBs have zero validator errors, with inherited warnings (one on each Cesium file, six on each Quaternius file). The first validator invocation encountered a manifest absolute-path join error; the manifest writer was fixed to use relative paths and validation rerun successfully. No artifact encoding tolerance was relaxed.

Full regression suite: 273 tests passed with four upstream Torch deprecation warnings. Additional tests cover malformed recipes, clock quantization/endpoints, exact local pose preservation, contact remapping, selected input-version metadata and native annotation hash/clock integrity through contact chaining.

## Remaining scope

No physical realism, animator, semantic, force balance, continuous collision or scene-contact approval is implied. Pose/time changes may create invalid support or dynamics. Loops, transition preservation, object/partner time synchronization, prompt-based semantic editing, a broader independently selected clip/rig set, and measured animator cleanup time are still required. These implementation fixtures are not held-out release evidence.


## Event timing after speed edits

Clip edits retain the frame-based event contract: nearest output frame, with
half ties rounded up. A confirmed event can therefore move away from its ideal
retimed timestamp. The editor now records the ideal frame, chosen frame and
signed timing error for each retained event in `clip-edit-audit.json`, and appends
the input GLB hash and mapping to the event lineage. Every shifted event requires
explicit timing reconfirmation before runtime dispatch. Only numerical residue
within 1e-9 frame is ignored. Missing confirmation remains unknown. Exact
mappings preserve existing review state; later edits cannot clear an earlier
review requirement. Events outside the inclusive trim remain listed as omitted.

For example, source frame 11 in a trim starting at frame 10 and played at 2x
ideally becomes output frame 0.5. The frame-based exporter chooses frame 1,
16.667 ms later, and marks the cue for review. Source frame 12 becomes frame 1
exactly and can retain its prior timing confirmation. A creator can reconfirm
through the existing event editor; that confirms intent timing, not contact
correctness or physical realism.

This change makes frame quantization explicit; it does not implement fractional
single-character event authoring or eliminate quantization. Shared-scene timing
has a separate fractional-marker schema. No motion quality or release gate is
approved by event eligibility.

Thirteen focused tests cover shifts in both directions, half ties, exact
slowdowns, trim endpoints, stable simultaneous-event order, omitted events,
missing confirmation, explicit reconfirmation and repeated-edit lineage. The
complete minimal public Python suite passes 698 tests.

The local `reports/clip-event-retiming-v2` check edits an existing imported rig
clip from source frames 10-40 at 2x into 16 poses. Eight synthetic test cues
include two outside the trim, two half-frame shifts, one missing confirmation
and one prior review flag. Only the two exactly mapped, confirmed cues remain
eligible in the finite runtime manifest. Maximum decoded matrix and skin
errors are 1.34e-15 and 1.78e-15 m. Input geometry stays unchanged. This is an
actual GLB/metadata export check, not a fresh Godot run or human timing review.
Verification hash: `0963dd62bada00bab0bc2fc0a40e06125d54fca166a438d11c597756f90e66ef`.

The Studio marker editor now shows the most recent recorded speed-edit rounding
shift in milliseconds, labeled as a previous edit. A missing review flag stays
unconfirmed when opening or saving the editor. Previewing a cue does not
confirm it; the explicit confirmation button updates only the local draft.
Rounding notes do not enter the strict four-field marker submission payload,
and loading another source clears those notes. The desktop bundle was rebuilt.
Nine Node UI scripts and four desktop build/preservation checks pass, including
the new editor DOM simulation. No rendered-browser check is claimed.


## Confirmation through loops, transitions and runtime export

The same explicit-confirmation rule now applies to source-contribution remapping
and finite/cycle runtime metadata. Previously a fully weighted authored event
with a missing review flag could acquire `requires_review: false` during a loop
or transition; direct runtime export also treated null, zero and empty values as
confirmation. Only the boolean `false` now preserves confirmed timing. Missing,
non-boolean and pending-review states remain excluded from runtime dispatch.
Partial contributions still require review, and the marker editor can explicitly
reconfirm them without losing their source history. The reverse-export study
helper uses the same explicit confirmation rule when building its editor request.

Eleven additional model-free tests exercise missing/malformed flags, repeated
loop contributions, an exact retime followed by a transition, source immutability,
lineage and explicit reconfirmation. The combined confirmation/retiming suite
passes 24 tests. This repairs eligibility; it does not validate contact semantics.

`reports/event-confirmation-export-v1` checks both actual runtime metadata writers
using existing cycle and finite character GLBs. Seven synthetic cues exercise
explicit false, missing, null, zero, empty text, text `false` and true review flags.
Only the explicitly confirmed cue is eligible; all six others are preserved in
the exclusion audit. The cycle case includes full-weight remapping first. Both
GLBs remain byte-identical to their sources. No new engine, browser, physics or
human-review result is claimed. Verification SHA-256:
`19607804d3441833ee183f584b4b26c3ed2d38d96196fe75a0505079dbd03116`.

The complete minimal public Python suite passes 732 tests after this fix.
