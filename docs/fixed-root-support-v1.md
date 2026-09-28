# Constant-root gesture refit

The prior gesture transfer resolves most floor/support error but introduces vertical acceleration near both clip ends. Its root peak rises from0.4333 to1.8455m/s². The last six-sweep update remains0.0873 in mixed root/rotation units; convergence is unproven. See the independently decoded root diagnostic.

This experiment tests a different authoring constraint: preserve the source root trajectory up to one constant world translation, and refit the lower-body rotations. A constant translation preserves root velocity and acceleration before serialization by construction. It does not prove that the source trajectory is natural, balanced or collision-free.

## Frozen protocol

`reports/fixed-root-support-v1/request.json` freezes one150-frame beckon-left rig01 case, original foot anchors/height targets and hard root/joint/adjacent edit budgets, six additional sweeps,80 local evaluations, and all source dependencies. The fixed offset is the componentwise median of the previous full-clip root edits: [0.0002035255736887434, 0.04554132528207479, 0.0030734296145809507]m. This choice is declared once; no search over offsets, weights or sweep counts follows. All draft support weights must be1 throughout the clip for this pilot.

Initialization retains the prior six-sweep leg edits and replaces its varying root edits with that median. This is a correction of a retained development attempt and uses additional compute; it is not an equal-budget ablation or a held-out result. The root coordinates are eliminated from optimization, not constrained by a large penalty. Original frame objectives are retained; the root-curvature term is identically zero because its offset is constant. Adjacent hard bounds still apply to every leg edit.

The isolated sparse surface kernel is used with its prior48-pose/three-rig and two short-solver parity evidence. No source in existing live or queued studies is changed. The new runner is PID2448,created1790565958.9595287,exec38079.

## Preflight and tests

All150 preflight poses preserve source root acceleration within6.25e-15m/s². Moving the root alone worsens floor penetration to6.857mm, above the5mm development screen. This is an explicit failure of root placement alone and motivates refitting the legs. It is not the final candidate.

Four tests pass: root elimination with a known free-coordinate optimum; conflicting leg targets under absolute/adjacent bounds; median initialization preserving all leg edits; invalid/varying-root input rejection. Test artifact is `reports/fixed-root-support-tests-v1.json`.

## Required result

The full result must retain decoded hard bounds and untouched local transforms, root/contact sidecars, integer/half-frame floor measurements, foot support max/p95/hover, full/global and release acceleration metrics, and actual Godot import of input/prior/candidate for450 actor-frames. The existing raw/prior development comparison is unchanged. A separate decoded root-acceleration-vector difference must be≤1e-4m/s² to allow glTF float quantization; changing a pass flag cannot replace this measured check.

No benefit is assumed before these checks complete. Any floor, support or dynamics regression remains a failure. This pilot does not qualify moving support, locomotion, object/partner interactions, force balance or general motion quality. The single full-project goal and all release gates stay open.

## Completed result

The fixed six additional sweeps completed and all450 actual Godot actor-frames passed. The independent `reports/fixed-root-support-audit-v1.json` freshly decodes all three150-frame tracks and every half-frame for floor measurements, recomputes root/foot dynamics and the unchanged comparison, and checks source/export/engine bindings. Root-acceleration-vector difference from source is8.38e-7m/s²; root parameter offset is exactly constant.

| Measure | Raw transfer | Previous correction | Constant-root refit |
| --- | ---: | ---: | ---: |
| Root acceleration peak(m/s²) |0.433256|1.845543|0.433256|
| Full/half-frame floor peak(mm) |60.0479|0.9411|0.8385|
| Left support speed max(mm/s) |17.4548|0.2980|0.0891|
| Right support speed max(mm/s) |11.8811|0.1426|0.2017|
| Left support speed p95(mm/s) |12.8828|0.0756|0.0343|
| Right support speed p95(mm/s) |9.9884|0.1110|0.1017|

The ONLY failed frozen check is `Right_support_max_no_worse`: an increase of0.059126mm/s, with the new peak at step ending frame144. The absolute scale and all other metrics are retained; this tiny numerical regression is not by itself evidence of visible implausibility. No threshold was relaxed, and no animator judgement is invented. The attempt is retained for comparison and is not automatically promoted. Convergence remains unproven(last-sweep parameter change0.03016). This is useful evidence that preserving source root dynamics can coexist with low floor/support error in this one stationary gesture, not a general action/rig or release qualification. Exec38079 terminal0 consumed.


## Second rig replication and synchronized preview

The same six-additional-sweep policy was repeated on beckon-left rig02 (Quaternius), without changing the optimizer, weights or acceptance checks. The completed first trial's implementation snapshot is retained. The preparer now accepts the three declared stationary-gesture rig IDs and binds the immutable whole-study protocol and freeze alongside the selected completed case. These research IDs do not restrict product prompts.

`reports/fixed-root-support-rig02-v1` completed normally (exec61671, exit0). Independent `reports/fixed-root-support-rig02-audit-v1.json` freshly decodes all450 integer poses and447 half-frame skins and verifies450 actual Godot actor-frames. The constant translation is [-0.0006006067,-0.0337387674,0.0041181313]m. Source root-acceleration-vector error is1.67638e-6m/s², below the unchanged1e-4 serialization tolerance. Last-sweep change is0.00074365; convergence is still not proven.

| Measure | Raw transfer | Previous correction | Constant-root refit |
| --- | ---: | ---: | ---: |
| Root acceleration peak (m/s²) |0.700301|1.132548|0.700301|
| Full/half-frame floor peak (mm) |0|0|0|
| Left support speed max (mm/s) |49.053442|0.385201|0.521664|
| Right support speed max (mm/s) |44.564544|0.607542|0.955428|
| Left support speed p95 (mm/s) |37.795678|0.143971|0.147265|
| Right support speed p95 (mm/s) |33.179989|0.131675|0.291292|

Four strict comparisons fail: left/right support maximum and p95 no-regression checks. All other frozen checks pass. The result retains source root dynamics with small absolute foot drift, but the previous correction has lower drift. Do not erase this tradeoff, relax thresholds post hoc, or automatically promote either refit. Both tested stationary gestures still fail their complete development screens. Neither result establishes perceptual quality, anatomy, force balance or general action coverage.

`reports/fixed-root-preview-v1/viewer.html` compares original/prior/refit for both rig families with unchanged GLB bytes, grey preview-only materials, whole-clip bounds, synchronized timeline and orbit controls. Manifest, audit, decision and original character-license links are included. Browser smoke checks verified both loads, playback, frame seeking, reset, case switching and synchronized orbit; clicking the canvas retained all characters. No console warnings/errors were returned. `browser-verification.json` binds the tested files and screenshot. This is an organizer comparison, not a blind review packet. No animator ratings or cleanup time were invented.

At this stage, source-root preservation remained experimental and the third-rig baseline was still pending. The subsequent completed replication is recorded below. Do not add sweeps or tune offsets on these completed trials.


## Third rig baseline and completed replication

The unchanged whole-support study has completed beckon rig03 with300 engine actor-frames, independently summarized in `reports/whole-support-breadth-interim-v9`. Floor depth remains0, but root acceleration rises0.709601→5.442488m/s² at frame129. Left support maximum improves42.546→0.0876mm/s; right29.698→7.5213mm/s, with a14.039mm maximum predicted-support hover. This is a different interior root spike from the first two gesture rigs, not proof that their behavior generalizes.

The same fixed-root policy, median offset and six-additional-sweep budget completed in `reports/fixed-root-support-rig03-v1` (exec18040, exit0, consumed). The independent `reports/fixed-root-support-rig03-audit-v1.json` verifies all450 integer poses,447 half-frame skins and450 engine actor-frames. Floor depth remains0; root acceleration returns from5.442488 to the source0.709601m/s². Last-sweep parameter change is0.010116, without a convergence claim.

| Measure | Raw transfer | Previous correction | Constant-root refit |
| --- | ---: | ---: | ---: |
| Left support speed max (mm/s) |42.546421|0.087618|0.098416|
| Right support speed max (mm/s) |29.697956|7.521304|23.596550|
| Left support speed p95 (mm/s) |30.059085|0.054584|0.058778|
| Right support speed p95 (mm/s) |26.619842|1.248826|5.380591|

Six original checks fail: left/right support max and p95, right support hover, and right global foot acceleration. The larger right-foot regression is retained, not hidden behind root preservation. All three gesture rigs now have independently verified source-root preservation and1,350 actual engine actor-frames, but none passes its full development screen. Source-root preservation remains experimental.

`reports/fixed-root-preview-v2/viewer.html` adds the third rig to the unchanged comparison implementation, retaining nine unchanged GLBs and their source licenses. The v1 browser-tested two-rig build is preserved. The v2 build and all-frame bounds are verified; this new three-rig version has not had a separate browser interaction check.
