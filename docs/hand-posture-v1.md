# Timed hand-posture authoring

`scripts/hand_posture.py` authors explicit local finger rotations on an existing 30 fps rigged GLB. The recipe binds the exact source file hash, declares one or two mapped hand roots, and supplies target quaternions with fade-in, hold and fade-out frames. Targets are absolute local orientations, blended from the original finger pose on each frame. Thus a rough finger track can be edited without assuming it is constant.

The tool preserves all other local transforms, every local translation and all frames outside the intervals. It rejects stale source hashes, targets outside the declared hands, edits of the hand roots themselves, duplicate/overlapping targets and malformed quaternions. Explicit angular and per-frame correction budgets are checked before export and again on decoded GLB frames. These are edit budgets, not anatomical limits or a continuous-time dynamics guarantee. The hand-root mapping must be correct; a numeric node declaration cannot establish its anatomical identity.

The input clip, recipe, implementation snapshot, exported GLB, preservation/budget report and posture-intent intervals are retained. The intent file does not claim actual hand contact or create confirmed gameplay contact events. The same core is now available in the main Studio through Characters > Hand posture, with immutable comparison and package outputs. The separate personal portable installation has not yet been rebuilt with this addition.

Run from the project root with a recipe matching the selected GLB:

```powershell
.venv\Scripts\python.exe scripts/hand_posture.py SOURCE.glb POSTURE.json NEW_OUTPUT_DIRECTORY
```

`reports/hand-posture-v1/A/posture.json` is a complete example for its retained `A/input.glb`. Its target is the original mesh reference hand pose, explicitly unreviewed. It must not be advertised as a validated open-hand/high-five preset. The editor accepts other authored quaternions and independent intervals for either hand; it does not infer a grasp from a prompt or prop geometry.

## Executed evidence

Both original high-five actors received nineteen finger targets around frame 75, with fades over frames 60–90. Each preserves 121 of 150 frames outside the edit interval. Maximum finger edit is 34.461 degrees and maximum adjacent correction is 3.441 degrees. Independently decoded world transforms outside the hand chains differ by at most 0.000000068. Source root positions, smoothed root, heading and predicted foot-contact arrays are unchanged.

Both actors were actually imported into Godot, with every one of the 77 bones checked on all 150 frames: 300 actor-frame samples. Five tests pass, covering timing and quaternion interpolation, disjoint intervals, moving source fingers, simultaneous two-hand edits, hierarchy/hash/quaternion validation, zero strength and rejection of excessive/abrupt edits. No full-suite or independent animator approval is claimed.

The edited pair was then processed by the existing coupled arm fitter as a separate experiment, `reports/paired-hand-prototype-v6`. It matches palm points within 0.00533 mm but creates **18.014 mm partner penetration**. Actual Godot import and preservation checks pass; contact quality fails. The reference posture is not adopted as an automatic correction.

A second recorded experiment, `reports/palm-frame-calibration-v1`, addresses the original point's noisy orientation. Its bind-mesh normal differs from a knuckle-derived palm-plane hint by 36.105 degrees. A fixed geometric rule selects central-palm vertices within 45 mm of the estimated center and within 5 degrees of that hint, then chooses the point closest to the original probe. Seven vertices qualify; vertex 7159 is selected at 4.844 degrees. The original vertex 14712 and all previous results remain unchanged.

That new authored point also fails: `reports/paired-hand-prototype-v7` reaches 0.03976 mm point separation but **19.872 mm partner penetration**, with 274/275 vertices exceeding 5 mm. Both variants pass another 600 actual Godot actor-frame comparisons. Normal alignment alone therefore does not explain or fix the overlap. Neither heuristic is anatomically approved, neither candidate is promoted, and no whole-window collision pass is inferred from a failed event frame.

Further work needs hand-posture review and contact regions constrained against actual surfaces. A matched central vertex is not sufficient evidence of a believable high-five.


## Studio workflow and integration evidence

Choose an existing character motion and its input/transfer/corrected version, then open **Hand posture**. Choose either mapped hand. Load the rig default reference or capture the current preview's finger rotations; optionally adjust individual local XYZ angles. Set start, full start, full end, end and strength, then add the interval. Add disjoint intervals or independent intervals on the other hand and create a candidate. The selected source remains unchanged. Comparison retains the current frame; GLB, recipe, intent and verification downloads accompany the animation package. Closing/reopening the editor on the same source retains its draft; changing the source resets it. A rig without finger skin joints reports that limitation.

`rig_posture_edit.py` binds roots to the saved rig profile, checks the selected source hash/clock, snapshots the original source/input and independently verifies protected body transforms. Root, contact-annotation and event-timing bytes are preserved. Existing timing confirmation is not contact confirmation. Contact target recipes are retained with the new candidate hash and an explicit refit/review requirement; old correction success is not inherited. Current reports contain current roundtrip/floor evidence; source diagnostics remain in `input/report.json`. No periodic runtime adapter is emitted by this edit.

`reports/hand-posture-studio-v1/completion-verification.json` records:

- Nine focused tests passing (1.06 s), including mapped-root rejection, stale source/clock, arbitrary body-root substitution, descendant inventory, sidecar/event preservation and historical-quality separation. No full suite run.
- Actual HTTP rejection of stale source, wrong mapped root and stale clock, each 400.
- A 120-frame Quaternius male wave with 25-degree local edits to four left-finger joints, max adjacent correction 1.869 degrees. Protected body world error 7.81e-8; 61 frames outside the interval preserved.
- Browser capture/edit/submission of a right-finger interval on the first candidate, creating a second output while preserving the first edit. Candidate/input switching remains on frame 40. No captured browser console errors.
- Four actual Godot imports (both versions of the canonical and browser jobs), 480 actor-frames, 65 bones each. Max position discrepancy 4.27e-7 m, max basis-element discrepancy 6.96e-7. Presence of skinned surfaces is checked, not GPU-rendered skin or naturalness.
- Main server downloads verified against local hashes; every ZIP member byte-verified.

Canonical job: `reports/rig-jobs/20260927-175713-84d100b0`. Browser job: `20260927-175536-ab796917`. First retained job: `20260927-175338-39f04f09`. The first two precede canonical report separation; their inherited source measurements are historical, not current-candidate evidence. Contact-target retention was added and unit-tested after the canonical job; that particular input has no contact-spec. Implementation snapshots remain in each package and the evidence distinguishes them from the final live source.

This development example is not a held-out realism test or a validated gesture/grasp preset. The model still does not generate articulated finger tracks; these rotations are explicitly authored.
