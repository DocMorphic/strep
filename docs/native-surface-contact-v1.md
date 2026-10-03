# Surface-facing conditions for authored point contacts

`scripts/native_surface_contact.py` adds explicit orientation and sidedness
conditions to existing rig-bound point contacts. A short point distance alone
does not establish that two intended contact surfaces meet from their facing
sides. This audit is read-only and keeps all original contact limits. It does
not identify anatomical palms or prove collision freedom.

```powershell
.venv\Scripts\python.exe scripts/native_surface_contact.py contacts.json surface-policy.json reports/surface-contact-audit
```

A fresh output directory is required. The policy binds the exact contacts JSON
and covers every contact. For a partner target, normals derive from its exact
target vertex references. World and object targets require explicit unit
normals, in world and object-local coordinates respectively. Object-local
normals follow the declared rigid pose at each exact contact clock.

Example for a partner contact named `palm-to-palm`:

```json
{
  "schema": "strep-native-surface-contact-v1",
  "contacts_sha256": "<exact source contact SHA-256>",
  "maximum_actor_pose_queries": 2000,
  "limits": {
    "maximum_opposition_error_degrees": 15.0,
    "backface_allowance_m": 0.0005,
    "minimum_normal_area_m2": 1e-14,
    "minimum_normal_coherence": 0.1
  },
  "contacts": {
    "palm-to-palm": {
      "target_normal": { "space": "partner-surface" }
    }
  }
}
```

For a world target, use `"target_normal": {"space": "world", "normals":
[[0.0, 1.0, 0.0]]}`. An object target uses `"space": "object"` and local normals.
Supply one normal per measured point, or one for an explicitly authored centroid.
The example limits are prototype authoring choices, not frozen release targets.

## Measurements and reliability

For each individual source or partner vertex, the oriented normal sums the
area-weighted cross products of all incident posed triangles. A centroid uses
the union of incident faces, counted once per group. These directions follow
mesh winding; outwardness and anatomical meaning are not inferred. Cancellation,
degenerate incident faces, missing faces or insufficient area/coherence make
the normal unavailable and the condition fail. Vertex or face populations are
never silently truncated. Exceeding the explicit pose-query budget rejects the
audit without returning a partial result.

For source normal `nA`, target normal `nB` and source-to-target offset `d`, the
opposition error is `acos(-dot(nA, nB))`. Facing-side projections are `dot(nA, d)`
and `dot(nB, -d)`. Both projections must stay above the explicitly allowed
negative distance. Original point position/speed conditions must also pass.
Coincident points still require valid opposed normals; division by a zero point
separation is not used.

Complete source skinning follows every existing contact clock, including all
declared hold populations. Sources, policy, actor payloads, method archives and
observations are snapshotted and hashed. Mutation leaves a failed job visible.
An audit pass remains separate from full mesh intersections, contact forces,
between-clock collision, GPU/runtime playback and animator review.

## Integration with native fitting

`scripts/native_scene_fit.py` accepts `--surface-contact-policy surface-policy.json`.
This is an additional final acceptance filter. Current point/surface fitting
does **not** optimize these new normal conditions; a failed filter remains a
failure instead of being promoted by successful point fitting.

`point_and_motion_constraints_pass` reports the original conditions separately.
When a surface policy is supplied, `native_constraints_pass` additionally requires
the surface conditions. `surface_contact_conditions_pass` and its result hash
are saved with the complete derived policy and observations. The derived policy
changes only its binding to the exported contacts file. Originals remain selected.

A resumed fit that already includes this additional policy must retain its
exact bytes. Omitting, changing or corrupting the archived policy is rejected;
original source-rate arrays and clip replay remain required. New conditions may
be explicitly added to an older point-only fit, without altering its source
epoch or relaxing original constraints.

## Retained high-five diagnosis

The existing seed `[0, 0, 14712]` is predominantly weighted to the provided
index/ring finger-base tracks (about 0.35 each), with only about 0.098 weight on
the hand track. This is rig metadata, not anatomical annotation. At the retained
contact pose, the declared hand-subtree surface extends about 51.7 mm past that
seed along its winding-derived normal. It is not an outer support point of that
entire selected hand region.

| Saved motion | Point condition | Normal opposition error | Source / target facing-side projections |
| --- | --- | ---: | ---: |
| Unchanged source | Fail | 44.982° | -195.755 / -129.347 mm |
| Point-only correction | Pass | 39.577° | -27.589 / -27.623 mm |
| Surface-guided correction | Pass | 39.162° | -25.518 / -21.023 mm |

All three fail the explicit prototype surface policy. Both normals in the
latest correction point away from the source-to-target contact direction.
The small point gap should not be presented as a usable high-five. This changes
the next action: review/select the intended contact patch and normal meaning
before further fitting or collecting training labels. Earlier measurements and
their failed outputs remain retained; the existing seed is not silently replaced.

A real fitting composition replays the 35-iteration clip without adding motion
steps. Original point/motion conditions pass, while the new surface filter makes
native acceptance fail. Its four start/final exports match the preceding clip
byte-for-byte, original cap arrays remain exact, and full geometry and normal
observations match retained verified evidence. Independent scalar incident-face
accumulation confirms the three diagnostic cases; 82 audit files and 308 fitting
files are rehashed. Shared skin samplers remain used.

All 423 focused model-free regression cases pass, including 28 new audit,
coordinate-transform, reliability, budget, mutation and fitting/resume cases.

Local evidence: `reports/native-palm-orientation-diagnosis-v1/`,
`reports/native-surface-contact-development-v1/verification-v1/`,
`reports/native-surface-contact-fitting-v1/high-five/verification-v1/` and
`reports/native-surface-contact-validation-v1/`. Character/study payloads remain
excluded from the public repository. Public CI covers the new audit and fitting
integration on Linux and Windows. No training, anatomical approval or release
approval is inferred.
