# Measured Godot weight precision experiment

The [imported-skin audit](imported-scene-measurements-v1.md) found whole-skin
displacement above the existing 0.1 mm precision screen in four actor instances.
An opt-in derivative export now addresses the measured quantization loss while
preserving original character files, motion, contacts, scene placement and
acceptance tolerances. This is an export experiment, not model training or a
change to the default Studio export.

## Method and retained failures

The pinned Godot 4.7.2 import normalizes weights with a sequential float32 sum,
then packs each influence into unsigned 16 bits. Independent truncation can
lose total weight. Renormalizing observed engine weights would hide the actual
skin function, so all measurements continue to use the raw imported values.

`scripts/godot_weight_derivative.py` normalizes the original weights for a
largest-remainder allocation whose integers sum to 65535. It encodes those
integers as float32 and orders joint-weight **pairs** together. Starting from
stable ascending order, it selects the first cyclic order for which the pinned
import simulation preserves every allocated integer. An unsupported row
rejects the derivative; it does not relax the condition or discard influences.

The original-slot rounding preflight reduced average mass loss but worsened
the maximum, and was retained as a failed candidate. Ascending order alone
looked promising on the character, but a random eight-influence test exposed
a sequential-sum edge case with mass loss about `0.00012206845`. The checked
cyclic fallback fixes that tested case. These are coefficient simulations;
only subsequent actual imports support engine measurements.

The derivative changes only paired influence payloads. It independently checks
unrelated payload bytes and document values, detects incompatible shared or
aliased accessors, and saves a source/output/method-bound receipt. V1 supports
four/eight influences with original float32 weight accessors and plain unsigned
joint accessors. Accessors with influence extrema, unsupported layouts or
overlapping unrelated data reject explicitly. Original files remain intact;
third-party asset terms still apply. No character payload is published.

## Reproduction

```powershell
python scripts/godot_weight_derivative.py original.glb derivative.glb --source-sha256 EXACT_ORIGINAL_SHA256
```

Use fresh output and receipt paths. The adjacent `.weights.json` records the
changed coefficients and leaves fidelity, quality and release approval false.
Create a separate source-bound scene bundle pointing to the derivative while
preserving original motion, targets, timing, objects and placements. Reimport
with `scripts/run_scene_playback.py --measure-skin` at the original rate.

`scripts/weight_derivative_fidelity.py` accepts a pair manifest with schema
`strep-weight-roundtrip-pairs-v1`. Each pair names `original_producer`,
`original_id`, `derivative_producer`, `derivative_id` and an `actor_receipts`
mapping from every actor name to its derivative receipt. Both producers must
be terminal, unchanged imported-skin audits. The comparison rejects changed
clocks, actor populations, source motion, contacts or scene geometry; it also
checks the complete derivative encoding and every non-influence accessor.

```powershell
python scripts/weight_derivative_fidelity.py reports/my-pairs.json reports/my-original-fidelity
```

The reference remains the **original GLB's normalized skin**, sampled from its
unchanged animation. The measured side uses actual imported derivative poses,
binds and raw weights with placement after skinning. Every original sample and
every surface vertex is checked; comparing the derivative against itself is
not accepted. Per-sample maximum distances and source-vertex witnesses are
saved with input bindings and implementation snapshots.

## Actual engine results

Four unchanged development motions were reimported as five derivative actor
instances. The original clocks retain 2585 actor poses and 1407 object poses,
with all 18,056 vertices and eight influences per actor. All pose, imported-skin
function and complete triangle-correspondence checks pass. Five derivative
GLBs have zero validator errors and warnings.

| Actor instance | Original import maximum skin error | Derivative import versus original skin |
|---|---:|---:|
| Corrected reference, seed 7103 | 130.876 micrometres | 1.320 micrometres |
| Corrected reference, seed 7104 | 125.785 micrometres | 1.117 micrometres |
| Original lift, seed 11 | 95.163 micrometres | 2.655 micrometres |
| Original high-five A, seed 11 | 138.701 micrometres | 1.400 micrometres |
| Original high-five B, seed 11 | 138.701 micrometres | 1.400 micrometres |

All five instances pass the unchanged 100-micrometre screen, with zero samples
over its limit. These results cover these motions, rig and pinned importer;
they do not guarantee every character or pose.

Both corrected references retain their strict 1 mm contacts at
0.986473/0.937494 mm and have zero sampled floor and box-vertex depth. The
longer lift still misses both grips by 549.478/497.664 mm; the high-five still
misses hand-to-hand contact by 533.734 mm. Their floor failures remain
8.996512/6.233599 mm. Precision improvement is not interaction correction.
Fresh complete geometry audits of both derivative references also pass all 261
samples each: bounded triangle/box depth and floor depth are zero, and the box
center remains outside the actor volume. Both complete numeric archive receipts
verify. This audit takes 130.047 seconds with peak process-tree RSS 469,168,128
bytes and does not trigger the unchanged resource guards.
The original full-surface high-five overlap remains a retained failure;
derivative partner surfaces need a fresh audit when that motion is repaired.

The focused model-free suite passes 71 tests, including raw association,
eight-influence sum loss, checked fallback, aliased/corrupted data rejection,
original-reference preservation, unchanged precision rejection and missing
vertex rejection. Failed intermediate test receipts remain local. CI declares
399 Python modules in four shards (100/100/100/99) and 37 Node scripts per OS;
hosted status is separate from these local results.

## Remaining scope

Promote this opt-in encoding into reviewed export paths only with source-bound
provenance, independent original-skin comparison and appropriate scene checks.
Complete the longer constrained lift and repair the coupled high-five motion.
GPU rendering, self-collision, continuous collision, dynamics, naturalness,
held-out rig/action coverage and independent cleanup-time evidence remain
unapproved. All fourteen release capabilities and the whole-project goal
remain unfinished.
