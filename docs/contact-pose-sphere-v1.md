# Full-distance contact reach bound

The stronger three-dimensional bound proves that the retained **kick-11** stationary foot request cannot pass the current native 22 cm joint-change screen and 5 mm pin tolerance together, under the stated rigid-skin assumption. At frame 50 it requires at least **26.443903 cm** relative to raw, or **26.519804 cm** relative to limb. The previous componentwise test did not prove a conflict; its no-conflict result was not a feasibility guarantee.

This diagnoses a request/policy incompatibility. It does not establish that the animation type is impossible, that a 22 cm change is intrinsically unrealistic, or that the generator cannot kick. The budget limits an edit's deviation from a reference at the same frame, not character travel. The original target, request, failed outputs and acceptance policy remain unchanged.

## Certificate

For a skinned material point, write `v = sum_j w_j (R_j q_j + t_j)` with nonnegative skin weights. Suppose each candidate joint position differs from its reference by at most `D`, every candidate rotation has operator norm at most `K`, and the target error is at most `epsilon`. The triangle inequality gives the necessary condition:

`||target - sum_j w_j t_ref_j|| <= D sum_j w_j + K sum_j w_j ||q_j|| + epsilon`.

`contact_pose_sphere_bound.py` evaluates this condition using the exact rational values of the supplied floating-point inputs. Each bind-vector norm receives an upper rational enclosure with 96 binary fractional bits. `isqrt` and integer comparisons ensure the enclosure is outward; floating-point square roots are not trusted to certify feasibility. The target distance is squared exactly and compared against the square of the upper allowed distance. A positive exact squared margin proves the incompatibility under the stated assumptions. A lower square-root enclosure also supplies a conservative reported lower bound on required displacement.

The method retains `D = 0.22 m`, `K = 1.02`, the `0.005 m` pin tolerance and an additional `0.000001 m` arithmetic reserve from the earlier diagnostic. It handles all supplied influences and their actual weight mass. It does not assume arbitrary scaled bones satisfy the rotation bound. No-conflict results do not prove kinematic, temporal, collision or physical feasibility, and the certificate concerns native keys, not exported interpolation.

## Retained measurement

All 316 saved native frame/reference inputs from the eight-case [earlier study](contact-feasibility-diagnosis-v1.md) were reevaluated after verifying the original motion, mesh and contact hashes. The exact squared margins were independently replayed.

| Case | Conflicting frame/reference pairs | Largest required displacement |
| --- | ---: | ---: |
| Crawl, seed 11 | 13 | 55.630173 cm |
| Kick, seed 11 | 2 | 26.519804 cm |
| Crawl, seed 22 | 0 | 3.098192 cm |
| Kick, seed 22 | 0 | 0.241743 cm |
| Both wave and both jump-land cases | 0 | 0 cm lower bound |

Crawl conflicts remain raw frames 50–56 and limb frames 50–55. The newly proved kick conflicts are frame 50 against both references. Zero lower bounds are conservative information, not zero error or approval.

Twenty focused tests pass across both bound modules, including diagonal conflicts missed by per-axis checks, tighter Euclidean lever allowances, exact square-root enclosure comparisons at large and tiny scales, sixty constructed rigid candidates within budget, all eight influences, reserve handling and invalid inputs. Local reports remain under ignored `reports/contact-pose-sphere-v1`; no new animation or engine observation was produced by this diagnostic.

The body-constraint fitting experiment had already started before this stronger certificate was found. Its source stays frozen while it finishes; its result cannot satisfy both original native criteria under the certificate assumptions. Do not pursue more iteration-only retries or change the target/limits silently. Integrating this certificate into Studio's preflight is the next step after the live study is accounted for. All release capabilities remain unapproved.
