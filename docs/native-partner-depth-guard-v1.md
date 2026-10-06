# Hard local partner depth guidance

The new guidance prevents the affine gaps of existing partner penetration witnesses from decreasing. The complete retained experiment stops with `InsufficientProgress` after 28 solver iterations and returns no proposal. This is a solver convergence failure, not evidence that the animation problem is infeasible. No new animation is exported or approved.

## Original acceptance and added guidance

`scripts/native_partner_depth_guard.py` appends one hard local norm for every `penetrating-vertex` witness. The original native vectors, caps, scales and derivative prefix stay unchanged. All original surface conditions remain represented through the existing certified affine row reduction. Existing producers and Studio jobs remain unchanged.

For each selected derivative row `J`, the extra norm has vector `[offset, 0, 0]`, cap `offset`, scale 0.005 and derivative `[-J, 0, 0]`. The offset keeps the first coordinate nonnegative throughout the local proof box. Consequently its norm inequality enforces `J delta >= 0`: the local witness gap must not decrease from the decoded anchor. It does not treat an already failing gap as acceptable or change the external 5 mm depth limit.

These fixed-normal, fixed-barycentric affine conditions are guidance. They do not establish nonlinear signed-distance nonregression, prevent new intersections, or certify full-scene geometry. Complete decoded native and original geometry checks remain the acceptance authority.

## Complete retained experiment

The starting point is the previously stored-native-passing one-eighth proposal, with seven absolute one-neighbour quaternion component corrections. Its complete geometry still fails, with approximately 5.195942 mm depth against 5 mm and 1,594 failed samples. Those are prior measurements; no new geometry evaluation is claimed here.

The experiment rebuilds the complete model at that decoded anchor. It retains all thirty controls, original reference, contacts, nine byte-exact source-rate arrays, all 1,707 native times and all 1,673 geometry times. Source-scale storage and the 0.02 local trust remain explicit. Central finite differences use step 0.001. Guide actor paths and digests are rebound to the anchor; external geometry limits, clocks and policies remain unchanged.

| Model population | Rows |
| --- | ---: |
| Original native norms | 29,290 |
| Extra partner gap-change guards | 2,840 |
| Complete scalar surface conditions | 277,385 |
| Equivalent encoded scalar conditions | 118,367 |
| Whole-box dominated conditions | 159,018 |

Every one of the 30,505 triangle blocks retains its nine affine conditions through direct certified implication. All 2,840 other witnesses remain encoded. Clarabel 0.11.1 stops after 28 iterations with `InsufficientProgress`. The driver returns no direction, so it creates no candidate fractions or new engine/geometry results.

## Validation and limits

All 53 focused tests pass with zero skips, including twelve new guard, opposing-direction, original-prefix and malformed-input cases. The workflow adds only the new test suite. Hosted CI is not asserted green.

Raw model arrays, complete derivatives, witness blocks, proof roots, solver result, original inputs, method archives and driver remain in ignored local reports. No model weights, credentials or generated motion payloads are published. This study uses generated fixtures and local CPU software checks; it establishes no production humanoid quality, rendering, physics, model sampling/training or human-review evidence. All fourteen release evidence arrays remain empty.


Independent replay imports neither the new guard, reduction nor solver module. It verifies every guard coordinate remains nonnegative over the proof box, every direct surface implication with exact rational arithmetic, byte-exact original native norms and derivatives, and all thirty complete scalar derivative columns. Maximum derivative difference is 3.3306690738754696e-13. A zero step and finite soft penalty 2.1338542952726747 satisfy the complete local system; solver nonconvergence is therefore not an infeasibility proof. No nonlinear geometry predicates are independently recomputed. Both CPU drivers exit zero with worker locks free and original/current/archive method bytes preserved.

| Local receipt | SHA256 |
| --- | --- |
| `reports/partner-depth-guard-probe-v1/result.json` | `2e9362063313edad45e3b0e5a46858a6766d46adc9b7c538653e109cbda4bfb9` |
| `reports/partner-depth-guard-independent-v1/result.json` | `aaef5fdac48baa1b0ddfbfcd9875e6a2ca1f0dc4c2036a45d63956916d73d115` |
