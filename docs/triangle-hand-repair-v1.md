# Triangle-witness hand repair experiment

The interval audits identify crossings that vertex containment can miss. This
experiment turns retained triangle pairs into an optimization objective, then
checks the exported motion and queries actual mesh triangles again. It does not
claim a repaired interaction: the completed trial accepts no step.

## Constraints and editable support

The donor is the unchanged larger-trust paired candidate used by the interval
studies. Thirteen independently verified first-pair witnesses are retained:
ten from the full native-clock audit and three from the earlier short audit,
including its 1.94 s crossing with zero vertex-containment depth. The thirteen
timestamps are distinct; some belong to the same native interval.

The preceding six-key editor cannot influence several early crossings. The
new experiment expands only the earlier approach support, from
[1.74093949795, 2.09172248840] to [1.54049241543, 2.09172248840] seconds. It has
ten editable native keys and 140 independent wrist, swivel and hand-orientation
controls, with zero controls at both anchors. Existing donor controls map by
exact key time; new keys start unchanged. Their decoded poses reproduce the
donor within 2e-10 matrix tolerance.

The original reference remains the source of per-joint speed/acceleration caps
for both position and rotation, measured on the same 148-pose clock. The original
45-degree native edit ceiling, guide speed limits and maximum guide amplitudes
remain in force. The longer window changes available keys and distance-to-anchor
guide envelopes; it does not rebase motion caps on the improved donor. All 962
old signed vertex witnesses also retain fixed ceilings of their donor depth or
5 mm, whichever is greater, plus the existing 1e-8 m numerical slack.

The protected contact time is 2.0917225950783 s. Twelve retained triangle
witnesses lie inside editable support. The thirteenth is at the fixed end key,
2.0917224884033203 s, and cannot be repaired by these controls. It is excluded
from the active objective but explicitly retained in the failure report and
fresh geometry population. Full motion outside the editable keys and protected
contact endpoints must reproduce exactly after export.

## Triangle objective

For each retained active pair, select a fixed direction from center-pose face,
edge and Cartesian axes using the strongest available projected gap. Keep this
direction fixed throughout the local experiment. All nine pairwise vertex gaps
are separate rows, with a requested 1e-8 m separation. This avoids differentiating
a changing minimum or choosing a new favorable direction during a step.

Positive gaps for all nine rows separate those two triangles at that timestamp.
They do not establish mesh clearance, penetration depth, contact quality or
continuous-time safety. A fixed direction is a local correction choice; failure
does not prove no other direction or parameterization can succeed.

The existing norm-constrained local solver uses float64 proposal derivatives,
actual float32 quaternion acceptance, trust sizes 0.1 / 0.01 / 0.001, and eight
exact backoffs per proposed direction. Original motion and witness-envelope
constraints remain hard acceptance gates. Fresh triangle queries inspect the
exported GLBs at all thirteen retained times.

## Completed result

The first local iteration accepts none of its 24 exact trials. Every trial has
a negative preserved constraint margin; the largest predicted improvement is
only about 0.0000163 mm in the active triangle gap violation. The configured
three-iteration run stops immediately with `no_exact_feasible_improvement`.

The final active fixed-axis violation stays at 1.295077 mm. This number is an
objective residual, not anatomical penetration depth. Both exported GLBs are
byte-identical to their donors. Original motion limits, all old witness ceilings
and protected contact endpoints pass. Fresh queries still find all thirteen
retained proper crossings and 3,281 proper triangle-pair crossings summed over
the thirteen timestamps. These are pair-time observations, not 3,281 independent
animation defects. No candidate is approved or substituted into Studio.

This is a failed local repair with a broader editable approach. It does not
prove global infeasibility, justify loosening motion limits, or establish that
more training data is the remedy.

## Protected contact diagnosis

The frozen witness uses triangles 10562 and 9994. Independent common-interior
point checks confirm a proper crossing both at the frozen native key and at
the exact protected contact time. At the latter time the minimum barycentric
weight is 0.100294 and the scaled equality residual is below 6e-17.

The first triangle's mean skin influence is 99.947% `LeftHandPinky1`; the
second's largest influences are 74.668% `LeftHandThumb1` and 21.050%
`LeftHandIndex1`. These are skin-weight measurements, not inferred anatomical
labels. They motivate testing finger-posture freedom with explicit preservation
of palm/contact targets and original motion limits. That experiment must state
its changed control scope; silently removing the existing whole-pose guard
would not be a valid comparison.

## Evidence and reproducibility

Historical proof code is checked against its archived implementation, while
asset and result hashes remain exact. This matters because the older short
proof predates the swept-box count optimization. All retained crossings are
independently reproduced on the donor before optimization. Two regression tests
verify that newer current code does not invalidate archived proof bytes, and
that changed assets or archived code still fail validation.

The complete minimal suite passed 856 tests before those two archival checks
were added; the resulting 12 objective/provenance tests pass. The CI list now
contains 858 tests. Previous commit `ff31fbf` passed hosted Windows/Linux checks.

Local immutable outputs:

- Result: `reports/triangle-hand-repair-v1/result.json`, SHA-256
  `721e721eca884a83a1ff0ecd2dd0ba953322ae7571c67a3f25df369030e696f0`.
- Request: `b206a7b54599e93143dba663d3c6c4ff7424ee2f5a81b553744c615bbeb5049b`.
- Fresh geometry summary: `9e8ff2f3e6835f33ee8629a9acfaf7f395cc22e9606ffcd6eee2e64f3af1ff3a`.
- Decoded motion: `0b12405c81c03e47911669b93cb4b76e611e73d99a9601a2b737ec89ae330a20`.
- Protected contact diagnostic: `reports/protected-contact-crossing-v1.json`,
  SHA-256 `21a99a3a7cd3d515925ee4f9380f333cf02aea2adea02b0e49c89d2b1340347b`.

```powershell
.venv/Scripts/python.exe scripts/study_triangle_hand_proposal.py reports/scene-pair-hand-norm-larger-trust-v1 reports/<fresh-output> --proofs reports/adaptive-skin-full-proof-v1 reports/adaptive-skin-proof-v1 --iterations 3
```

No new generation, training, held-out evaluation, engine quality or animator
approval is claimed. The general authoring goal and all release gates stay open.
