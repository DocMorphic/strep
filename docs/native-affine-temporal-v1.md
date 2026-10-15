# Coupled native-key correction on supplied affine rigs

The crawl's [passing serialized touch](native-key-contact-reserve-v1.md) still leaves eight failed floor times and 377 original motion-rate violations. The temporal model previously replaced edited local linear blocks with pure rotations and measured angular motion directly from affine joint matrices. It could therefore discard source scale or reject the same supplied rig that the pose initializer supports. The model now preserves sampled scale in its explicit native TRS path and uses the original request's declared angular metric.

## Transform and measurement contract

Legacy rigid/strict defaults remain unchanged. With `pose_representation: native-trs-v1`, every edited quaternion is sampled at the complete native/geometry/contact/rate clock and multiplied by the original sampled scale in glTF T·R·S order. Static and animated positive scale are retained. Source translations, untouched local transforms, original rig nodes, inverse binds and influences remain unchanged. Export uses the same existing-key quaternion writer.

Decoded local edit angles remove only the known original scale; the resulting matrices must be proper rotations within the stated numerical check before conversion to rotation vectors. A changed scale cannot pass as an authorized rotation edit. The optional `right-polar-v1` metric measures world orientation separately from stretch, without normalizing geometry. All four rate cap arrays are rebuilt from the original source, with the existing 120-Hz clock, four bins and `1e-5` tolerance. They are never recalibrated from the corrected seed.

Active keys still form a complete contiguous interval of at most 768 scalar controls. The model now respects the original explicit boundary contract: an authorized clip-start edit may participate, while preserved endpoints, frozen keys and keys outside the edit window remain fixed. All seed controls at protected times must be zero relative to the original source, including inactive protected keys.

## Loading corrected keys without repeating pose solves

`KeyIntervalModel.from_inputs` is a Python entry point for a fresh source-bound temporal seed:

```python
from native_key_interval_model import KeyIntervalModel
from strep import sha256

paths = dict(contacts=contacts_path, geometry=geometry_path,
             request=original_authoring_path, controls=key_controls_npz)
problem = KeyIntervalModel.from_inputs(
    **paths, active_keys=[11, 12, 13], output=fresh_seed_folder,
    expected_sha256={name: sha256(path) for name, path in paths.items()})
```

The four input digests must match exactly. The NPZ must contain only the original `times_s` and complete bounded finite numeric `controls`, with an identical native clock. Boolean controls, nonzero protected keys and over-limit rotation vectors reject. Accepted numeric controls are converted to Float64 before edits, so an integer zero seed cannot truncate subsequent fractional proposals. The fresh output cannot contain original inputs or asset dependencies. The constructor exports the seed from the original rig and original animation, checks actual decoded channels and matrices against the batch preview, and binds the seed bytes and derived contact file. It writes a source/method receipt with approval flags false. Original source assets and controls remain bound during later checks.

This authoring path accepts an explicit bounded proposal; it does not inherit an old initializer's approval or bypass that initializer's method binding. The existing initializer-result constructor remains available with its original strict lineage checks. No new public command or Studio selector is claimed. Complete decoded checks are required before a temporal proposal can be retained.

## Complete floor guidance with bounded temporary memory

The previous floor method accumulated and concatenated the entire skinned timeline. The new method evaluates at most 32 geometry times at once, checks every triangle-referenced vertex against every declared plane, and retains each exact minimum and witness. Plane-major row order and every original time remain intact. It does not decimate geometry or replace the separate complete decoded geometry check. This bounds the temporary skin gather rather than the total solver size.

The original coupled affine system still protects every rate and floor condition separately against worsening. Passing rows retain their original limits, failed rows cannot worsen, and the original limits remain in the optimization objective. Every returned candidate must also pass decoded edit/contact/root checks and complete geometry retention. Fewer failed rows alone cannot justify selection.

## Validation and development trial

All **33 selected checks pass in 169.49 seconds**, including original interval/restoration behavior and new static/animated affine scale, native export agreement, all-plane streamed minima/witnesses, invalid digest/clock/frozen/norm/Boolean seeds, explicit start edits, changed-scale rejection and source-cap mutation rejection. The guard completes in 185.953 seconds with peak sampled process-tree RSS 132,120,576 bytes; all 184 observations replay. Inventories validate at 508 Python/45 Node files and 72 Python/5 Node files in the focused suite. This is inventory validation, not execution of every listed test.

The real development trial reconstructs the rejected crawl seed from original source files and already-saved controls, then verifies exact seed GLB bytes and original cap arrays. A three-key interval is selected around the largest saved normalized rate violation, using all sixteen originally permitted rotation tracks. One bounded affine step uses trust `0.01`, difference step `0.001`, up to six decoded backoffs, all original condition rows, and the existing rowwise retention rule. No other pose solve is repeated. The fixed CPU resource profile keeps the 512 MiB runtime cap, additional 600 MiB free-RAM floor and 15-second admission stability.

The actual interval is **keys 11–13**, all sixteen permitted tracks and **144 scalar controls**. The reconstructed seed is byte-identical to the prior margin-corrected export; all four original cap arrays match exactly. Complete decoded baseline checks reproduce 377 rate failures and eight floor failures, with contact/edit/root conditions passing.

The affine system retains **482,068 norm rows**, including a **355,609-row protected prefix**, all 123,630 original rate rows and 2,829 complete floor rows. Its sparse Jacobian has 238,334 nonzeros. The solver handles 2,191 active cones; fixed and conservatively affine-box-passing conditions are accounted for separately, while every decoded condition remains in the audit and retention population. The primary solve reports `Solved` after 21 iterations. Its optional smaller-norm phase is rejected after a separate affine hard-row check; the primary direction remains the proposal.

| Returned clip | Rate failures | Floor failures | Contact/edit/root checks | Maximum normalized violation | Retained? |
| --- | ---: | ---: | --- | ---: | --- |
| Start | 377 | 8 | Pass | 378.400225 | Initial proposal |
| Full step | 379 | 8 | Fail | 366.861002 | No |
| Half step | 377 | 8 | Pass | 372.604304 | Research proposal only |

The full step is rejected despite a lower worst violation. Its touch error is 5.000000431 mm, outside the original 5-mm tolerance; no precision waiver is applied. The half step preserves every individual rate/floor/geometry condition against worsening and passes the complete decoded prefix, while reducing maximum normalized violation and squared positive violation (848,567.472 to 822,539.025). Its touch error is 4.736161 mm and peak floor depth improves from 5.399995 to 5.364233 mm. It repairs no failed rate or floor row yet. The clip stays **rejected** and the original remains selected. These normalized numerical scores do not measure naturalness or animator acceptance.

The trial completes in 302.078 seconds, peak sampled process-tree RSS 498,688,000 bytes, within the unchanged 512 MiB cap; all 292 resource observations replay. Its retained research GLB SHA-256 is `da87ac034ce4e7470ccd636c89040884ce1f5f4f41e5cbb88c4074368bf07432`. All returned clips and failures are retained. A separate fresh replay reproduces exact bytes and complete observation arrays for all three clips, complete contact/geometry reports, and both rejection/retention decisions. It takes 247.672 seconds, peak sampled RSS 507,142,144 bytes, with all 244 resource observations replayed. It reruns no optimizer or finite-difference Jacobian and shares the curve/reader/skin/audit methods; it is not an independent physics implementation.

The numeric seed-type conversion is added after the production trial and its replay; the archived implementations stay intact. All three supplemental integer/Float32/Float64 cases pass in 14.74 seconds, checking fractional controls and actual export agreement. Their guard completes in 31.609 seconds with all 33 resource observations replayed. A passive original-input check verifies that the real trial seed is already Float64 and conversion changes none of its values. No production optimization is repeated for this input-type correction.

Local evidence is retained under ignored `reports/native-affine-interval-validation-v1`, `reports/native-affine-interval-validation-v2`, `reports/crawl-affine-temporal-v1` and `reports/crawl-affine-temporal-replay-v1`. This does not add generation, training, held-out, engine, independent animator or cleanup evidence. Next work is further coupled correction and broader scene/partner/style/rig/engine/release validation. All fourteen capability/calibration gates remain unapproved and the entire-project goal remains active.
