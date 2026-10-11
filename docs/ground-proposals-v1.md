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
Both target-screen batches complete: all 30 transfers and screens finish without
exceptions, but **0/30 clips pass** the complete experimental floor condition.
Across 75,750 declared target times, **58,293 fail**. Each time checks all 1,029
triangle-referenced target vertices; no failed seed or frame is removed.

| Action | Condition | Mean peak penetration (mm) | Failed target times / total |
|---|---|---:|---:|
| Crawl | Baseline | 268.51 | 10,085 / 10,085 |
| Crawl | Root path | 262.87 | 10,085 / 10,085 |
| Crawl | Clearance and root path | 262.16 | 10,085 / 10,085 |
| Get-up | Baseline | 817.22 | 9,823 / 15,165 |
| Get-up | Root path | 741.08 | 10,243 / 15,165 |
| Get-up | Clearance and root path | 936.50 | 7,972 / 15,165 |

These are means of each clip's worst sampled depth, not mean penetration over
time. On paired seeds, adding root guides reduces mean peak depth by 5.64 mm for
crawl and 76.14 mm for get-up. Added clearance wording reduces crawl's mean peak
by only 0.72 mm and **increases get-up's by 195.42 mm**, despite fewer failing
get-up times. These mixed diagnostics do not establish an animation improvement.
No condition supplies an acceptable replacement.

Native-key source/target comparisons retain all 4,500 paired samples:

| Action | Both fail | Source only fails | Target only fails | Neither fails |
|---|---:|---:|---:|---:|
| Crawl | 1,800 | 0 | 0 | 0 |
| Get-up | 1,664 | 868 | 0 | 168 |

Source failure means the complete SOMA mesh crosses the declared floor at a
native key; it does not identify anatomical supports or establish the cause of
target failure. Source geometry between keys remains unmeasured in this study.

Only **1/20 guided clips** passes the existing provisional guide screen, whose
limits are 30 mm root-path error and 15 degrees heading error at three authored
frames. Maximum observed errors are:

| Action | Guided condition | Root error (mm) | Heading error (degrees) | Passing clips / 5 |
|---|---|---:|---:|---:|
| Crawl | Root path | 77.34 | 4.02 | 1 |
| Crawl | Clearance and root path | 72.10 | 3.59 | 0 |
| Get-up | Root path | 155.80 | 54.52 | 0 |
| Get-up | Clearance and root path | 92.33 | 38.59 | 0 |

The guide limits are development screening values, not calibrated release gates.
Guides are learned conditioning, not hard enforcement of the authored path.

The crawl screen completes in 301.203 seconds at 760,041,472-byte peak process-tree
RSS; all 313 resource observations replay. Get-up completes in 413.25 seconds at
766,418,944 bytes; all 423 observations replay. The local aggregate verifies the
frozen protocol, raw/transfer/report/geometry hashes, complete seed populations,
paired counts and original resource evidence. It does not independently recompute
motion or approve semantics, support, dynamics, engine import or human quality.
All release criteria remain unchanged.

A separate floor replay now checks **77,946,750 target vertex positions** at all
75,750 declared times with row-wise matrix products instead of the producer's
skin einsum. It reproduces every sampled depth and pass/fail classification,
and every target native-key minimum. All original target binary payloads remain
preserved. Shared GLB decoding and animation interpolation remain explicit;
this is separate skin/floor arithmetic, not independent source FK, clock
construction or complete motion-quality validation. The worker completes in
194.453 seconds at 175,366,144-byte peak RSS, and all 209 resource observations
replay. The original clips stay selected and all failed proposals stay retained.

The result closes this prompt/root-guide comparison with no promoted output.
Further work must test explicit whole-body/contact targets or a scene-conditioned
editor against these retained baselines. Repeating clearance wording or selecting
the least bad penetration peak is insufficient. Clean demonstrations and genuine
developer/animator review remain required before learned targets or release
approval; this study supplies neither.
