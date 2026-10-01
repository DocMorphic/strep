# Absolute and reference-excess guards for native contact fitting

The [preceding experiment](peak-guarded-contact-v1.md) improved a weighted motion
objective while passing per-joint reference-excess guards, but increased absolute
angular-acceleration peaks. Reference-bin caps vary with time, so a peak can move
into a more permissive bin and grow without increasing its excess.

This matched experiment starts again from `contact-rate-path-v1`, not from the
candidate with increased absolute acceleration. It preserves the same 36 controls
per actor, 120-iteration budget, original joint references, fractional contact,
0.45 mm auxiliary hand clearance and original motion acceptance caps.

## Two bounds at each sample

For each rate kind and joint, freeze both quantities from the starting serialized
clip: its positive peak excess over the original time-dependent cap, and its
absolute maximum rate. Each candidate sample must satisfy both bounds. The
optimizer uses the minimum of the two fixed envelopes, equivalent to imposing
both inequalities separately without doubling its constraint-row count.

Actual acceptance permits only the existing 1e-7 numerical peak allowance in the
corresponding rate unit. Proposal-only inward reserves are the smaller of 10%
of the respective positive peak and 1e-4 times the rate's objective scale.
Zero peaks receive no reserve. The existing proposal hand-plane reserve remains
1 micrometre. These numerical reserves are not realism thresholds, certified
rounding-error bounds, or changes to original motion acceptance.

Proposal constraints cover the affected arm subtree. Serialized acceptance and
independent export decoding check every joint and both bounds. Original cap
failures, failure counts, contact error, joint budgets, untouched channels,
protected poses and sampled mesh intersections remain separate evidence.
A passing non-regression guard does not repair an already poor starting clip.

## Reproduction and validation

```powershell
.venv/Scripts/python.exe scripts/study_dual_guarded_contact.py reports/contact-rate-path-v1 reports/<fresh-dual-guarded-fit>
```

The local source-evidence chain and separately acquired character are required.
Raw earlier experiments stay unchanged. Tests check the changing-cap counterexample,
equivalence to separate inequalities, both proposal/actual envelopes, source
feasibility, frozen source arrays, zero peaks and omitted-joint regressions.

Both actors reach the 120-iteration limit. Every tested serialized step, from
full strength to 1/256, fails an actual guard. Both selected GLBs remain
byte-identical to the starting clips. All 53 sampled mesh checks pass because
the source is retained; this is not improved motion. All four original rate
acceptance groups still fail. A read-only replay identifies the rejecting
constraint families without rerunning optimization. No Studio selection, release approval, new training or held-out
assessment follows from implementing this guard.


## Replayed rejection and structurally frozen samples

The saved proposal replay reproduces all 18 serialized attempt scores and minimum
constraints within 1e-10. Actor A's full step increases the LeftHandIndex1 absolute
angular-acceleration peak from 196.237019 to 197.464545 rad/sÃ‚Â². Actor B's full step
violates the LeftArm reference-excess acceleration envelope at 1.441667 s and also
misses its hand plane. Even the smallest tested steps fail at least one rate bound.

The replay also exposes an impossible **proposal-only** requirement: a rotation
of LeftArm, LeftForeArm or LeftHand cannot move the origin of LeftArm. Yet the
absolute reserve demanded that this origin's maximum positional acceleration
fall by 0.001 m/sÃ‚Â². The proposed origin acceleration remains exactly at its source
value (5.869754 m/sÃ‚Â² for A; 8.011927 m/sÃ‚Â² for B). Frozen samples outside the editable
native-key support can create the same issue. This is a defect in reserve placement,
not proof that the original motion constraints are infeasible.

A follow-up computes conservative structural dependency masks. A joint's position
depends on controlled strict ancestors; its rotation also depends on a control at
the joint itself. A native edited rotation key can affect only the open interval
between its neighboring keys. Speed uses the union of two pose dependencies, and
acceleration the union of three. The masks deliberately overestimate freedom at
locked contact poses and basis zeros rather than omit a potentially changing row.

Only proposal rows with no structural dependency are omitted. Every joint and
sample retains both actual envelopes during serialized acceptance and independent
decoding. No final threshold is relaxed. Tests cover own-origin invariance,
frozen interpolation endpoints, derivative stencils, noncommuting native rotations
in double precision and float32, and rejection of a changed omitted row by final
acceptance.

```powershell
.venv/Scripts/python.exe scripts/diagnose_dual_guard_proposal.py reports/dual-guarded-contact-v1 reports/<fresh-proposal-diagnosis>
.venv/Scripts/python.exe scripts/study_supported_guard_contact.py reports/contact-rate-path-v1 reports/<fresh-supported-fit>
```

The supported fit again starts from `contact-rate-path-v1`, with the same controls,
objective and iteration limit. Both actors accept full-strength serialized updates.
Actor A reaches the 120-iteration limit; actor B converges after 82 iterations.
Their weighted objectives decrease by 4.9632% and 12.3575%, respectively.
Only 14,257 structurally mutable proposal rows remain per actor, compared with
15,822 subtree rows previously. Final acceptance still covers every joint.

All 53 sampled inter-actor mesh checks pass, with zero crossings and vertex depth.
Contact gap is 1.00002477 mm; anchors miss their targets by about 31/21 nanometres.
The 0.45 mm auxiliary planes pass; the stricter 0.5 mm plane comparison fails.
Original edit budgets, clocks, untouched channels and protected poses pass.
Maximum sampled floor penetration remains 6.003415 mm; it is not corrected here.
An independent decode confirms zero regressing absolute peaks in every joint
and all four rate groups over the same uniform audit interval.

Original motion limits still fail:

| Rate group | Failing rows | Maximum cap excess |
| --- | ---: | ---: |
| Position speed | 143 | 0.416848 m/s |
| Position acceleration | 294 | 63.870684 m/sÂ² |
| Angular speed | 1,330 | 2.206541 rad/s |
| Angular acceleration | 222 | 229.019441 rad/sÂ² |

Contact-marker velocity jumps remain 0.333194/0.426167 m/s. The largest acceleration
excesses now occur earlier in the approach at 1.591667 s. The source's 278 failing
position-acceleration rows increase to 294 despite lower excess and absolute peaks.
This illustrates why failure counts and original acceptance remain separate.
Next test finer temporal control around the early approach under both unchanged
peak guards and original edit/contact limits; a lower scalar score is insufficient.

All 1,081 model-free Python source tests pass. The comparison package at
`reports/native-contact-review-v4/viewer.html` adds this result to the four earlier
versions. All ten copied GLBs pass offline format/loader checks with zero errors
or warnings. Browser rendering, engine playback, continuous collision, human quality
and release approval remain unverified for these new exports.

## Bound evidence

| Local study | Inputs | Methods | Outputs | Result SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `dual-guarded-contact-v1` | 4,475 | 98 | 60 | `d87a4b5e0bebb444cf2716bb69b3c504d26e69a091b11c3e6f92369734c4d85b` |
| `dual-guard-proposal-v1` | 4,634 | 99 | 2 | `6e795871d2e6cf340d79bf934af5b50d385ebd916af76945bb9a26b4834c7a01` |
| `supported-guard-contact-v1` | 4,475 | 99 | 60 | `6e02ad7d917a4a20d8defab672bf63bca3600883c128527e7dfd4d39702d8b82` |
| `supported-guard-absolute-rates-v1` | 4,635 | 100 | 2 | `7ad7564faa0ee74f62f61360633d36ee70364bacacd20b8b57377603be34573a` |
| `supported-guard-turnaround-v1` | 4,635 | 100 | 2 | `153564e8d596ad1ce97b4757512c360be2c60e4b347f3d014f050bc7bf719a9e` |

| `supported-guard-proposal-v1` | 4,635 | 100 | 2 | `10c1cf03a0000f2ea8d873d84990e1eb78d9eb6215af0b2a36514e836f2c597e` |

The replay handles both complete-subtree and structurally supported proposal rows.
It also reproduces both accepted full-step scores and minimum constraints within
1e-10; the saved source clips and original rejected study remain unchanged.
