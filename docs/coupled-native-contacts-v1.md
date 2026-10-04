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

## Actual source comparison at initial publication

The canonical unchanged sphere-hold source retains four contact groups, 1,033 times per group and ten point correspondences. Complete reference and cache calculations agree within `1e-12` for all orientation vectors and facing gaps, with identical caps, scales, ordered point identities and logical query counts. This comparison is complete; it does not accept an animation correction.

One reference construction/evaluation took 150.507434 seconds; one cache evaluation with already prepared topology took 0.119875 seconds. The reference timer includes constructor work and the cache timer does not. Neither includes world decoding, and both finish with source rehashing. These are measurements of this one repeated-row evaluation, not a fair cold-start comparison or a general performance guarantee.

At source publication, the protected proposal study is still performing its full geometry audit. Its explicit clock contains 2,552 times, the union of the 2,201 original geometry/imported times and native/contact/rate clocks. Original source-rate caps were captured before adding geometry clocks and remain frozen. The study permits one coupled proposal, ten saved-curve backoffs and at most one candidate eligible for a full geometry audit. A proposal failing native, individual surface or static-payload checks cannot skip directly to retention. An unaudited candidate's geometry result remains unverified.

At that publication, no solver or candidate outcome had been reported. The original clip remains selected. The study uses one humanoid and two declared spheres; the object named `box` is a sphere, and there is no partner or declared floor. Normalized source skin remains distinct from raw engine import. Full-system interaction, engine, continuous collision, anatomy and human quality evidence remain open. All release criteria and evidence lists remain unchanged.

Local evidence: `reports/coupled-native-contacts-tests-v1.log` and `reports/coupled-native-contacts-development-v1`. Generated character payloads and complete numeric archives remain outside public Git history.

The [native contact-support preflight](native-contact-support-v1.md) identifies twelve failing source orientation rows at structurally frozen held endpoints in this setup. Interior improvements would not make all authored surface rows pass. Its inputs remain unchanged; a broader edit setup needs a separate study with original source-rate and contact limits retained.

## Completed protected proposal study

The complete canonical source geometry audit passes all 2,552 declared times, with 5,104 actor/sphere records. All loaded actor triangles and primitive center-containment conditions are included. The maximum reported depth upper bound is `9.818366e-14` m, a floating reserve with no positive sphere-depth witness. The 15,313-array archive retains 7,371,829,696 logical bytes without truncation or downcasting. This is sampled geometry, with no floor, self-collision, continuous-time or engine certificate.

The coupled model contains 303,593 native conditions, 30,990 authored surface rows and a separate duplicate of every surface row for protection: 365,573 norm rows in total, with 334,583 hard rows and 36 control components. Model construction takes 28.666860 seconds. Its native Jacobian has 30,656,508 nonzero entries out of 32,788,044 dense positions; the complete protected matrix stores 34,347,054 entries. This observed density warrants investigation of the continuous proposal differences before expanding the solve; no small coefficient is discarded to improve the measurement.

Clarabel 0.11.1 reports `MaxTime` after 24 iterations under its 30-second phase limit, with 71,477 active cones. It returns no direction. Consequently there are zero serialized candidate trials, zero candidate geometry audits and zero accepted corrections. `MaxTime` is a solver-budget outcome, not a proof of infeasibility. The separate frozen-endpoint diagnostic establishes why this particular edit setup cannot satisfy every authored surface condition.

Independent replay reconstructs the original source-rate caps, reproduces all 303,593 native source conditions and re-skins the entire loaded actor surface at every one of the 1,033 unique contact clocks. All 10,330 point-normal observations and 30,990 orientation/facing residuals agree with at most `2.198242e-14` difference. It checks every protected model row, exact guard/soft row correspondence and paired Jacobian entries. It also verifies the entire numeric archive transport and reduces every saved geometry decision. Geometry queries and center-containment calculations are not independently rerun. Candidate fields remain unverified because no candidates existed.

Two verifier-only failures are retained: an unnecessary sorted-storage assumption for valid CSC entries, then a missing source-surface result mapping. Fresh versions compare entries by row identity and invoke the complete source-surface replay. Producer code, numeric archives, limits and proposal results remain unchanged. Ninety-four cache/coupled/reference tests pass from an isolated source copy without vendor code, models or character assets.

A separate prepared setup extends the twelve-channel edit window to `[1.75, 4.3]`, with knots at `1.75`, `2.0`, `4.0333333015441895` and `4.3`. It has 72 control components and no structurally frozen contact observations, while retaining rotation/displacement budgets, source actor/object/contact payloads and source-rate/contact/geometry limits. It has not been solved or certified feasible. Original clips remain selected; all release criteria and evidence stay unchanged.

Local evidence: `reports/coupled-native-contacts-verification-v5`, `reports/coupled-native-contacts-clean-source-v1` and `reports/expanded-native-contact-support-preflight-v1`.
