# Coupled native motion and contact surfaces

`scripts/coupled_native_contacts.py` builds one protected proposal model containing every original native edit, displacement, positional/angular rate, point-contact and held-speed condition, plus complete authored surface orientation and facing-side rows. Action names and anatomical joint-name rules do not select its channels or contact regions.

```python
from coupled_native_contacts import CoupledContactModel, acceptable
from native_scene_conic import direction

# motion is a SceneProblem whose caps were captured from the original scene.
# Add the complete declared geometry clocks before constructing this model.
model = CoupledContactModel(motion, surface_policy, contacts_sha256,
                            maximum_contact_rows=50000)
system, jacobian, details = model.linearize(
    original_controls, independently_decoded_worlds, trust=0.02, step=0.001)
delta, proposal = direction(system, jacobian, original_controls,
                            motion.lower, motion.upper, 0.02,
                            hard_rows=details['hard_rows'])
```

This Python API is not a Studio feature or a complete fitting command. The caller must serialize and independently decode proposals, audit static/native permissions, measure complete contact rows and run complete declared geometry before retaining an improvement. A missing or failed geometry report makes `acceptable()` false. Original motions remain selected, and the model never grants quality or release approval.

The base native conditions must already pass. All of them become hard proposal rows, including every authored point and separate game-frame velocity population. Original source-rate arrays, sampling clock, time step and tolerance are captured when constructing the model; changing them afterward rejects. The model does not rebuild caps from a candidate or reset permissions.

Each surface condition receives a separate hard no-regression row. Passing conditions retain their authored limit; failing conditions cannot gain excess over the retained baseline. Original surface limits remain in the soft objective. Neither aggregate improvement nor optimizer success can override an individual row regression. The affine proposal still requires the original independently decoded native checks: exact nonlinear interpolation and Float32 storage can invalidate a predicted step.

`acceptable(before_native, after_native, before_contact, after_contact, full_geometry_report)` requires matching complete finite populations, a passing native baseline and candidate, exact per-contact row protection, passing sampled geometry, no increase in worst positive contact violation and a decrease of more than `1e-12` in squared positive violation. This improvement threshold does not add an acceptance allowance to authored conditions. Successful retention still does not establish that all failing surface conditions have been solved.

## Complete incident-surface cache

`scripts/cached_contact_norms.py` implements `CachedContactNorms`, compatible with the existing `ContactNorms` residual and linearization APIs. For each actor it retains every face incident to any authored individual or centroid group and every vertex required by those faces and contact points. It skins all supplied influences on those vertices. Centroid normals sum the complete union of incident faces once, while centroid positions use the original point group.

Shared actor/time poses are batched rather than re-skinned for each contact group. Actor placement, moving-object normals/points and actual partner surfaces retain their original coordinates and clocks. The full input world population is checked once per call. A cache is rebuilt for each pose population; it is not reused after controls change. Group availability is consulted only at that group's original active times, so an unused degenerate surface at another group's time cannot become a new contact condition.

The original logical actor-pose query budget is preserved even when fewer physical skins are computed. Original row order, point identities, caps, scales, area/coherence reliability tests and facing allowance remain unchanged. Complete contact-row, pose-query and estimated owned-cache/batch byte budgets reject overflow without returning a subset. The byte budget is a working-array estimate, not a process-memory ceiling; caller-owned world arrays and Python/library overhead remain outside it. Defaults allow 20,000 combined contact rows and a 256 MiB cache estimate. Larger row budgets must be explicitly chosen within the existing 100,000-row ceiling.

Incident-surface caching is sufficient for these contact normals and points. It is not a whole-body geometry query. Full actor triangles, primitive enclosure, partner penetration/crossings and declared planes remain the responsibility of the geometry audit. No inferred floor, anatomical palm, force model, continuous collision proof, imported skin validation or human quality assessment is provided by this cache.

## Synthetic validation

Forty-two focused tests cover complete world/object/partner clocks and ordered rows; individual and centroid groups; multiple influences/primitives; shared logical budgets; active versus unused unavailable normals; original clock, input and cap mutation; complete orientation/side derivatives; byte/row overflow; individual condition regressions; and missing geometry. Existing full-population reference calculations remain separate and unchanged. No synthetic success counts as human quality evidence.

## Actual source comparison; correction study still running

The canonical unchanged sphere-hold source retains four contact groups, 1,033 times per group and ten point correspondences. Complete reference and cache calculations agree within `1e-12` for all orientation vectors and facing gaps, with identical caps, scales, ordered point identities and logical query counts. This comparison is complete; it does not accept an animation correction.

One reference construction/evaluation took 150.507434 seconds; one cache evaluation with already prepared topology took 0.119875 seconds. The reference timer includes constructor work and the cache timer does not. Neither includes world decoding, and both finish with source rehashing. These are measurements of this one repeated-row evaluation, not a fair cold-start comparison or a general performance guarantee.

At source publication, the protected proposal study is still performing its full geometry audit. Its explicit clock contains 2,552 times, the union of the 2,201 original geometry/imported times and native/contact/rate clocks. Original source-rate caps were captured before adding geometry clocks and remain frozen. The study permits one coupled proposal, ten saved-curve backoffs and at most one candidate eligible for a full geometry audit. A proposal failing native, individual surface or static-payload checks cannot skip directly to retention. An unaudited candidate's geometry result remains unverified.

No solver or candidate outcome is reported yet. The original clip remains selected. The study uses one humanoid and two declared spheres; the object named `box` is a sphere, and there is no partner or declared floor. Normalized source skin remains distinct from raw engine import. Full-system interaction, engine, continuous collision, anatomy and human quality evidence remain open. All release criteria and evidence lists remain unchanged.

Local evidence: `reports/coupled-native-contacts-tests-v1.log` and the in-progress `reports/coupled-native-contacts-development-v1`. Generated character payloads and complete numeric archives remain outside public Git history.
