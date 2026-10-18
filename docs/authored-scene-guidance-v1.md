# Authored scenes and metric retention during sampling

Development prototype, 2026-10-18. The whole-project goal and every release
criterion remain unchanged. The default generator and Studio selection stay
unchanged.

The [first scene-energy pilot](scene-denoising-guidance-v1.md) improved point
tracking while worsening maximum penetration. The next stage adds complete
named metric retention and connects real saved scene inputs to the experiment.

`scene_metric_retention.py` compares every supplied lower-is-better scalar in
matching named arrays. It preserves names, shapes and row order, records every
metric's increased-row count, and rejects even a last-row increase hidden by
an improved average. There is no added tolerance, score averaging or dropped
population. Explicit size bounds reject oversized comparisons.

`kimodo_scene_retention.py` wraps the existing energy proposal. Its three
predeclared rays (1, 1/2, 1/4) must each lower energy and preserve every supplied
metric relative to that call's original clean prediction. Every rejection and
inner energy proposal remains recorded. If no ray passes, it returns the
original prediction object. Disabled/out-of-schedule calls preserve the existing exact
passthrough behavior without calling metric or energy evaluators.

This local guard is separate from comparing the finished sampled clip against
its matched ordinary baseline. Later diffusion steps can change earlier
results. Both checks are necessary; neither confers realism or release approval.

`compile_scene_guidance.py` freezes the complete authored scene and source
motion hashes, all primitive tracks and relevant contact intervals. Box,
sphere and cylinder descriptors keep their actual geometry. World/object and
fixed-reference partner targets are transformed into the selected actor's
native frame using the recorded rigid placement and an explicit XZ origin
offset. No origin is guessed. Normal/tangent targets retain actual adjacent
skin triangles and wrist/knuckle mappings. Incoming partner point relations
keep their original identity and use the fixed source partner track.

Reference partners are not jointly sampled motion. Distributed regions and
dynamic same-actor targets reject rather than becoming point/reference proxies.
Partner/self/continuous triangle collision, attachment, object forces and
human/anatomical review remain required separately.

`authored_skin_scene_energy.py` uses actual decoded poses and the complete
sparse skin. Energy and metric evaluation preserve all supplied frames,
vertices, eight influences, objects and contact intervals. Activation chunks
do not alter the observation population. Metrics include complete per-frame
floor/object maxima, penetrating-vertex counts and squared depths; every
contact position/normal/tangent/degeneracy row; and complete skin/joint speed
and acceleration peak tracks. These are numerical geometry/motion observations,
not calibrated physical capacities or proof of natural animation.

The 62 local checks pass: 36 new cases plus the previous 26. They cover exact
retention and hidden regressions, source/read races, arbitrary rigid placement
and explicit origin transforms, all three primitive types, preserved target
intervals/orientation, incoming partner relations, unsupported requirements,
full gradient/metric equivalence across activation chunks and existing hook/
skin behavior. Model-free compiler/comparison tests enter both source manifests;
the tensor suites enter the existing CPU adapter and focused OS workflows.

The real preparation study retains the existing moving-box and high-five
scenes unchanged. It produces three actor plans: box A (180 frames), high-five
A and B (120 frames each). The box's whole moving track and both 61-frame grip
intervals remain intact. Owned target tracks reproduce the existing world
measurement within 2.711e-17 m. Both high-five actor plans keep the shared
original three-contact identity list, including the incoming partner relation.
These scenes and their source poses remain development failures, not approved
targets or clean training data. Local evidence is under
`reports/authored-scene-guidance-tests-v1` and
`reports/authored-scene-guidance-prepare-v1`.

Actual matched checkpoint sampling and independent saved-file validation are
the next evidence. Report zero retained proposals as a failed correction
attempt, not a solved interaction. Full primitive triangle/partner checks,
semantic and action breadth, retargeting, style/stat calibration, transitions,
engine import and real review/cleanup stay part of the same entire-project goal.

## Actual authored-scene trial

`reports/authored-scene-guidance-pilot-v1` completes nine fresh unchanged-
checkpoint samples: ordinary, energy-only and metric-retained modes for the
moving-box actor and both high-five actors. The prompts are the original
development descriptions, seeds 77 / 77 / 88 respectively, 180 / 120 / 120
frames, 100 steps, CFG [2,2], no postprocessing, and the same five late mapped
base timesteps [0,10,20,30,40]. Existing validated v0 cached text features and
the established CUDA transport are retained. This is a functional study on
known development scenes, not a quality comparison against the best prior
pose-guided baseline or held-out release evaluation.

| Actor | Ordinary maximum contact error | Energy-only maximum contact error | Retained changes |
| --- | ---: | ---: | ---: |
| Moving box A | 824.015 mm | 822.931 mm | 0 |
| High-five A | 991.971 mm | 981.104 mm | 0 |
| High-five B | 932.516 mm | 928.321 mm | 0 |

All three energy-only final clips fail complete raw-metric nonregression.
Per-call guards reject all 15 inner energy steps and all 45 fixed metric-ray
trials. Each retained-mode sample has **every raw array byte-identical to its
ordinary baseline**. Finished raw metric arrays are also compared separately:
1,916 scalars for the box actor and 840 for each high-five actor. Baseline
errors remain failed errors. **Zero accepted edits is a failed correction
attempt, not a successful interaction or motion-quality pass.** No clip is
adopted. Complete object tracks, all original contact IDs/intervals and
orientation targets remain bound; partner targets remain fixed source motion.

The model study completes in 154.532 s with 1,749,499,904-byte peak tree RSS,
within the predeclared 2 GiB expected / 3 GiB maximum policy and unchanged
600 MiB reserve. No weights, data, encoder, default generator or release gates
are changed.

`authored_scene_observations.py` adds an independent model-free observer of
all native scene metric arrays from supplied raw or saved GLB poses. It uses
the established NumPy skin/primitive libraries, excludes guidance and Torch,
keeps exact row populations and recomputes actual normal/tangent triangles.
The source suite now passes **67 cases**, including five additional complete
observation tests. The same 67 pass on both hosted operating systems at
`7550aac052a4ed679dced16cbaa0f839ceb93cf3`
([focused run 39122376511](https://github.com/DocMorphic/strep/actions/runs/39122376511)).

`reports/authored-scene-guidance-replay-v1` independently checks all nine saved
GLBs and their full original scene/motion metric populations: **22,750,560
vertex/frame pairs**, original eight weights/indices and all 36,108 faces.
Maximum skin-component error is 5.740e-7 m. Guidance, decoder, sparse Torch
skinning and Torch itself are excluded. All three energy-only clips fail
independent raw and saved nonregression; all three retained clips reproduce
their ordinary raw arrays **and GLB files byte for byte**. Separate Float32,
NumPy and serialized observations stay distinct; no physical epsilon is added
to reconcile numerical differences. Shared baseline geometry libraries do not
constitute independent physics. The 512 MiB replay completes in 87.937 s with
117,903,360-byte peak RSS and the unchanged 600 MiB reserve.

## What the rejection means

The preserved rejection ledger identifies every failed metric group in all
45 fixed ray trials. All 15 box trials worsen floor and contact rows, as well
as source motion tracks. The 30 high-five trials are locally rejected **only
by source speed/acceleration preservation**. Their complete finished
energy-only clips also worsen sampled floor rows after subsequent denoising.
The average/max contact improvements do not hide these failures.

Speed and acceleration are not universally lower-is-better measures of
realism. They are complete source-preservation probes in this versioned
experiment. This strict policy is not a new global ban on faster or more agile
characters. Next separate physical contact/penetration requirements from
explicit authored timing/style/motion envelopes, keeping every original trial
and release criterion intact. Do not relax a failed physical threshold or
reinterpret rejection as successful animation. Source-relative edit caps also
remain distinct from physiological strength/fitness calibration.

The completed checkpoint is `reports/authored-scene-guidance-progress-v1`.
Its streaming audit verifies 6,275 current source, checkpoint, cache, asset,
data and resource bindings and the prior whole-goal checkpoint receipt. All
45 rejection rays are rechecked against their complete metric summaries.
It completes in 51.109 s with 54,390,784-byte peak tree RSS, preserving the
512 MiB cap and 600 MiB reserve. The audit confirms the fixed release contract
changes only in goal line 3 and the two permitted progress fields. All 14
capabilities remain unapproved and the entire-project goal remains active.
