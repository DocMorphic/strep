# Event-preserving arm approach probe

After the completed seven-state component study, `probe_contact_approach.py` tests whether earlier arm controls can reduce a forearm collision without weakening the achieved event contact. This is a fixed diagnostic, not an accepted animation or a replacement optimizer.

The event basis is exactly `[0,0,1,0,0]`. The middle control knot of both actors is therefore locked; the projected clearance gradient changes only earlier controls. The selected witness is actor A vertex6702 at frame66.5, the retained worst candidate collision. Its analytic directional derivative is0.820964714292 metres/radian; the true-distance central difference is0.820964714278, an error of1.39e-11. The derivative is checked before evaluating geometry.

The protocol fixes three step sizes,0.25,0.5 and1 degree maximum per control-joint vector, and four geometry samples:66.5,67,74.5,75. All three proposals satisfy the original hard edit limits, and both actors' entire event skin positions remain exactly unchanged. Fresh full meshes are queried in both directions with the32-point cap.

| Step | Selected witness depth (mm) | Worst depth among four samples (mm) |
|---|---:|---:|
|0.25°|20.839673|23.855326|
|0.5°|17.195067|25.629179|
|1°|9.886956|25.850130|

The original candidate's worst depth is24.422624 mm. The largest step improves the selected point but worsens another surface region at frame67. Event depth remains0.897661 mm, unchanged. The quarter-degree probe modestly improves the four-sample maximum, but remains worse than the original raw peak21.622598 mm and far above5 mm. It is neither selected nor exported.

All inputs, source snapshots, controls, derivatives, geometry and failures are retained in `reports/contact-approach-probe-v1`. Completion verifies all declared hashes. The result supports preserving event controls while considering multiple collision witnesses and times jointly; it rules out promoting a one-witness improvement. Full-clock, triangle, floor, anatomical and human checks remain required for any later candidate.
