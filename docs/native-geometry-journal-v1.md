# Resumable complete-frame scene geometry

The native scene geometry audit can now checkpoint each fully evaluated clock sample and resume from a caller-pinned checkpoint. This addresses the stopped high-five study, where near-contact vertex-containment queries make a single uninterrupted full-clock pass expensive. It changes work persistence and object lifetime; it does not claim faster intersection predicates or reduce coverage.

`scripts/native_geometry_journal.py` supports native source skin or a separately sealed actual Godot capture. The latter verifies the successful raw-engine receipt, executable/input hashes, executed scripts, saved animation resources, selected actors, exact clock, complete imported skin functions and triangle population before evaluating geometry. Original executed methods and current Python measurement methods remain separately identified. Reconstructing a capture is CPU work; it does not run Godot or generate new motion.

Every committed frame preserves the complete loaded triangles, partner containment/crossings, object queries, plane tests, original tolerances, witness IDs and globally indexed numeric array names. All native keys, midpoint/frame phase populations and declared clock entries remain in the original full clock. A selected slice has an explicit partial schema and cannot set the full `sampled_conditions_pass` flag, even if its checked conditions pass.

The journal snapshots inputs and methods, then publishes immutable frame receipts and hash-linked checkpoints. A checkpoint names its previous checkpoint, exact request, frame artifacts and ordered prefix position. Resume verifies the caller-supplied checkpoint digest, entire ordered prefix, source/snapshot/method hashes, runtime versions (Python, NumPy, SciPy and Trimesh), full clock and all saved numeric transports. The latest `progress.json` is a convenience pointer, not an independent signature or substitute for a trusted expected digest.

If a process stops during a query, the partial attempt remains. Resume creates a fresh attempt for the uncommitted frame and reuses the committed prefix. Completed checkpoints and source bytes are never overwritten. Each frame releases unreachable Trimesh query/cache cycles before starting the next frame; admission and process-tree/free-RAM supervision remain necessary. This does not guarantee recovery from storage failure or uninterrupted hardware availability.

Finalization requires every original clock entry, in order. It streams the full JSON sample list and numeric archive one frame/array at a time. There is no passing full-clock result for an incomplete prefix. A completed full population can still contain failed conditions, which remain failed. Finalization preserves the existing complete geometry report schema and measurements; the separate journal result records its provenance and deliberately grants no engine-skin, contact, GPU, physics, human or release approval.

## Use from the repository root

Use the configured Python environment with the pinned CPU dependencies. Replace the input paths below with an existing source-bound native contact specification and geometry policy. Generated journals belong under ignored `reports/`.

```powershell
$receipt = python scripts/native_geometry_journal.py prepare contacts.json geometry-policy.json reports/scene-geometry-journal | ConvertFrom-Json
$receipt = python scripts/native_geometry_journal.py advance reports/scene-geometry-journal $receipt.checkpoint $receipt.sha256 --maximum-samples 16 | ConvertFrom-Json
```

Retain each returned checkpoint path and digest in the experiment record. Repeat `advance` using that receipt until `population_complete` is true, then finalize into a fresh output directory:

```powershell
python scripts/native_geometry_journal.py finalize reports/scene-geometry-journal $receipt.checkpoint $receipt.sha256 reports/scene-geometry-complete
```

For an existing actual capture, add `--engine-capture <capture-directory>` and `--capture-receipt-sha256 <recorded-raw-receipt-digest>` to `prepare`. The contacts and policy must be the exact captured inputs. A capture made with a different layout or clock cannot be silently substituted. Missing or mutated receipts/resources/scripts are rejected. A synthetic transport fixture is not evidence of an actual engine run.

## Verification and scope

All **124 targeted checks pass in 58.03 seconds**, covering the new journal plus existing scene geometry, imported skin/scene observations, numeric transport and convex partner queries. The 512 MiB CPU guard completes in **74.625 seconds**, peak sampled process-tree RSS **128,806,912 bytes**; all **75** resource observations replay. The initial 122-check run also passes before adding unsigned-index and full native-clock tests.

The new tests interrupt a query after publishing an earlier frame, verify that resume evaluates only the missing sample, retain both abandoned and fresh attempts, and assemble exactly the original full report and every numeric dtype/shape/byte. They exercise passing and failing partner geometry, object arrays with global frame indices, source changes during evaluation, tampering, missing populations and native frame-clock metadata. Capture tests use explicitly synthetic fixtures and do not claim a Godot integration result.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38687628648) passes all **33 new checks on each OS** at `7a4e8f2274b4cca593f31c2e096ebc19bd64c911`: Windows 22.89 seconds and Ubuntu 2.57 seconds. Broader source/export workflows remain separate.

The fresh real high-five capture study binds all **2,017** original times and completes its first predeclared **512-frame** prefix. All 512 committed artifact sets and the full prefix chain verify after evaluation. Its CPU-only 768 MiB guard completes in **348.750 seconds**, peak **654,839,808 bytes**, with all **343** resource observations replayed. This profile is motivated by the earlier raw-capture reconstruction measurement; it does not lower the unchanged engine/model admission estimate. No engine or model is run again. The prefix contains failed conditions and cannot pass the full clock. Remaining 1,505 times and full assembly are still pending at this checkpoint. Records remain local under ignored `reports/high-five-imported-geometry-journal-v1`.

A fresh process verifies that pinned 512-frame prefix and computes only the next **80** frames, reaching **592 of 2,017**. All 592 artifact sets reverify, and the prior checkpoint remains unchanged. The resume guard completes in **397.032 seconds**, peak **651,718,656 bytes**, with all **391** resource observations replayed under the same 768 MiB CPU cap and additional 600 MiB free floor. The complete saved sample at index 579 (1.1395833333333334 seconds) matches the earlier diagnostic exactly, including surface outcomes, containment counts/depths, witnesses and floor tests. This is a matched actual sample, not a full-clock numerical replay or performance comparison.

The next predeclared 128-frame continuation completes, reaching **720 of 2,017**. It reuses the prior 592 frames, verifies all 720 artifact sets and preserves the old checkpoint. Its 768 MiB CPU guard completes in **547.031 seconds**, peak **667,226,112 bytes**, with all **540** resource observations replayed. The following 256-frame batch reaches **976**, verifies the complete prefix and preserves the prior checkpoint: **743.109 seconds**, peak **652,992,512 bytes**, with all **730** resource observations replayed. At 976, 1,041 times remain. The 512-frame continuation under ignored `reports/high-five-imported-geometry-journal-batch5-v1` stops at its unchanged 1,200-second execution guard after 77 new committed frames, reaching **1,053 of 2,017**. It is not a RAM stop: peak 671,895,552 bytes, last available 4,282,601,472 bytes, total guard time 1,216.172 seconds; all 1,197 resource observations replay. A fresh guarded process verifies every committed artifact in the pinned 1,053-frame chain before further work. The incomplete frame attempt remains preserved. The next 32-frame continuation completes and verifies every committed artifact through **1,085 of 2,017**, preserving the prior checkpoint. Its unchanged 768 MiB CPU guard completes in **558.657 seconds**, peak **664,199,168 bytes**; all **552** resource observations replay. At verified 1,085, 932 original times remain. The next 48-frame batch completes and re-verifies **1,133 of 2,017** artifacts, preserving the prior checkpoint: **871.250 seconds**, peak **649,302,016 bytes**, with all **855** resource observations replayed. At verified 1,133, 884 original times remain. That next 48-frame continuation completes and re-verifies **1,181 of 2,017** committed artifacts, preserving the prior checkpoint: **371.328 seconds**, peak **714,907,648 bytes**, with all **366** resource observations replayed. At verified 1,181, 836 original times remain. The 128-frame batch completes and re-verifies **1,309** artifacts in **207.360 seconds**, peak **666,054,656 bytes**, with all **205** resource observations replayed. The final 708-frame work budget then completes and verifies every artifact through **2,017 of 2,017**: **457.359 seconds**, peak **659,910,656 bytes**, with all **449** observations replayed. Both use the unchanged 768 MiB CPU cap, 600 MiB free floor, 1,200-second execution guard and original predicates. Every prior checkpoint and abandoned attempt remains preserved. Records remain under ignored `reports/high-five-imported-geometry-journal-batch9-v1` and `-batch10-v1`. The complete population contains failed conditions; completeness is not a pass. Earlier resume records remain under `reports/high-five-imported-geometry-journal-resume-v1`, `reports/high-five-imported-geometry-journal-next-v1` and `reports/high-five-imported-geometry-journal-batch4-v1`.

The [captured audit completion bridge](native-scene-engine-completion-v1.md) rejects incomplete populations. The real high-five population is now complete and has passed through that bridge, strict saved-observation replay, original-reference fidelity and explicit reference root/intent exports. These completed checks retain the original failed scene conditions; no full playable game package or realistic interaction is claimed.

The installed Trimesh 5.1.0 fallback ray test can draw from its shared [random generator](https://trimesh.org/trimesh.util.html#trimesh.util.random_generator), whose default initialization uses OS entropy. V1 preserves and verifies committed measurements; it does **not** checkpoint that fallback generator's state. Fixture equality and exact saved-array verification therefore do not establish fresh numerical rerun equality for ambiguous fallback cases across processes. Explicit evaluator seed/state binding remains necessary before making that stronger reproducibility claim.

The underlying [Trimesh ray API](https://trimesh.org/trimesh.ray.ray_triangle.html) documents undefined containment behavior for points on a surface. Existing near/boundary/coplanar outcomes remain separate, and this journal does not turn the floating-point vertex/surface checks into continuous collision or physical realism certification. All release gates remain unchanged and unapproved.


## Complete actual imported assembly

The full pinned 2,017-frame sequence is assembled without new geometry queries
in **159.062 seconds**, into a 19,792,094-byte geometry JSON and a 4,591-byte
numeric archive. This actor-only scene has no object-depth arrays; the archive
binds the complete clock, while partner outcomes and world-plane measurements
remain in the geometry JSON and their executed pose/skin sources remain in the
sealed capture. The final result is complete with `sampled_conditions_pass=false`;
its digest is `68949c940021af83d6a690c0d0ec0112d385b5e406217aeaab81bba0521dc842`.
All original methods, inputs, tolerances and time populations remain bound.

Local final artifacts remain under ignored
`reports/high-five-imported-geometry-complete-v1`. The combined finalization/test
job later fails a new test fixture assumption; the assembly itself succeeds and
is preserved independently. Its corrected test run does not repeat assembly.
See [reference-control validation](native-pose-reference-v1.md) for the complete
status and resource accounting. The actual [capture-completion bridge](native-scene-engine-completion-v1.md),
strict saved-observation replay, original-reference fidelity and explicit reference
root/intent exports now complete. Human quality and full game packaging remain
separate; no corrected motion or release approval follows from assembly.

Across the original declared clock, the pair fails at **402 of 2,017 times**.
There are **129,274 recorded surface outcomes**: 129,268 proper crossings and
six boundary/near-contact records. Maximum recorded inside-vertex depths are
**21.552571 mm** for A inside B at 1.8166666666666667 s (vertex 12652), and
**33.499061 mm** for B inside A at 1.2479166666666666 s (vertex 2977).
Neither actor has an unavailable containment result. Both fail the original
5-mm ground tolerance at every sampled time: maximum penetration **10.436220 mm**
for A at 0.8208333333333333 s, and **8.331528 mm** for B at
0.8583333333333333 s. Thus the complete scene fails at every declared time.
These are counts on a nonuniform clock, not duration percentages. Recorded
vertex depths are not exact triangle penetration, continuous collision or
physical/human quality certification. The summary is independently bound under
ignored `reports/high-five-captured-engine-replay-v1/geometry-summary.json`.

## Pinned partner query working set

Journal preparation now accepts `partner_query_batch_size` and the CLI flag
`--partner-query-batch-size`, bounded to integer values 1–32. The default
remains 32. The request records this setting, every resumed frame passes it
to the existing geometry evaluator, and the final journal receipt reports it.
Changing the setting invalidates the caller-pinned checkpoint/request binding.

```powershell
$receipt = python scripts/native_geometry_journal.py prepare contacts.json geometry-policy.json reports/scene-geometry-journal --partner-query-batch-size 1 | ConvertFrom-Json
```

This controls how many partner point queries are processed together. It does
not reduce the original clock, mesh/vertex population, query predicates or
physical tolerances. A smaller batch is not a memory guarantee: continue using
resource admission and supervision. Method hashes still bind the journal to
its recorded implementation; preserve older journals and use their recorded
revision rather than silently upgrading an unfinished checkpoint.

The affected local selection passes 114 tests in 42.42 s, including 13 new
cases. Batches 1, 2 and 32 produce the complete resumed reports and arrays of
their corresponding direct fixture queries. Invalid settings reject before
opening a scene or creating output. A changed valid setting cannot resume a
pinned prefix, and invalid context settings reject before loading assets.
The existing interrupted-prefix, full-clock, source mutation and synthetic
capture checks also pass. The 512-MiB test guard completes in 71.953 s at
124,198,912 peak sampled bytes; all 73 observations and archived bindings
replay. Fixture agreement does not remove the fallback RNG and boundary
limitations above or establish actual engine, human or release acceptance.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/39003789224)
at source `515d746` passes the journal suite on Ubuntu and Windows.

## Assembly-v4 prefix: real failures retained

`high-five-subkey-full-geometry-journal-v1` is a fresh study of the later
assembly-v4 candidate, separate from the older captured-engine candidate
above. It retains the full 2,017-time clock and uses pinned batches of one.
Initial 64- and 320-frame prefixes pass; their guards complete in 46.765 s /
150,093,824 sampled bytes / 48 observations and 118.687 s / 155,508,736 bytes /
119 observations, respectively. All recorded bindings and resource traces replay.

The next continuation commits through frame 610: 611 samples, 25 failed.
The first failure is index 586 at 1.1541666666666666 s. After confirming real
crossings, this continuation is intentionally stopped, retaining the committed
checkpoint, failure frames, source/method bindings and next abandoned attempt.
Its guard is accounted as intentionally failed: 700.984 s / 220,811,264 bytes /
692 observations, not a memory failure or completed full-clock sweep.

The pinned prefix ends at
`checkpoints/000611-24a59fac1c954accb05e04676c36490a.json`, SHA-256
`6da03974e5ecbf1725c2aac0d75c8307f9aa6e37dae36def09487006ad0a6a44`.
Independent diagnosis verifies its chain and all 85 exact rational crossing
witnesses for the first failed frame's represented Float64 triangles. These
failures do not depend on the containment fallback RNG. This prefix is neither
a full-population pass nor evidence of continuous, anatomical or human quality.
See the [region constraint study](native-affine-region-pose-v1.md) for scope.
