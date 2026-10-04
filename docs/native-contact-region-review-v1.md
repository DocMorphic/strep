# Review declared contact regions without replacing intent

`scripts/native_contact_region_review.py` measures whether an authored contact
point is exposed along its winding-derived normal relative to an explicitly
declared mesh region. It preserves the original clip, point references, targets,
timing and limits. Candidate references are advisory choices for an author;
the tool never selects a replacement or approves an animation.

The retained corrected high-five passes its original point-contact condition,
yet both declared hand regions extend approximately 51.741 mm past those points.
The three exposed candidates are 116–118 mm away. Moving the contact there
automatically would change the request and could select fingertips instead of
the intended palm. This review makes that distinction measurable.

## Run and policy

```powershell
.venv\Scripts\python.exe scripts/native_contact_region_review.py contacts.json region-policy.json reports/contact-region-review
```

The output directory must be fresh. The policy binds the exact original contacts
JSON and supplies a region for every contact. A partner contact requires both
regions; world and object contacts require only the source region. Each explicit
region contains unique existing `[meshNode, primitive, vertex]` references and
must include every original contact reference. Regions can span the complete
source mesh; they are not restricted to the 256-point contact limit.

Example structure for a partner contact, with illustrative region references:

```json
{
  "schema": "strep-native-contact-region-review-v1",
  "contacts_sha256": "<exact original contact SHA-256>",
  "maximum_surface_pose_queries": 20000,
  "maximum_candidate_curve_values": 20000000,
  "limits": {
    "support_band_m": 0.001,
    "maximum_candidate_normal_angle_degrees": 20.0,
    "minimum_normal_area_m2": 1e-14,
    "minimum_normal_coherence": 0.1
  },
  "contacts": {
    "palm-to-palm": {
      "source_vertices": [[0, 0, 14712], [0, 0, 1268]],
      "partner_vertices": [[0, 0, 14712], [0, 0, 1268]]
    }
  }
}
```

Use the actual author-selected regions, rather than copying these example IDs.
All four limits are explicit development review parameters, not frozen release
criteria. The maximum budgets are 20,000 full-surface queries and 20,000,000
candidate curve values. The complete declared population must fit both budgets;
exceeding either rejects the review before any full-surface query. No sampled
subset is substituted. A failed attempt remains saved and cannot be overwritten.

## Measurement and candidate contract

For original point `p`, reliable winding-derived unit normal `n` and every posed
vertex `v` of the declared region, the projection is `dot(v - p, n)`. The largest
projection is the forward extent, with an exact witness vertex. The original
point is exposed under this advisory condition when that extent stays within
the declared support band at every original contact time. Both source and
partner sides are measured separately. The old point position/speed result
remains a separate field.

The complete native/30/60/120/240 Hz hold-clock union comes from the existing
contact evaluator. Every posed mesh and every indexed triangle participates;
placements apply to both actors. Individual normals sum all incident face cross
products, counting each face once per vertex. A centroid uses the union of its
incident faces, rather than averaging vertex normals. Degenerate, missing,
cancelled or incoherent normals are explicitly unavailable and prevent exposure
approval. Mesh winding does not establish anatomical meaning or outwardness.

A candidate must lie within the band of the region's forward extent, have a
reliable normal inside the authored normal cone, and remain eligible at every
original contact time. The intersection retains the same material vertex
references through a hold; switching vertices per frame is prohibited. Every
persistent reference and its complete distance-from-original curve is saved.
There is no top-K selection or implicit centroid. More than 256 candidates
remain present but are marked unsuitable for direct encoding as one contact;
explicit author selection is still required for smaller populations.

One full surface pose is cached at a time. Sources, policy and all executed
Python methods are copied and hashed. Original source/method changes reject the
job. Complete observation arrays undergo exact dtype, shape and byte readback.
The result keeps `original_selected: true`, `original_intent_changed: false`,
`anatomical_review_pending: true`, and collision, quality, training and release
approval false.

## Four completed development reviews

The policies declared regions using at least 0.5 summed influence from the
original point's dominant bone subtree, plus every original reference. SOMA hand
subtrees use the provided hand ancestors; the coarse crawl rig uses its provided
dominant bones. Exact references and selection provenance are retained. These
are development declarations, not annotated anatomical palms or soles. The
2,847-vertex SOMA region differs from the older 2,872-vertex diagnostic region.

| Existing clip / side | Original point condition | Region vertices | Maximum forward extent | Persistent candidates |
| --- | --- | ---: | ---: | ---: |
| Source high-five / A, B | Fail | 2,847 each | 51.741 mm each | 3 each |
| Corrected high-five / A, B | Pass | 2,847 each | 51.741 mm each | 3 each |
| Crawl / left shin | Fail across clip | 197 | 6.110 mm | 1 |
| Crawl / right shin | Fail across clip | 197 | 17.274 mm | 1 |
| Crawl / left hand | Fail across clip | 59 | 0.609 mm | 1 |
| Crawl / right hand | Fail across clip | 59 | 0.357 mm | 3 |
| Sphere hold / left hand | Pass | 2,847 | 6.856 mm | 4 |
| Sphere hold / right hand | Pass | 2,847 | 0.586 mm | 21 |

The crawl point result above is the existing aggregate contact result, not an
individual hand failure. Under the declared 1 mm exposure band, both crawling
hand points and the sphere's right-hand point pass this advisory plane condition.
Both high-fives, the shin points and the sphere's left-hand point fail it.
Neither outcome establishes good or bad anatomical contact on its own.

All four jobs complete, retaining 2,214 full-surface queries: 2 + 2 + 144 + 2,066.
The sphere hold retains all 1,033 times per grip and a conservative candidate
curve bound of 5,881,902 values. All input/method bindings and observation
roundtrips verify. No animation was generated or edited, no reserved held-out
example was consumed, and no model was trained. The latest 93 related model-free
tests pass, including complete populations, persistent references, both budgets,
normal reliability, centroid unions, input/method mutation and retained failures.
The test is included in Windows/Linux source CI.

Bound local records are in
`reports/native-contact-region-review-development-v1/checks.json` and
`release-checks.json`. A separately bound CPU Matplotlib projection under
`reports/native-contact-region-review-plot-v1/` displays every declared high-five
region vertex, the original point and all three candidates. The figure is a
projection of posed source geometry, not a GPU render or collision certificate.
Generated reports and third-party character payloads remain local.

## Interpretation and next authoring work

A whole-region supporting plane is a useful diagnostic for this specific point
choice; it is not a universal contact validity test. Curved, concave or wrapping
grasps can have valid localized contact without satisfying whole-hand exposure.
The author must identify the intended localized patch and facing direction.
Changing either produces explicit new intent, followed by separate contact,
complete geometry, motion-limit, engine and human review. Existing failed
studies and fixed-point conditions remain intact.

[ContactOpt (CVPR 2021)](https://openaccess.thecvf.com/content/CVPR2021/html/Grady_ContactOpt_Optimizing_Contact_To_Improve_Grasps_CVPR_2021_paper.html)
is research precedent for predicting surface contact and optimizing hand pose.
Its contact model allows interpenetration to approximate soft tissue. This
simple Strep diagnostic uses none of its models, training data or penetration
allowances and does not establish equivalent grasp quality.

Next, make localized author choices reviewable and test motion corrections
under preserved source constraints across additional development actions and
rigs. Broader held-out semantics and developer cleanup review remain required.
Action categories remain evaluation strata rather than an allowed-prompt list.
The full project goal and all release gates remain open.
