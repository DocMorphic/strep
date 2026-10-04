# Multiple-point rigid-object holds

An experimental CPU authoring command can fit a declared object's trajectory to
three or more explicit, noncollinear surface correspondences. Character files
remain byte-identical. This extends object editing across arbitrary supplied
rigs; it does not generate finger articulation or approve a grasp.

The [two-grip operation](native-object-hold-fit-v1.md) retains its existing
protocol and reference-dependent twist behavior. Two points constrain an axis
but leave rotation around it undetermined. The new operation uses all selected
points to propose a proper rotation and translation by equal-per-correspondence
least squares, with reflections excluded. Its kernel is checked against
[SciPy's documented Kabsch alignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html).
This minimizes squared point error; it is not a minimax solver or a proof that
no other bounded pose could pass.

## Explicit request

The source is a `strep-native-scene-contacts-v1` JSON. Selected contact IDs must
describe holds on the same declared object over the same complete interval.
Each individual vertex contributes one matched object-surface point; an
explicit centroid contributes one correspondence. Several loaded actors can
supply points. No contact patch or anatomical role is inferred.

```json
{
  "schema": "strep-native-object-correspondence-fit-v1",
  "contacts_sha256": "<SHA-256 of the source contacts JSON>",
  "object": "item",
  "contact_ids": ["left-palm", "right-palm", "left-side"],
  "edit_window_s": [1.5, 4.5],
  "maximum_translation_m": 0.002,
  "maximum_rotation_degrees": 2.0,
  "maximum_keys": 3601,
  "maximum_correspondences": 16
}
```

```text
python scripts/native_object_correspondence_fit.py contacts.json request.json geometry-policy.json fresh-output
```

Three to 256 distinct object-local correspondences are supported. The explicit
budget must cover every selected point. Noncollinear local and observed
geometry and nondegenerate covariance are required; the command rejects
unobservable fits instead of guessing the missing twist. All native keys and
all twelve 30/60/120 Hz rate/phase populations enter the held fit. Positive
ingress and egress surround the hold, with quintic correction weights returning
to the original object path. Resource overflow rejects the whole population.

Only the selected object's keyframes change in a separate proposal. Original
keys outside the edit window preserve their exact JSON values. Other objects,
all contact intent and limits, actor placements, animations and GLB bytes remain
unchanged. Source files and implementations are archived and hash-bound.

The saved proposal is reopened before evaluating all scene contacts. Original-
relative pose budgets and complete sampled scene geometry are separate gates:
passing point contacts cannot override excess movement or collision. Geometry
includes all loaded actor triangles against all declared objects, actor pairs
and world planes on the policy's expanded clock, including every new object
key. No failed condition is silently removed. Finished proposals, including
rejected ones, retain observations and decisions; computation errors retain
their failure archive. The original remains selected and quality, release and
training approval remain false.

## Development measurements

A procedural closed-cube case introduces alternating twist around the axis
defined by its first two grips. The unchanged two-point operation retains that
twist and exceeds the third grip's 5 mm position limit by producing over 6 mm
error. The new three-point proposal passes saved contact, slip, edit-budget and
sampled geometry checks. Individual and grouped correspondence forms are both
tested. This constructive fixture demonstrates observability and preservation,
not human animation quality.

The actual humanoid trial uses the earlier, previously corrected and unapproved
sphere-hold animation. It adds **all immediate
triangle neighbours** of the two original grip vertices, selected in sorted
native order before fitting. At the original hold start, those eight new points
are radially projected onto the original sphere. Both original grip targets
and all prior conditions remain unchanged. This explicitly adds contact intent
to a development case; it is not a held-out test, a same-contract improvement
claim or evidence that arbitrary object surfaces are solvable.

The resulting ten correspondences cover four held contact conditions. The
original limits remain 5 mm position error, 5 mm/s slip, 2 mm translation and
2 degrees rotation around the 2–4.0333333015 second hold, within a 1.5–4.5 second
edit window. Actor motion and both declared sphere geometries remain unchanged.

The source path fails three of the four conditions: the right grip's slip and
the two added patches' point distances or slip. Both the earlier two-point path
and the new ten-point proposal pass every contact condition under the added
intent. They differ in the original-relative object edit budget:

| Measurement | Earlier two-point path | Ten-point proposal |
| --- | ---: | ---: |
| Maximum point error across all four conditions | 4.767394 mm | 4.668694 mm |
| Maximum slip across all twelve populations | 3.149603 mm/s | 3.157128 mm/s |
| Maximum object translation | 0.994770 mm | 4.707991 mm |
| Maximum object rotation | 0.014456 degrees | 2.301633 degrees |
| All original pose-budget conditions | Pass | **Fail** |
| Saved object keys / geometry times | 1,266 | 1,266 |

The new proposal stays rejected despite its slightly smaller point error. The
earlier path provides a feasible numerical reference; adding correspondences
does not make unconstrained least squares preferable to that bounded result.
This failure cannot be presented as an impossible task or justification for
loosening its limits.

The earlier geometry observations are bound to the identical actor bytes,
placements, object geometry and complete object paths, policy limits and full
1,266-time clock under the added contact intent. No geometry query is rerun for
that reference. Its archived geometry and original verification stay intact.
Two method files have changed since that study to stream observation arrays;
AST comparison verifies unchanged geometry calculations, request validation,
two-point proposal and pose-bound calculations. The storage-container changes
are recorded explicitly. Initial reference-binding attempts fail on an older
result format and method drift and remain retained; the final binding validates
the archived receipts and these specific source differences.

The ten-point proposal also passes the full sampled geometry check: all 36,108
actor triangles against both declared spheres at all 1,266 expanded times,
giving 2,532 complete actor/object observations. Both object centers remain
outside the closed actor volume. No partner or world plane is declared, so this
does not establish partner or floor clearance. Contacts and geometry passing
still do not override the failed pose budgets.

Independent SciPy alignment reconstructs every saved proposal array within an
absolute component tolerance of 1e-12, including complete native/phase clocks
and ingress/egress. Saved contact arrays replay exactly; every point distance,
all twelve speed populations and original-relative pose-budget decisions are
recomputed. Complete per-triangle depth-array reductions are checked for every
geometry observation without repeating the expensive queries. Original
containment observations and shared native skin decoding remain distinct from
the independent rigid alignment.

The retained procedural case also replays its full 156-key proposal and all 156
complete geometry observations. Its first replay stops because an archived
authored relative GLB path is interpreted from the snapshot directory. The
corrected replay loads the byte-bound actor snapshots while preserving the
original JSON and input bindings; the failed directory remains retained. The
humanoid's earlier successful verifier revision is archived separately.

All 49 related model-free regressions pass, covering complete correspondence
populations, centroids, multiple actor placements, reflections, degeneracy,
separate contact/budget/geometry failures and unchanged source artifacts. New
tests are included in public CI. The preceding public commit passed all four
CI jobs; this change starts a new run after publication.

## Limits and next work

This operation proposes object motion around supplied animation. It does not
repair the character, select contact anatomy, enforce forces, certify
continuous collision, infer a floor or validate self/object-object collision.
Point correspondences do not substitute for palm orientation, finger shape,
support, action semantics, engine playback or timed human cleanup review.
Numerical edit-budget failure means this proposal failed; it does not establish
that the authored task is impossible. A subsequent bounded proposal must retain
the same contact intent and acceptance limits.

Local evidence stays under ignored `reports/native-object-correspondence-development-v1`.
The original contact specification SHA-256 is
`59fc7f796ec40e42569dacfb5535c345851ef4d62a82c822127ec888e36f59a9`;
the unchanged actor GLB SHA-256 is
`aa650e4a9199ab356f54015b5b346bdca4da80db102aae9a690fb841bb69b5da`.
Source, tests and this summary are public; character payloads and generated
geometry archives are excluded. No new model sampling or training is performed
by this operation, and the project-wide release goal remains active.
