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
inner energy proposal remains recorded. No retained ray returns the original
prediction object. Disabled/out-of-schedule calls preserve the existing exact
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
attempt, not a solved interaction. Full primitive triangle/partner checks,+semantic and action breadth, retargeting, style/stat calibration, transitions,
engine import and real review/cleanup stay part of the same entire-project goal.
