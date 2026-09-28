# Existing animation editing and contact inspection

Development progress only. The full-project release goal remains active. No training, checkpoint changes or new model generation occurred.

## What works in Studio

**Characters → Edit mesh contacts → Inspect contact errors** evaluates the current draft on the selected exact GLB without modifying motion or starting a fit. It reports each interval's maximum error and failing-frame count, sorts the worst intervals first, and jumps to the matching frame, patch and editable target. It also identifies the skin influences at the worst floor vertex. Changing the saved draft clears stale diagnostics; a result arriving for an obsolete draft/version is discarded.

The retained combined get-up failure has 11/36 failing intervals and 70/180 floor-failing frames. The worst interval is Left-fore-a, frames67–71, with 51.2 mm error at 67. The deepest vertex at 67 is 22.5 mm below the plane, weighted 64% LeftFoot, 20% LeftToeBase, 16% LeftShin. The head-clearance interval is within its 20 mm screen. This localizes the remaining conflict to foot geometry/targets instead of treating the head as the only problem. Skin influences are not independently reviewed anatomical support labels. Post-hoc evidence is separate in `reports/contact-inspection-v1`; original job packages remain immutable.

**Characters → Edit an existing animation** lists embedded clips in the imported GLB, reports unsupported clips, and prepares a selected clip for playback/contact editing. A saved humanoid mapping is required to identify the pelvis and editable bones. Profile alignment rotations and placement offsets are deliberately not applied to an existing clip. The original animated asset is retained byte-for-byte. This path requires no native SOMA NPZ or model inference. It does not yet provide prompt-based semantic editing, general trim/retime controls, BVH/FBX import or unrigged input.

The importer samples a documented 30 fps editing copy, preserving the original timing/interpolation in the source file. It supports distinct translation/rotation and nominal-unit-scale channels, independently timed samplers, linear/step/cubic interpolation, endpoint clamping and normalized quaternion interpolation. Morphs, significant animated scale, compressed/external assets and clips over 30 seconds are explicitly unsupported in this version. Existing rig limits still apply (one skin, rigid default transforms). Up to 1e-5 unit-scale float drift is accepted and every exported sample's world matrices and skin are checked against 1e-5. Linear output sampling approximates source STEP/cubic motion between samples; no continuous-fidelity claim is made.

Interpolation was implemented against the primary [Khronos glTF 2 specification, animation section and Appendix C](https://raw.githubusercontent.com/KhronosGroup/glTF/main/specification/2.0/Specification.adoc). Samplers can have different clocks, quaternion linear interpolation uses the shortest spherical path, and cubic tangents use interval duration before quaternion normalization.

## Actual external-clip trial

The licensed original CesiumMan animation was prepared through the real Studio UI as job `20260926-202128-ecb5f088`: 61 samples over 2 seconds, 19 bones. The exported skin differs from the original sampled skin by at most 4.78e-7 m, and source matrix drift is below 1.98e-6. This is a source interpolation/format check, not improved-motion evidence.

An engineering five-frame left-heel contact (frames 21–25) was selected using low surface height/speed and authored through the UI. It is not independently confirmed support. Job `20260926-202244-c3c3bb14` preserves the prepared input and fits under the existing edit caps. Floor depth improves 26.0 → 10.0 mm, but 5 frames still exceed 5 mm, so the candidate is **rejected**. Maximum authored target error is 4.20 mm. Root movement is bounded (15.3 mm vertical, 20.2 mm horizontal); largest joint edit is 14.4 degrees. The deepest frame is 22. There are no fabricated model contact predictions: input annotation lists stay empty, hover remains unavailable and authored targets are separately recorded.

The supported workflow is therefore real: existing GLB → select clip → prepare → preview → author/inspect contacts → bounded fit → inspect retained failure → download source/candidate/root tracks and evidence. Professional realism is not established by that workflow test.

## Verification

- `reports/rough-clip-authoring-v1/contact-request.json` freezes the planned request. The UI submitted identical numerical fields; only its provenance text differs.
- `import-verification.json` checks the original source, all 25 initial package entries and absence of a model-native motion file. `verification.json` checks the editing package, all served input/candidate GLB hashes, every archive entry, reloaded metrics/bounds, untouched local poses and root tracks.
- `reports/rough-clip-interpolation-v1` adds a clearly synthetic mixed-interpolation fixture derived from the licensed asset: independently timed cubic root translation, linear chest rotation and step hand rotation. This is an interpolation fixture, not an action-quality result.
- Actual Godot checks 245 clip frames across five files with all 19 bones and skinned surfaces. Maximum position discrepancy is 2.53e-7 m. See `reports/godot-rough-interpolation-v2/verification.json` and `reports/godot-rough-clip-authoring-v1/verification.json`.
- The first engine audit (`godot-rough-interpolation-v1`) failed at a STEP boundary because decimal-double 24/30 precedes the float32 .8 key by 1.19e-8 seconds. Its raw output and failure remain. V2 explicitly sends the same stored float32 sample timestamps to Godot and the source sampler; it does not loosen comparison tolerances. A regression test fixes this clock contract.
- All five GLBs have 0 format errors and 1 inherited skinned-mesh-parent warning each. Full suite: 261 passed, 4 upstream Torch warnings. JS syntax checks pass.
- UI verified existing-clip preparation, playback data, no-annotation messaging, exact-version contact binding, numerical request submission, rejected candidate display, worst-floor jump and per-contact inspection. No browser console errors observed during these checks.

## Next work

Preserve failures and improve whole-body support selection/feasibility without silently weakening bounds. Add usable rough-clip trim/retime/pose and prompt editing, then verify those transformations independently and expand to more original rigs/actions. Continue loop/transition/style, object/partner, offline packaging and release evaluation work. Independent animator ratings, cleanup-time evidence and broader held-out trials remain missing. The release matrix records only development evidence.
