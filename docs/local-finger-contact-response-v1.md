# Local finger contact response

The retained development clip has correct point contacts but still fails authored surface facing. This experiment diagnoses that failure and measures an actual local motion change without relaxing targets, clocks or limits. It concerns one humanoid holding two spheres. The contacts named `grip` are explicit vertices, predominantly weighted to pinky joints; they are not verified anatomical palms or a completed box pickup.

## Rigid normal-field diagnosis

`scripts/rigid_contact_normal_bound.py` compares every pair in a caller-selected normal field. For one common rigid rotation and an opposition allowance θ, sphere triangle inequalities require

`θ >= |angle(source_i, source_j) - angle(target_i, target_j)| / 2`.

Negating every target normal leaves its pair distances unchanged. The largest pair bound is necessary, not sufficient: it neither finds a rotation nor rules out local skin deformation. Arithmetic is floating point, not an interval certificate. Missing/non-unit normals, unmatched populations and excessive complete pair budgets reject.

The saved, previously replayed source/default-import/native-authoring reports supply all five points per hand at all 1,033 shared contact clocks, including all ten pairs. Every frame's bound exceeds the unchanged 15° allowance. Peak lower bounds are 26.45266°/26.51913° for source left/right, and 26.45512°/26.51382° for imported left/right. The peak witness is points 2 and 3 in main-point-plus-neighbours order, at 4.0333333015441895 s. This rules out the common rigid normal-field hypothesis for those observations; it does not establish anatomical intent or general pose infeasibility. No new poses, geometry queries or engine runs were used for this diagnosis.

## Local motion experiment

`scripts/native_contact_mask_probe.py` probes both exact signed coordinate steps for an explicit mask of 1–24 normalized control components. Steps must be 1e-6–.005 and fit both sides of the original boxes; clipping, implicit masks and baseline recentering are rejected. Every unselected component stays equal to the supplied baseline. Original curves, Float32 source-scale rotation storage, original source-derived sampled caps, contact references, target points, timing and limits remain in force.

It predicts each stencil on the complete original native/contact clocks, then independently exports and decodes the baseline and the candidate with the best predicted worst/total surface score. If a different candidate has the best score among predictions passing all motion and point conditions, that candidate is also decoded. Saved arrays distinguish predicted from decoded measurements. Static payloads, permissions, frozen keys and native clocks are audited on exported clips. Mid-study input or method mutation prevents a complete receipt and preserves partial output. This is a finite response experiment; it never writes retained controls or grants collision, engine, training or quality approval.

```powershell
python scripts/native_contact_mask_probe.py --contacts SOURCE_CONTACTS.json --permissions PERMISSIONS.json --surface-policy SURFACE_POLICY.json --baseline BASELINE.npy --output FRESH_PROBE_FOLDER --indices 30 31 32 33 34 35 66 67 68 69 70 71 --step .005
```

Those example indices were read from this rig's declared `LeftHandPinky1`/`RightHandPinky1` tracks. Other rigs require their own explicit control mapping. Permissions and surface policy must bind the original contact scene; the baseline is expressed relative to that scene's original curves, not a newly centered candidate.

The development run completes 24 predicted probes. All 12 components belong to the two pinky tracks; forearm, wrist and other finger controls are frozen. Three right-hand signed probes fail original protected conditions, so a local finger mask alone does not guarantee motion feasibility. The best prediction is component 33 minus .005. Its independently decoded GLB passes all **303,761** sampled native/motion/point conditions, including **276,471** protected rows, and regresses zero guarded surface rows. It covers **1,617** distinct native/contact motion clocks, **4,132** contact samples and **30,990** surface residual rows. The separate full geometry job uses 2,552 clocks. Baseline export reproduces the exact previously retained actor hash.

| Decoded measurement | Retained baseline | Provisional local change |
| --- | ---: | ---: |
| Worst positive normalized surface residual | 1.9132966708083026 | 1.9092579696629004 |
| Sum of squared positive surface residuals | 7467.535326933635 | 7444.538265321576 |
| Failed surface rows | 2066 | 2066 |
| Failed native/motion/point rows | 0 | 0 |
| Guarded surface rows regressed | — | 0 |

The small improvement establishes a useful local response, not a solved grasp. Full native mesh measurement completed on all **2,552 unchanged geometry clocks**, all **18,056 vertices and 36,108 triangles**, with original geometry, placements, planes, objects and limits. All sampled conditions pass; every sample is measured freshly, with zero reused queries. The original worker exits are zero. The provisional actor remains unretained, with original selection preserved. Actual imported-candidate checks, full independent replay and anatomical/human review remain outstanding. No engine or GPU was run for this new candidate. Full geometry result SHA256: `437c443343ea8f65771d2f6a9b005f6634949dd487cd2d4bb0810a682b9af420`.

## Validation and provenance

An isolated public-source copy passes **31 checks** in **6.56 s**: 11 rigid-bound cases and 20 mask/probe cases. Tests include a necessary-but-insufficient normal-field example, complete pair populations, antipodal normals, explicit mask/box failures, actual tiny GLB export/decode/static audits, unchanged control components and mutation preserving partial evidence. No models, vendor code or downloaded characters are copied. The initial direct test invocation failed collection because the new tests lacked the repository's explicit `scripts` import path; adding it resolved collection. Production methods and limits were unchanged.

Local evidence is preserved under ignored `reports/rigid-grip-normal-bound-v1`, `reports/local-finger-response-v1`, `reports/local-contact-diagnostics-source-check-v1` and `reports/local-finger-geometry-v1`. Method/input/request/array bindings are stored with each study. The full-project goal remains active; no release evidence or human cleanup record is added from this diagnostic.

## Cross-hand object conflict and inspection

The existing object-only preflight and the newer pair-bound API were also compared on the current completed imported observations. At every one of **1,033 object clocks**, they retain all **ten active hand points and 45 pairs** from four contacts, covering **4,132 contact samples and 10,330 normal observations** per mode. The native-authoring/default-import source-surface fields give the same result: necessary opposition allowances range from **38.41922° to 39.23408°**, above the unchanged 15° limit. Maximum library disagreement is 7.11e-15°. The strongest cross-hand witness is neighbour point 2 on each hand, at **4.020833333333333 s**. This is distinct from the earlier preflight's 41.31210° result on its different measured source epoch; neither result replaces the other.

This condition concerns rigid object pose changes with all measured character surfaces and authored local target normals held fixed. It does not rule out body deformation, different authored correspondences or a revised interaction intent. Source winding and bone weights do not establish an anatomical palm. The result supports reviewing contact patches and body corrections; it grants no feasibility or quality approval.

A local CPU inspection figure shows both hands in three orthographic views at **4.000 s**. Points 0–4 identify the main grip and four neighbours; red indicates the existing facing/side failure, blue a passing point, and green crosses the authored targets. All geometry is extracted from a previously completed native mesh archive for the exact retained actor. Each selected array is checked against the pinned archive receipt's dtype, shape, bytes and logical hash. Other archive arrays and the full 2.35 GB archive hash are not reread. The figure creates no new pose or collision query, changes no asset and counts as no human review. Display triangles are the crop incident to positive declared hand-subtree influence, not a new mesh audit or anatomical classifier. Matplotlib 3.10.8 runs through its CPU Agg backend in a separate ignored plotting dependency target; the live geometry environment is unchanged. An initial label layout is preserved alongside the clearer second figure.

The reviewed image and its request/snapshot/plot bindings remain local under `reports/current-hand-contact-review-v1`. The point cluster and the normal arrows provide a developer inspection aid; a complete animation, anatomical decision and timed cleanup review remain required.

A fresh isolated source copy passes **96 checks in 16.69 s**: the existing 58 mask/composition/normal cases, one new compatibility case and 37 existing object-bound/preflight regressions. The compatibility case rotates the whole target frame independently at each sample and confirms the necessary bound remains consistent. Production methods, limits and the live/queued studies remain unchanged. The object-wide saved-data cross-check is `reports/current-object-normal-bound-crosscheck-v1`; receipt SHA256 `04e8525ba8ba487141e6e35100b91036fc9b1e0703c5c99bc2f24fbe8e23fea0`. Source receipt SHA256: `80e79d53a5278a249d65fa5977c19420b592181d760d9e7aa99a8953f9294874`.
