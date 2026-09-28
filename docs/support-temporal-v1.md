# Root-correction smoothness: matched two-rig comparison

The revised support objective reduced sliding but introduced sharp changes in the added root correction. The completed endpoint experiment removed a separate clip-end release artifact. This comparison starts from those endpoint-repaired clips and edits only frames 36–69, leaving both the beginning and repaired ending intact.

Before running either rig, `run_support_temporal_pair.py` froze the first declared seed on both rigs, six sweeps per candidate, and root-curvature weights 0, 10 and 30. Weight 0 is an equal-budget continuation control. Every candidate and failure is retained. The new residual penalizes the second difference of the **added root correction**, not the source motion's acceleration. It is a smoothing prior, not a physical acceptance threshold or proof of realistic movement.

`support_curvature.py` includes every acceleration center affected by a coordinate update: the current frame and its two neighbors, including centers crossing the fixed edit-window boundaries. Its analytic derivative and change in energy match full-track recomputation. `relax_temporal_support.py` preserves the original joint/root and adjacent-edit limits. Eight focused tests pass, including fixed poses on both sides of an interior window and rejection of invalid inputs.

| Rig | Equal-budget control peak | Weight 10 peak | Weight 30 peak | Scope |
|---|---:|---:|---:|---|
| 01 | 6.12493 m/s² | 4.72893 m/s² | 4.72588 m/s² | Whole clip and edited window |
| 02 | 15.19529 m/s² | 6.87088 m/s² | 6.88431 m/s² | Edited window only |

Rig 02 retains a larger **12.14551 m/s² peak at frame 2**, outside the editable window, with both nonzero weights. The temporal correction did not repair that beginning-of-clip artifact. Its support draft ramps from 0.25 to 0.75 to 1 even though the interval begins at frame 0. The saved start-boundary diagnostic motivates a separate controlled test; a start repair has not yet been implemented or verified.

The floor and contact tradeoffs are small on these two examples but are still recorded. On rig 01 the whole/half-frame maximum floor depth changes from 0.68953 mm in the continuation control to 0.69490/0.69498 mm. On rig 02 it changes from 0.50139 to 0.49974/0.49972 mm. Worst predicted-support p95 speed remains near 0.00202 m/s and 0.00259 m/s respectively. Individual support-speed peaks remain much higher, about 0.112 m/s and 0.369 m/s; low p95 is not a whole-contact success claim. Rig-02 right-foot hover increases slightly, from 10.6050 to 10.6628/10.6649 mm. Contact labels are still unconfirmed.

`reports/support-temporal-v1` completed all six candidates. Raw, endpoint-repaired initializer and all three candidates per rig passed actual Godot checks: **1,500 actor-frames**, 19 bones on rig 01 and 65 on rig 02. Independent decoded edit/preservation checks pass; transforms outside frames 36–69 agree to numerical precision, and the repaired last-step speeds are unchanged. No global stationarity, physical balance, anatomy, action correctness or animator approval is inferred. The six-sweep fits retain nonzero parameter changes.

`reports/support-temporal-summary-v1` verifies the complete declared population, source/implementation/result/trace/engine hashes and agreement between decoded acceleration traces and independent measurements. Its table includes all methods and the remaining global peak. The inspected figures are in `figures-v3`; earlier layouts remain retained because their legends obscured data or the title. Foot-speed plots show all steps, including intended swing motion; they are not all measurements of sliding. Matplotlib ran in the isolated plotting environment without changing the model runtime.

The moderate and stronger settings give similar results on this development seed. These observations do not select a universally optimal weight, prove generalization to other actions, or qualify either candidate for release. Next: isolate the clipped-start support ramp with an equal-budget control, then broaden the combined correction under a fixed protocol and independent review.
