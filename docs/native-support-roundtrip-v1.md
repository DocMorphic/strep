# Repair across editable native serialization

An opt-in warm repair now evaluates both stored GLB quaternions and their
editable float32-matrix preview representation. The previous development
proposal passed before conversion but failed three actual preview rate rows;
this mode addresses that demonstrated representation boundary. The actual
NPZ export and native preview conversion still run independent final audits.

## Method and calibration

`native_support_roundtrip.py` keeps the existing bend, knee-plane and foot
orientation controls and authored bounds. Changed stored quaternion keys
pass through float32 rotation matrices, quaternion reconstruction and preview
continuity signs. Unchanged source keys keep their source representation in
the calibrated population. Both raw and preview signed constraint vectors
cover sampled support height, edit bounds and source-relative motion rates.
Coordinate screening or finite differences use these two populations; each
accepted numerical probe exports and independently decodes both GLBs.
Selection additionally requires the preview population to pass. No clock,
source-bin cap, 1e-5 rate tolerance or original authoring budget is relaxed.
These four-bin source-relative limits are not independent animation-quality
benchmarks. The separate full-clip absolute-peak diagnostic is recorded;
strict peak enforcement is not enabled in this study.

A source-bound calibration against the previous failed actual native preview
reproduces all three edited nodes' float32 quaternion keys exactly and keeps
all unedited key tracks exact. Across 701 audit times,
maximum world-component difference is 1.11e-15
and signed-constraint difference is 1.127e-11.
It reproduces the same three failing rows. This is one known source's
calibration, not proof of equivalence for every rig or possible edit.

The experimental command requires a completed source-matched orientation
study, its archived controls, a bound draft and a fresh output directory:

```powershell
.venv\Scripts\python.exe scripts/native_support_job.py source.glb draft.json fresh-fit --joint-rates --joint-swivel --joint-foot-orientation --repair-from completed-fit --repair-coordinates --repair-native-roundtrip --repair-iterations 4 --repair-trust 0.0000002
```

This is an offline warm-repair option; Studio's existing initial search is
unchanged. It is not a new motion-generation or learned-model update.

## Matched development result

Four historical wave warm starts use four maximum coordinate iterations and
initial 2e-7-radian trust, within their unchanged original boxes. The study
completes 21,436 numerical screens and 23 independently decoded
raw/preview probe pairs. Failed raw rate rows are grouped as positional
speed/acceleration and angular speed/acceleration:

| Proposal | Before failed rows | After failed rows | Initial combined worst excess | Final combined worst excess |
| --- | --- | --- | --- | --- |
| 1 | 8 / 4 / 1 / 2 | 8 / 3 / 1 / 2 | 0.0037830542 | 0.0037828987 |
| 2 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 2.18161739e-06 | 0 |
| 3 | 23 / 4 / 5 / 4 | 23 / 4 / 5 / 4 | 0.00688001379 | 0.00687598565 |
| 4 | 14 / 4 / 0 / 8 | 14 / 4 / 0 / 8 | 0.00203675181 | 0.00203336131 |

1 of four fitter proposals pass the final gates. Actual native
conversion accepts the selected correction.
Root translations and first/last local poses remain exact, and missing
foot-contact labels remain unknown. Authored support markers bind the actual
selected preview; passing numerical support is separate from human labels.
The selected raw proposal's stricter absolute-peak diagnostic is
False;
passing the configured bin limits does not imply passing that diagnostic.
The two-population squared merit is not directly comparable to older
single-population objectives. Reduced maximum excess alone does not establish
improvement; every failure remains recorded.

The selected native fixed lower-foot patch has 14
vertices in a 1195-vertex region. On the authored
1.6–2.4 s stance, maximum tangential drift changes from
4.879932 to
4.879948 mm; maximum
tangential speed changes from
28.614383 to
28.618025 mm/s.
Sampled penetration is 0.000000
mm. This patch is a fixed geometric diagnostic, not an inferred whole sole
or reviewed contact. Passing height/rate screens does not establish planted
feet, continuous collision, balance, dynamics or realistic motion.

Godot imports 5 clips/600
native frames with 77 bones, one skinned surface and non-looping playback.
Maximum joint position difference is 5.437e-07
m and maximum basis-element difference is 9.795e-07.
These are headless CPU import/pose checks, without browser/GPU appearance or
animation-quality approval.

## Validation and remaining work

Ten new analytical/fixture cases check stored-matrix reconstruction, malformed
keys, two separately decoded populations, doubled constraint sparsity, strict
warm-mode validation, preserved bounds, immutable parents and archived probe
hashes. The focused selection passes 53 tests. The full geometry/Studio
selection passes 1,682 Python tests and all 16 JavaScript suites. Hosted
workflow 37049551756 for preceding commit b011dec passes; new hosted results
are reported after publication.

Terminal raw evidence stays local in `reports/native-roundtrip-canary-v1`,
`reports/native-support-fit-native-roundtrip-v1` and
`reports/native-support-roundtrip-calibration-v1`. A local
`reports/native-roundtrip-validation-v1/verification.json` binds this source
and the archived results. Tokens, model weights, character payloads and
generated assets are excluded from the public repository.

This is one previously edited development motion with numerical stance
times. There is no fresh generation, real training update, licensed reviewed
target admission, human cleanup submission or formal held-out evaluation.
All 14 release capabilities remain unapproved and the formal 72-by-five
population remains untouched. The single full-project goal stays active.
Next work still includes geometric foot planting, broader actions/styles,
object/partner/finger contacts, rigs, reviewed licensed corrections, measured
learning and human release evaluation.
