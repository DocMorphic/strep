# Decoder-aligned support search and serialized repair

The support optimizer's batch model now matches the existing scalar decoder's
endpoint comparisons. The [preceding joint-search study](studio-joint-support-v1.md)
exposed a difference at its final 120 Hz sample. This fixes a demonstrated
numerical modeling error; it does not change the Kimodo checkpoint or approve
animation quality.

## Clock behavior and preservation

The native last key is the float32 time 3.9666666984558105 s. The audit also
contains the earlier uniform sample 3.966666666666667 s. In the pinned NumPy
2.2.6 environment, the scalar decoder's comparison treats that sample as the
endpoint and clamps it. The previous float64 batch comparison interpolated
instead. A similar mismatch can occur just after a non-binary first key.

`SupportRateProblem` precomputes the same scalar endpoint masks for each edited
rotation channel and uses its first/last quaternion where the decoder clamps.
Exact native-key handling and the existing SLERP path remain in place. These
masks also apply to the inherited swivel/orientation and warm repair models.
Unchanged nodes, free phases and frozen boundary poses retain their existing
preservation rules.

The scalar decoder, authored key times, rotation exporter, parameter boxes,
support specification, source-relative rate caps and final independent audits
are unchanged. This deliberately follows the installed decoder's arithmetic;
it does not substitute a new clock or hide a discrepancy by widening tolerance.
Historical method archives and the earlier failed replay diagnostic remain
intact. An optimizer proxy is still distinct from an exported asset audit.

Three new synthetic tests expose the error before the fix in bend, swivel and
orientation modes. They use non-binary endpoints, explicit near-boundary probes
and changed interior rotations, then independently export/decode the GLB. The
fixed path agrees within the existing 2e-14 matrix diagnostic tolerance and
preserves source clocks, unchanged branches and the 1e-5 rate tolerance.

## Development replay and warm repair

The study first replays all eight source-bound controls from the preceding
wave/kick requests. It verifies the old completed study, outputs, archived
methods, control boxes, native clocks and exact GLB hashes before evaluating
the new model. It compares rounded batch matrices and rate diagnostics against
the actual independent decoder at all 701 audit times per proposal, including
the terminal sample. Existing failure counts must reproduce exactly.

It then warm-starts the existing serialized feasibility repair from the four
wave proposals with **eight iterations per trial**, a **0.0002-radian trust box**
and quantized finite differences. This uses the same source, Y=0 plane,
numerical left-foot stance, authored displacement/angular limits, variable
boxes and final serialized gates. The least-squares method is not rerun and
its iteration budget is not increased. The separate stricter absolute-peak
guard remains a recorded diagnostic; this pilot uses the preceding job's
unchanged bin-based selection gates.

Every repair probe is exported and independently decoded before it can replace
its warm controls. Linear programs propose local directions, not certificates
of nonlinear feasibility. The method retains rejected probes and line-search
history. The final job can retain its source even after numerical improvement.
Its chosen result is independently converted to native SOMA77 geometry and
audited again after preview serialization. Root/boundary preservation and the
cumulative original-relative edit budget remain required. Unknown contact
labels stay unknown; no human review or rights claim is supplied automatically.

## Terminal results and limits

All eight historical wave/kick controls reproduce their proposal GLBs
byte-for-byte. At all 701 audit times, the rounded-key batch model and actual
decoder agree within 1.221e-15 matrix elements, including the previously
mismatched terminal sample. The actual recorded rate-failure counts remain
unchanged. Maximum rate-diagnostic differences are at most
8.191e-14 m/s, 1.784e-11 m/s², 2.665e-14 rad/s and 5.4e-12 rad/s².
These are numerical modeling checks, not motion-quality improvements.

The four wave warm repairs are terminal. Failed groups are position speed,
position acceleration, angular speed and angular acceleration. Worst merit
is the largest positive normalized serialized constraint excess; a decrease
does not establish acceptance and can increase other errors.

| Proposal | Before failed rows | After failed rows | Initial worst excess | Final worst excess |
| --- | --- | --- | --- | --- |
| 1 | 9 / 4 / 1 / 3 | 8 / 4 / 1 / 2 | 0.0046367564 | 0.0037908641 |
| 2 | 4 / 2 / 2 / 3 | 1 / 0 / 0 / 0 | 6.6854157e-05 | 3.2337731e-05 |
| 3 | 23 / 4 / 4 / 4 | 23 / 4 / 4 / 4 | 0.0070133847 | 0.0070133847 |
| 4 | 14 / 4 / 0 / 8 | 14 / 4 / 0 / 8 | 0.0020525048 | 0.0020473495 |

All four proposals still pass the sampled support-height screens and fail
at least one motion-rate row. **Zero repaired motions are accepted.** Both
the fitter and native conversion retain the exact input; its independent
selected-preview support screen still fails. Native roots/boundary poses remain
unchanged and no contact labels are inherited. No source-rate cap or authoring
limit is relaxed. Trial 3 makes no accepted repair step. Trials 1 and 4 lower
their worst excess but increase their final summed squared excess, so neither
a lower worst value nor a smaller failure count is a general improvement claim.

The closest proposal, trial 2, falls from eleven failed rate rows to one.
Its `LeftFoot` positional speed over [3.958333333, 3.966666667] s is
0.018117406058 m/s against a 0.018105789172 m/s source-bin cap
plus the unchanged 1e-5 tolerance. The remaining excess is
**1.61688653e-06 m/s**. It is a failure under this protocol,
regardless of its small magnitude. The conservative dependency graph identifies
5 candidate columns; it does not prove that each changes the foot origin.
A bounded coordinate screen of those controls with separate export/decoder
acceptance is the next experiment, rather than an unexplained budget increase.

Godot 4.7.2 imports all four repaired proposals and the selected native input:
5 clips/600 native frames, 77 bones, one skinned surface each and
non-looping playback. Native-time joint samples match within
5.437e-07 metres and 9.795e-07 basis elements. This is
engine import and CPU pose fidelity, not browser appearance, GPU deformation,
continuous collision or animation-quality evidence.

Source, parent output/archive/control and current method bindings remain intact
at completion. All 1,661 model-free Python tests and 15 JavaScript suites pass.
The focused five-module geometry/repair selection passes 90 tests. The new
endpoint cases first fail against the old batch behavior, then pass with the
fix. The preceding public commit `4c027b9` passes its hosted workflow
`37038656736`.

Local retained evidence:

- `reports/native-support-clock-repair-v1/result.json`: replay, matched repair,
  native conversion, method/source bindings and five-clip Godot results.
- `reports/native-support-fit-native-joint-wave-repair-v1`: all four repaired
  outputs, numerical controls, serialized probes and accepted/rejected history.
- `reports/native-wave-repair-remaining-v1/result.json`: exact remaining row
  and conservative control dependency columns.
- `reports/native-support-clock-repair-validation-v1/verification.json`:
  completed check and current source/evidence receipt.

These are historical development motions with numerical forearm/root edits,
not reviewed stance labels, fresh generations or the untouched release
population. No model update, human submission, cleanup-time result or release
approval is supplied. This work cannot establish horizontal planting,
whole-sole contact, balance, forces, collision clearance, action correctness,
interaction quality or human cleanup time. Scene/partner/finger contacts,
broader rig/action behavior, real licensed reviewed data, learned improvement
and full release validation remain unfinished. All 14 capabilities stay
unapproved, the formal 72-by-five population stays untouched and the single
full-project goal remains active.
