# General rig-clip transition authoring

2026-09-26. Development progress under the existing full-project goal. Release approval remains open.

Studio Characters now has **Join clips**: select ranges from two saved versions on the same character/mapping, set an overlap and explicit heading adjustment, then bake one finite GLB. It works on imported animations, generated transfers, corrected versions and edited clips. Both inputs and original source provenance are snapshotted. Transition history is retained under `source/transition-history` so subsequent edits do not discard the second original motion.

The next clip's pelvis XZ position aligns to the first clip at overlap start. Its world Y remains unchanged; heading is a user-specified Y rotation, not inferred from a possibly tilted pelvis. This rigid placement acts on the pelvis subtree; rig parent nodes remain intact. Local translations interpolate linearly and local rotations interpolate along the shortest rotation path with smoothstep weights. Source poses outside the overlap are preserved. Only source animated nodes and the pelvis receive tracks; static mesh nodes are not given ineffective animation channels.

This is offline asset baking, consistent with the distinction between animation blending and engine root-motion extraction in [Godot's AnimationTree documentation](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html). Rotations export as normalized quaternion tracks using glTF LINEAR interpolation; the rotation interpolation requirements are documented by [Khronos glTF 2.0](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc). The interpolation curve and alignment policy are Strep implementation choices, not claims of physical validity from these sources.

## Time and contact provenance

The saved timeline records each output frame's contributing source frame(s) and weights, plus the second clip's placement transform. Studio boundary buttons seek the start/end of the blend and show source frames and percentages. These boundary markers are authoring events, not semantic gameplay/contact events.

Predicted support during overlap uses the intersection of positive-weight source contributors. Missing annotations remain unknown; they do not establish absence of contact. Source origins are recorded separately. Source-authored mesh targets are transformed with clip placement and stored with their output frames/weights in `contact-review.json`. They are retained for review, not automatically fitted or declared compatible. Contradictory or missing support is diagnostic. Object/partner clocks are not handled by this single-character join.

Subsequent contact edits copy the unchanged event/timeline/review sidecars. Trim/speed edits preserve input sidecars, resample review weights and ambiguity flags, and move in-range events to the nearest output frame (half ties round up), recording dropped events. Pose or speed changes still require new contact/dynamics review.

## Executed studies

| Final transition job | Sources / overlap | Output | Measured failures |
| --- | --- | --- | --- |
| `20260926-210543-eddc7280` | Quaternius female edited wave → calibrated kick, 10 frames, +15° | 141 frames | Floor 47.8 mm, 113 frames over 5 mm; 106° maximum source local-pose disagreement; 15 joint/frame support disagreements |
| `20260926-210701-acfd72dc` | Cesium imported/edited clip → generated/corrected wave, 8 frames, −20° | 133 frames | Floor 41.0 mm, 7 frames over 5 mm; 109.6° disagreement; 36 joint/frame ambiguous support entries |

Maximum half-frame floor depths are 47.3 and 43.1 mm respectively. The wave/kick's existing kick penetration remains; the imported/generated overlap also introduces substantial depth. Maximum root acceleration is 7.50 and 16.64 m/s² respectively; these are diagnostics, with no realism threshold or pass inferred.

The first wave/kick was authored through the actual UI. Earlier jobs `20260926-210243-e9780b68` and `20260926-210410-4f821a81` are preserved in v1. They exported unnecessary static-mesh animation tracks (additional validator warnings); v2 removes them without changing the intended motion. V1 and v2 are independently verified, not overwritten.

Experimental contact job `20260926-210755-7717c78e` fits source-authored targets only where a source contributes weight one; there is no fixed contact target through mixed poses. It reduces integer-frame floor depth from 41.0 to 7.43 mm, with patch error 2.73 mm, but still fails at two frames. Worst floor vertex 2002 at frame 8 (before the blend); half-frame depth remains 8.50 mm. It is **rejected**, with unchanged 5 mm floor / 20 mm contact screens. No dynamics/animator approval is implied.

Retime job `20260926-211218-0eba552b` trims the 133-frame mixed join to source 0–40 at requested speed 1.5: 28 output frames, effective speed 40/27. Transition events 13/20 become 9/14. Contact-review targets, earlier ambiguity flags and complete two-source lineage stay in the package. The original sidecars remain available under input.

## Verification and limits

`verify_rig_transitions.py` checks decoded GLB local transforms against per-node SciPy Slerp, independently reconstructed source clocks/alignment, root tracks, half-frame mesh depth, served-file hashes and every archived entry. V2 maximum local matrix error is 3.77e-7. Each transition ZIP contains 81 entries. Corrected and retimed jobs have separate exported-geometry/bounds/package checks.

Evidence: `reports/rig-transitions-v1`, `rig-transitions-v2`, `rig-transition-contact-v1`, `rig-transition-retime-v1`; actual engine evidence uses the corresponding `godot-` folders. V2's six input/output GLBs total 566 frames, with 19/65 bones and all skin surfaces imported. Maximum Godot joint-position error is 4.37e-7 m. Contact-chain files add 266 verified frames and retiming files add 161. Every v2/contact/retime GLB has zero validator errors and only inherited warnings (six per Quaternius file, one per Cesium file).

This does not implement universal natural transitions, general loop authoring, contact-preserving blend optimization, force balance, semantic prompt editing, object/partner clock synchronization or held-out animator evaluation. Large pose discrepancies and new penetration remain visible failures. The next quality work should address support-aware transition selection/fitting and generic loops; a smooth interpolation and successful import are insufficient evidence of usable motion.

Final full regression suite: **280 passed**, four upstream Torch deprecation warnings. Tests include source-hash/range/rig validation, world placement, preserved unblended poses and parent nodes, source clocks, prediction masks, aligned authored targets, lineage retention, event retiming and unchanged contact-edit sidecar copying.
