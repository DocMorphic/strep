# Individual contact-condition protection

The first [contact-normal guidance experiment](native-contact-guidance-v1.md)
improved aggregate error while increasing opposition error from 39.1619 to
39.2352 degrees. The saved half-step remains visible. Current surface-vector
fitting prevents that tradeoff for each authored orientation and facing-side
condition at each exact contact point and clock.

For ordered normalized contact residuals `before` and `after`, every decoded
candidate must satisfy `after <= max(0, before)` element by element. A passing
condition can use its existing slack while remaining passing. A failing
condition cannot gain excess. There is no positive acceptance tolerance for
this guard, and missing/nonfinite/mismatched populations reject evaluation.
Aggregate max/squared-error checks, original point/motion feasibility and the
existing geometry score still apply. At least one objective must improve.

`native_contact_norms.protect_rows` duplicates contact norm rows into the hard
proposal prefix after the original native rows. Separate guard caps use the
greater of each authored cap and its current decoded base-vector length. The
unchanged authored rows remain in the minimax objective and final surface audit;
the guard cap is never reported as a relaxed quality limit. Their Jacobian rows
are duplicated in the same order. Original geometry rows remain in the soft
objective, with separate [worst-proxy proposal bounds](native-geometry-guards-v1.md).

Decoded restoration now responds to individual contact regressions even when
all original native rows pass. It fills the augmented hard prefix with actual
decoded residuals, including the difference from each original iteration's
contact bound. Measured proposal margins can tighten this prefix; they do not
change final authored limits. A passing affine model is not sufficient for
acceptance after export.

Every probe records `contact_rows_nonregressing` and
`maximum_contact_row_regression`. Optimizer metadata records
`individual_contact_rows_protected`. This applies when an explicit surface
policy accompanies `surface-vector`; other proposal modes retain final
surface filtering only. Complete mesh, between-clock, engine and human quality
requirements remain separate. Mesh normals still follow authored winding and
do not establish intended anatomical contact.

## Matched retained high-five experiment

Two primary iterations start from the same 35-iteration clip as the initial
aggregate-only experiment, with identical source actors, contacts, policies,
placements, edit permissions, trust and restoration budget. Only individual
contact protection changes. The first iteration accepts no candidate. The
second accepts its third restoration attempt, retaining one full proposed step
at the reduced trust radius. Its initial proposal fails both native motion and
the individual orientation guard and remains rejected.

| Measurement | Common start | Guarded retained step |
| --- | ---: | ---: |
| Contact point separation | 25.9743 mm | 24.8464 mm |
| Maximum partner containment depth | 20.7519 mm | 20.4945 mm |
| Proper surface crossings | 478 | 482 |
| Vertices deeper than 5 mm | 396 | 389 |
| Failed sampled geometry conditions | 7 | 7 |
| Normal opposition error | 39.1619 degrees | 39.1568 degrees |
| Source facing-side projection | -25.5183 mm | -23.8770 mm |
| Target facing-side projection | -21.0228 mm | -20.8896 mm |
| Maximum positive surface residual | 5.00366 | 4.67541 |
| Squared positive surface residual sum | 44.34132 | 40.94513 |

Every original point/motion condition passes. All three contact conditions
improve relative to the common start, but they still fail the exact prototype
surface policy. Complete geometry still fails and crossing count increases.
Originals remain selected. No stage rise, weight conditioning, new seed, model
inference or training is applied. This alternative also records 37 cumulative
attempted primary iterations; it does not extend the earlier aggregate-only
half-step or imply 37 accepted steps. The single-contact experiment does not
establish broad motion or interaction quality.

Local failed and retained outputs remain under
`reports/native-oriented-surface-fit-development-v2/`. The previous half-step's
saved residuals pass aggregate nonregression but have a positive orientation
row regression of about 0.004613, so the new individual rule rejects it without
altering its archived results. Contact-patch/anatomical review, continuous
collision, engine playback, human cleanup and the full release matrix remain
outstanding.

Replay verifies all 19 saved control vectors and 38 byte-exact exports, exact
original cap arrays, complete sampled geometry and all individual/aggregate
acceptance decisions. Independent scalar incident-facet accumulation checks
every saved contact normal, projection and error (19 samples) without the
production normal helper. Skin/pose samplers and geometry classifiers remain
shared. All 546 bound files rehash. See local `high-five/verification-v1/` under
the experiment directory. All 454 focused model-free regressions pass,
including 14 new protection cases; receipts remain local under
`reports/native-contact-guards-validation-v1/`. Public CI already selects this
test suite on Linux and Windows. No release gate or formal held-out protocol is
changed by these development results.
