# Coordinated stored-key repair experiment

The passive crawl inspection finds 41 remaining source-rate failures with
permitted support and nonzero saved caps. Many angular failures share nearby
forearm/hand support. `scripts/native_component_pair_search.py` adds an explicit
experimental alternative to changing one stored component at a time.

A proposal contains two absolute choices, each within the existing nearest or
one-neighbor Float32 envelope. It can coordinate different components at one
key, or the same component at adjacent editable keys of the same actor/track.
It can restore or replace existing corrections. It cannot accumulate steps,
add an unpermitted channel/key, alter controls/caps or exceed the original
correction count. Cross-track and nonadjacent pairs are outside this experiment.

The planner constructs the complete eligible pair population from the existing
four-rate failure planner. It rejects populations above its declared 65,536
candidate budget rather than silently clipping them. Deterministic round-robin
ordering shares a finite export prefix across actors, tracks and both pair
families. This is a search-order choice, not proof that a feasible clip exists.

The existing search core freshly decodes each complete native export and checks
every original row, cap, scale and control value. Authoring/near-unit/storage
audits run before and after export. Acceptance remains the existing first
improvement in native merit; only a complete native pass can be returned as a
repair. Partially improved anchors stay raw diagnostic evidence, with original
motion selected. Geometry, engine fidelity, semantics and human quality are
separate requirements. The default single-component fitter/Studio contract is
unchanged; this module is an explicit experiment.

All 69 related local tests pass (20 new paired-search cases and 49 existing mixed
storage/fitting cases); all 57 resource observations replay. New checks cover
complete pair populations, interleaving without dropped actor/track groups,
immutable caller data, invalid budgets/options, locality, absolute restoration,
actual two-component GLB export, unchanged intended curves, storage capacity,
complete archived observations and rejection of a forged decoded residual.
Inventory is 476 Python modules / 42 Node suites. The test record remains at
`reports/component-pair-checks-v1`.

## Matched retained humanoid protocol

`reports/crawl-paired-comparison-v1` starts both alternatives from the separately
replayed 41-failure crawl anchor. Controls, original 63-control authoring,
boundary/geometry contracts, source assets, original cap arrays and clocks are
identical. Each receives one stage with at most 32 probes; first-improvement
can stop early, so actual export counts and runtime must be reported separately.
Neither finite prefix is an exhaustive comparison or the original four-case
text-generation baseline.

Every probe retains complete decoded native observations and asset hashes.
Each best anchor additionally receives the original full 2,017-time floor
screen, regardless of native failure. Changes to previously passing rows and
root acceleration are reported alongside repaired rows and native merit. The
best anchor does not replace the returned result or enter training/release
evidence just because some failures decrease.

## Actual result and fresh replay

Both searches complete. The shared initial worst normalized excess is
`5.392360307710583e-6`. Neither repairs a failed row or breaks a previously
passing row, and both still return the 41-failure seed.

| Measurement | Single-component | Paired-component |
| --- | ---: | ---: |
| Complete planned proposals | 644 | 2,756 |
| Changed probes until first improvement | 18 | 3 |
| Native exports including start | 19 | 4 |
| Best worst normalized excess | 5.272741590159666e-6 | 5.145726907904529e-6 |
| Best squared positive residual sum | 1.6323476710957704e-10 | 1.199626820096588e-10 |
| Best failed native rows | 41 | 41 |
| Root acceleration failed rows | 0 | 0 |
| Failed floor times | 2,017 / 2,017 | 2,017 / 2,017 |
| Peak floor depth | 257.398701 mm | 257.398701 mm |

The accepted **partial** paired change is LeftForeArm (node 30), rotation key
90, components 3 and 2, both with absolute step -1. It lowers both recorded
merit terms; the single change lowers the worst term while its secondary term
worsens. These tiny storage changes do not solve clearance or establish visible
motion-quality improvement. Ordering differs as well as proposal family, and
first-improvement stops early; this is not a causal ablation or evidence of
general superiority. Native and geometry decisions remain failed.

The comparison finishes at 244.922 seconds execution and all 258 resource
observations replay. A separate worker reconstructs returned/best GLBs for both
modes, matching every payload, world matrix, native row, norm cap/scale, control,
clock and typed continuation. It recomputes identical original rate-cap arrays
and every floor sample for both best anchors. All 23 raw receipt/payload/array
hashes validate; other neighbors are not numerically replayed. This fresh replay
shares repository arithmetic, finishes at 87.906 seconds and all 104 resource
observations replay. Evidence remains in `reports/crawl-paired-comparison-v1`,
`reports/crawl-paired-comparison-replay-v1` and
`reports/paired-native-inspection-v1`.

The preceding `98040de` commit passes all six focused Windows/Linux jobs with
890 Python tests per OS, 33 subtests and offline editor checks; existing actual
engine fixtures also pass. These predate the paired-search addition. The larger
full-source workflow and this addition's hosted outcome remain separate.

Next measure a bounded continuation from the freshly replayed paired partial
anchor, retaining original limits, root checks and complete floor rejection.
Broader scene/partner, rig, arbitrary action/style/editing, transition/export and
human cleanup/release validation remain required. No new model inference,
training, held-out prompts, engine playback or human approval is claimed here.
