# KayKit auxiliary-root isolation study

The extra skin root does not explain the deepest floor penetration in the
seven existing generated transfers. A controlled probe that makes this root
follow the pelvis, while compensating children to retain all other node world
transforms, leaves every clip's maximum sampled floor depth unchanged. This
probe is not adopted as a correction.

## Method and scope

`scripts/auxiliary_root_diagnostic.py` accepts a validated `RigAsset`, animation
sampler, explicit ancestor root and descendant anchor, and a finite increasing
clock spanning both clip endpoints. The study uses the current
`NativeSupportSampler`, all distinct stored key times and their midpoints.
These are sampled observations, not continuous collision bounds.

For each sample, let `A` be the pelvis world transform, `A0` its default-node
reference, and `R0` the root reference. The isolated root probe is
`R' = A inverse(A0) R0`. Every other node world transform stays fixed. Local
transforms are reconstructed and composed to verify the compensated hierarchy.
This differs deliberately from moving a parent and allowing its descendants
to move with it. It does not establish a valid animation export or acceptable
local joint motion.

The independent skin displacement identity uses the original raw weights and
inverse binds: `delta p = (R' - R) sum(w I p_h)` for influences belonging to the
selected root. No weights are normalized or rounded to zero. Vertices with
exactly zero root weight cannot move under any change restricted to this root's
skin contribution with all other world transforms fixed. Their floor depths
therefore supply a conditional lower bound for that restricted edit class.
This does not rule out changes to other joints or general rig retargeting.

The original KayKit asset has 4,858 vertices. Exactly 467 have positive root
weight, with maximum 0.1655004322528839; 4,391 are unaffected by this probe.
The original authored `Lie_StandUp` clip also leaves this root stationary
(translation change zero; rotation matrix variation 2.23e-16). A static root
alone is therefore not evidence of a transfer bug.

## Results

The original maximum depth, probe maximum depth and unaffected-vertex lower
bound are identical for each row:

| Clip | Samples | Maximum floor depth, mm | Largest probe vertex movement, mm |
|---|---:|---:|---:|
| Jump and land | 239 | 54.077449 | 141.092561 |
| Crawl | 239 | 327.115974 | 203.397126 |
| Dance | 299 | 32.728972 | 103.438601 |
| Wave | 239 | 8.907740 | 24.327282 |
| Kick | 239 | 149.179829 | 88.296623 |
| Get up | 359 | 633.686105 | 142.928788 |
| Run, roll, stand | 419 | 1142.118350 | 819.836796 |
| Asset-authored Lie_StandUp | 141 | 122.873366 | 94.586240 |

The current key-plus-midpoint clock finds deeper penetration than the earlier
key-only results for getting up and rolling. Keep both reports with their
different populations and method bindings; the earlier roll result was
1129.485888 mm at native keys. No threshold changes are involved.

Across 2,174 samples, the skin displacement identity agrees within
9.993e-16 m and local/world reconstruction within 3.553e-15. A separate scalar
weighted-matrix replay verifies all 2,174 unaffected floor witnesses, including
their exact zero root weights, with zero observed depth discrepancy. It uses
the same time sampler, so this is an independent skin/witness arithmetic check,
not an independently implemented animation interpolator.

The existing 141-sample Godot `Lie_StandUp` capture is also replayed against the
current sampler. Requested clock, pose and complete imported skin checks pass;
maximum skin error is 0.031369371 mm against the unchanged 0.1-mm limit. This
reuses a saved native-authoring capture, not a new engine run, gameplay test,
GPU observation or visual review. Agreement does not approve the source clip's
floor contact.

## Evidence and next work

Ten focused tests pass, covering exact-zero ownership, tiny positive weights,
raw nonunit homogeneous response, rotation/translation, input preservation,
malformed clocks and invalid root selection. Both CI source inventories include
the new test module; no current full-suite result is claimed.

Local immutable evidence is in `reports/kaykit-auxiliary-root-v1/` and `v2/`.
The first worker finishes all eight motion diagnostics and ten tests, then
fails because the engine reader receives the capture envelope instead of its
single case. The failure remains preserved. The second worker verifies the
saved reports and all source bindings, replays the witnesses, and correctly
compares the existing engine case without rerunning the eight probes.
Both resource records replay: 64 and 39 observations; peak process-tree RSS
176,574,464 and 132,796,416 bytes. Each retains a 600-MiB available-memory guard
and a 512-MiB process-tree cap. The final result SHA-256 is
`0e711a18132879b0b2a1e695cc94739fe7297290514c42fff68b385cd4d09a1d`.

Next, investigate full-body target proportions and contact placement on the
get-up motion, keeping source joint/mesh problems separate from transfer
problems. The earlier attribution shows the worst native-key get-up vertex is
fully head-weighted. An auxiliary-root-only edit cannot fix that vertex.
Root-only isolation is now tested rather than assumed; a larger body/contact
correction still needs explicit constraints, edit limits, between-key checks,
engine validation and human review. No clip, quality gate or release capability
is approved by this study. The project-wide goal remains active.
