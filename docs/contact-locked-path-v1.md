# Hand clearance guide and contact-preserving native export

This follows the [palm-region experiment](palm-contact-region-v1.md), retaining
its explicitly authored surface points and 1 mm contact gap. It does not change
the old fixed-marker benchmark or the original joint/rate limits.

## Method

At 199 declared times per actor, measure the selected hand surface against its
contact half-space. Retract the wrist along the fixed contact normal when needed,
using two-bone reach while preserving wrist orientation, bone lengths and other
local channels. Refresh actual skin geometry after each reach, with at most four
steps and a 0.1 mm reserve. Freeze the exact contact instant, protected spans and
outside-window poses. Check all 22 original arm/finger pose-angle limits.

Bake the resulting local arm rotations only into editable native keys. For each
joint whose contact falls between keys, fit the two endpoint rotations using
`R_lower = R_contact exp(-fraction * omega)` and
`R_upper = R_contact exp((1-fraction) * omega)`. This retains the contact rotation
along the shortest geodesic when `norm(omega) < pi`; ambiguous arcs are rejected.
The fraction uses the decoder's native float32 clock arithmetic. Fit endpoint
closeness, then export float32 quaternions and independently decode the GLB.

Recheck original native-key angle budgets, unchanged clocks/unselected channels,
protected/outside-window poses, actual contact, all 53 full inter-actor mesh
samples, floor depth and the four original motion-cap groups. The endpoint fit
does not itself constrain geometry or speed. Neither discrete sampling nor the
contact-lock algebra certifies collision-free motion between samples.

## Results

The pose guide retracts 84 poses per actor, by up to 90.095 and 105.172 mm.
All original pose-angle limits and all 53 full inter-actor geometry samples pass;
the contact pose remains bitwise unchanged. One stricter half-space test at the
frozen contact has a 2.9792721e-8 m excess, above its 1e-8 m allowance. That failure
is retained separately from the passing full mesh screen. All four motion-cap
groups fail. This guide is not an exported animation or an accepted correction.

The native export retains a 0.999987 mm contact gap, anchor errors below
0.000045 mm and normal errors 1.002628/0.414843 degrees. Contact full-body geometry
passes. Maximum contact matrix drift is 5.643402e-8 for actor A and zero for B.
All original arm/finger native-key limits pass; clocks, unselected channels,
outside-window and protected poses remain exact.

Interpolation reintroduces intersections at three guard samples:

| Time (s) | Proper crossing pairs | Maximum vertex depth (mm) |
| --- | ---: | ---: |
| 2.016554892063141 | 14 | 0.509393 |
| 2.066666603088379 | 34 | 1.059081 |
| 2.0666666666666664 | 34 | 1.059083 |

The near-duplicate times come from native float32 and uniform float64 clocks;
both remain in the unchanged guard set. The source native motion failed 9/53
samples with 22.110409 mm maximum depth; this export fails 3/53 with 1.059083 mm.
This is a sampled geometry improvement, not an overall quality pass.

| Original-reference cap | Failing rows | Maximum excess |
| --- | ---: | ---: |
| Position speed | 144 | 0.725369 m/s |
| Position acceleration | 227 | 90.369821 m/s² |
| Angular speed | 934 | 1.937301 rad/s |
| Angular acceleration | 231 | 230.090866 rad/s² |

These caps compare against the original reference, not a human realism rating.
Some excesses worsen compared with the source motion. Floor penetration remains
6.003415 mm. No continuous collision, self-collision, engine-import or human
quality approval is established by this study. Neither candidate enters Studio.

## Reproduction and evidence

These commands need the separately acquired rig and completed local studies;
the public source snapshot does not include their payloads.

```powershell
.venv/Scripts/python.exe scripts/study_hand_plane_path.py reports/palm-region-motion-v1 reports/<fresh-guide>
.venv/Scripts/python.exe scripts/study_contact_locked_path.py reports/<completed-guide> reports/<fresh-native-export>
```

All bound inputs, archived/current methods and outputs were rehashed with no
mismatches. The guide binds 3,874 inputs, 87 methods and 58 outputs; the native
export binds 4,020 inputs, 89 methods and 59 outputs. Result SHA-256 values:

- Guide: `352bf56facbde242ddbed330021cba8a14b9245725a4e2d9bcf40a12e2737920`
- Native: `97173dfe832a8ac181fa1e3952fffc93fc14f52a3dfbc7a93cff999d66147f55`

The model-free Python source suite passes all 1,050 tests, including noncommuting
contact interpolation, shared sampler isolation, unchanged clocks, frozen-key
and original-budget rejection, surface clearance and unreachable reach handling.
No model training or reserved held-out prompts were used. All release capability
gates remain unapproved.

Next inspect the failing native intervals and constrain the actual interpolated
skin while preserving contact and original budgets. Smoothness needs its own
constrained solution; passing the pose guide is insufficient.
