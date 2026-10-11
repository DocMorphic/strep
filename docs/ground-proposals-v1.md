# Paired ground-motion proposals

The bounded [crawl repair](kenney-crawl-plane-envelope-v2.md) retained no changed
export. This separately frozen development study tests the existing proposal
stage on crawl and get-up, using the unchanged Kimodo checkpoint. It creates
new clips rather than presenting them as repairs preserving the old clip.
These two diagnostic actions do not define the system's prompt vocabulary.

The [protocol](../benchmarks/ground-proposals-v1.json) freezes three conditions
for both actions before inference:

| Condition | Text | Pose-derived guides |
|---|---|---|
| Baseline | Original action description | None |
| Root path | Original description | Original seed-77 XZ path/heading at start, midpoint and last frame |
| Clearance and root path | Original description plus explicit head/body-clearance wording | Same root guides |

Each condition uses seeds **77, 79, 83, 89 and 97**, producing **30 clips**.
Five seeds are represented as groups of four and one because the existing
request API accepts at most four per request. No seed is discarded. The two
comparisons isolate added sparse guides, then added wording with the guides held
fixed. Source NPZ hashes and chosen frames bind the guide references. They are
existing development outputs, not held-out release reservations or training data.

The same explicit `cuda-streamed` transport, model revision and inference settings
apply to every condition: 100 denoising steps, separated guidance `[2,2]`, one
sample, five transition frames and no postprocessing. The transport uses unchanged
float32 motion weights; its earlier [four-case equivalence study](motion-checkpoint-transport-v1.md)
does not prove every new guided output. Current text-loader provenance must match
before cached tensors are reused. Missing text is encoded locally with the
existing offloaded encoder; full resident-8B equivalence remains unverified.

Every proposal must retain its raw skeleton motion and generation/guide audit.
Target transfer uses the same Kenney static-rig derivative and reference profile
as the earlier seven-action development study. Target-floor screening keeps the
explicit Y=0 plane, 5-mm experimental tolerance and complete native/frame clock.
No vertical clip lift, changed rig geometry, motion cleanup or relaxed limit is
part of this proposal comparison. Complete geometry, source-versus-target
diagnostics, action semantics, contact support and engine/human review remain
separate; a root guide or clearance sentence is not scene-awareness evidence.

The first encoding attempt rejects a cache with different loader hashes before
creating new embeddings or motion. Its failed worker and all 55 resource
observations replay. A fresh encoding worker admits only exact current-method
caches and retains the previous failure. No qualifying current-method cache
contains these texts; all four descriptions encode locally. The encoding worker
completes in 181.625 seconds, peak process-tree RSS 2,908,667,904 bytes, and all
196 sampled resource observations replay. This checks encoding completion and
provenance rather than resident-8B equivalence or motion quality.
Raw study records remain local under
`reports/ground-proposals-v1` and guard/resource records under
`reports/central-hand-physical-v1`. There is no selected replacement or approved
release capability.

All 30 raw proposals now generate successfully: 15 four-second crawl clips and
15 six-second get-up clips, totaling 4,500 native poses. The worker completes in
250.969 seconds, peak process-tree RSS 1,590,583,296 bytes, and all 264 sampled
resource observations replay. Every raw NPZ and generation record is retained;
the 20 guided proposals also retain their constraint audit. Generation success
does not establish correct anatomy, contact, collision or action semantics.

Two sequential target-screen batches account for 15 proposals each. Each uses
the unchanged target, full target native/frame clock and experimental floor
limit. Source-versus-target floor diagnostics additionally compare every native
key using the full SOMA and target meshes; these source diagnostics do not cover
the source mesh between keys. No output is dropped after observing failure.
Complete target-screen results and independent motion verification remain pending.
