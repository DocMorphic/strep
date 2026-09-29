# Regional buffers: matched grasp continuation

On the repeated frame-121 development pose, a 0.1% solver-only regional buffer allows both hand regions to pass the unchanged exported contact checks while preserving sampled source foot support. Whole-body box clearance still fails. This is one static pose, not a completed lift, a new generated action, held-out evidence or release approval.

## Method

`reports/region-buffer-continuation-v1/method.py` runs two fresh solves from the exact same saved larger-budget candidate in `region-support-inner300-v1/preserved_feet/motion.npz`. The original frame-121 source remains the edit-budget reference. Each arm uses six stages of 100 iterations, a 600-second budget, shared-pose controls, both inferred foot supports, full sparse skin, per-vertex object constraints, augmented regional constraints, stage witness refresh and the existing export-rate guard. Optimizer state and multipliers restart; only the initial pose carries over.

The matched arms differ only in timestamp and `region_limit_margin_fraction`: zero versus 0.001. The buffer increases solver clearance/spacing/area requirements and reduces solver gap/radius/centroid/normal/anchor tolerances. It does not relax authored acceptance, original root/rotation bounds or inferred foot support tolerances. Protocol/input/implementation hashes and completed audit hashes are checked by `compare.py`; raw results and implementation snapshots remain local and immutable.

## Exported results

| Measurement | Starting candidate | Unbuffered continuation | Buffered continuation |
| --- | ---: | ---: | ---: |
| Runtime / objective evaluations | 493.985 s / 3,934 | 158.172 s / 1,234 | 162.625 s / 1,247 |
| Failed hand-contact samples / 34 | 34 | 17 | 0 |
| Failed geometry samples / 17 | 17 | 17 | 17 |
| Minimum box clearance | 1.043809 mm | 1.455999 mm | 1.767989 mm |
| Failed source-support samples / 34 | 0 | 0 | 0 |
| Maximum support drift | 3.998919 mm | 4.780190 mm | 4.116749 mm |

The starting runtime is included for context and is not part of the matched continuation budget. In the unbuffered arm the right hand passes, while the left normal error is 10.010291 degrees against a 10-degree limit. In the buffered arm both anchors remain within 5 mm, both normal errors remain within 10 degrees, and both hands have qualifying distributed contact triangles. Their minimum patch clearances are 2.059029 and 2.153534 mm. Passing hand patches does not establish whole-body clearance.

Four native skin vertices remain below the required 2 mm box clearance: the right forearm, two right-pinky vertices and a left-palm vertex. The closest is vertex 10977, weighted entirely to `RightForeArm`. `clearance-diagnosis.json` retains their identities and weights; the independent decoded-export audit is authoritative. All twelve continuation stages stop at the iteration limit, so neither convergence nor constraint infeasibility is established.

Both outputs repeat exactly across five native keys and pass original edit bounds. The buffered root lift is 10.445308 mm, minimum exported floor gap is 10.137296 mm and maximum original rotation edit is 33.494057 degrees. Twenty new Godot source/candidate actor-frames reproduce all 77 joints with maximum position discrepancy below 0.323 micrometres. Static rate checks do not establish transition quality or dynamics. Source-point support does not establish planted soles, balance or forces.

## Compatibility and review

The preceding 40 focused tests pass. A separate real-fixture comparison against the saved pre-buffer objective gives bit-identical default loss and vertex gradients, identical witnesses and unchanged default limits. It also checks buffered anchor tolerances and recorded configuration across ten regional records. This is objective-level compatibility, not a complete solver-equivalence claim.

Studio collections `region-buffer-unbuffered-review-v1` and `region-buffer-buffered-review-v1` retain source/candidate assets and geometry, rate, support and Godot evidence. Each passes thirteen file hashes and twelve permitted offline route checks. The Python snapshot remains unserved. No live browser or human review was performed; both packages remain quality-unapproved because whole-body clearance fails.

The buffer remains optional and defaults to zero. This single paired result supports testing it further, not promoting it globally. Next resolve the identified non-patch clearance failures while retaining the measured hand/support constraints, then verify transfer to full motion and broader scenes. All fourteen release capabilities remain unapproved.
