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

The fresh real high-five capture study is being evaluated separately under ignored `reports/high-five-imported-geometry-journal-v1`. It binds all 2,017 original times and initially requests a 512-frame prefix. Its result is pending; no complete full-clock audit, final scene/game package, original-reference fidelity or realistic interaction is claimed from the source tests.

The underlying [Trimesh ray API](https://trimesh.org/trimesh.ray.ray_triangle.html) documents undefined containment behavior for points on a surface. Existing near/boundary/coplanar outcomes remain separate, and this journal does not turn the floating-point vertex/surface checks into continuous collision or physical realism certification. All release gates remain unchanged and unapproved.
