# Native scene geometry diagnostics

This read-only CPU audit measures all loaded actor triangles against every
declared object, every actor pair and explicitly authored world planes. It works
with arbitrary joint names, all supplied skin influences and the selected native
animation. Action categories and contact patches do not limit the surface queried.
It never selects a correction, changes an input clip or approves animation quality.

## Use

Install the model-free dependencies in `requirements-ci.txt` in a development
environment, or use an existing environment containing those packages. Models,
downloaded characters and study outputs are not bundled in the public repository.

```powershell
python scripts/native_scene_geometry.py contacts.json geometry-policy.json reports/my-geometry-audit
python scripts/native_scene_fit.py contacts.json permissions.json reports/my-proposal --proposal-model vector --geometry-policy geometry-policy.json
```

Each output directory must be fresh. The standalone audit and fitting job share
the existing single-worker lock. The fitting job evaluates its serialized final
proposal without recursively acquiring that lock. Geometry results are separate
from native contact/rate/edit results, and originals remain selected even when
both sets of sampled conditions pass.

An authored policy binds the exact bytes of a `strep-native-scene-contacts-v1`
file. This example uses a two-second clip; change its endpoint explicitly to the
actual shared duration and supply the real SHA256 digest:

```json
{
  "schema": "strep-native-scene-geometry-v1",
  "contacts_sha256": "SHA256_OF_CONTACTS_JSON",
  "clock": {
    "mode": "native-and-frame-populations",
    "times_s": [0, 1, 2]
  },
  "limits": {
    "penetration_m": 0.005,
    "depth_resolution_m": 0.000001,
    "surface_tolerance_m": 0.00000001
  },
  "planes": {
    "ground": {"normal_world": [0, 1, 0], "offset_m": 0}
  }
}
```

`explicit` clock mode evaluates only the listed sorted unique times, including
both exact clip endpoints. `native-and-frame-populations` adds every actor native
key, object pose key, contact boundary, and all twelve existing 30/60/120 Hz
populations at 0/.25/.5/.75 frame phases across the shared clip. Reports retain
the exact union and populations. Neither mode proves what happens between ticks.
The more complete population can be substantially more expensive on full meshes.

Planes are explicit half-space boundaries: permitted positions satisfy
`normal_world · position >= offset_m`, with a unit normal. An empty plane
dictionary declares none; the audit does not infer a floor from a character.
It queries every actor/object and actor pair without excluding hand or foot
patches. No conditions is unavailable, rather than a vacuous pass. Objects retain
the scene contact contract's rigid linear-position/SLERP pose interpolation.

## Surface and volume measurements

Original indexed and nonindexed triangle populations are decoded in the exact
`RigAsset.vertices` order across all primitives. No welding, seam repair or
topology changes are applied. Native animation, inverse binds, normalized skin
weights, all influences and actor placement determine the posed surfaces.

`triangle_primitive_depth.py` queries analytic boxes, spheres and capped cylinders;
preview tessellation is not used. Its depth is the greatest negative primitive
signed distance attained anywhere on the triangle. Vertices alone can miss an
object piercing the triangle interior. Sphere depth uses the closest triangle
point. For a box, depth d erodes each half-extent by d; for a cylinder it erodes
the radius and each half-height by d. Convex polygon clipping and radial closest
points test these depth levels, followed by bisection. Constructed witnesses are
checked against the independent analytic point-distance implementation.

Each face retains lower/upper depth diagnostics and a world-space witness, with
the resolution and floating-point reserve recorded. These are floating-point
calculations, **not rigorously outward-rounded interval or exact-arithmetic
certificates**. Coordinate magnitudes incompatible with the requested resolution
are rejected. Degenerate faces remain visible and prevent sampled approval.
Boundary/near/coplanar partner outcomes also prevent a sampled pass.

An object wholly enclosed in an actor can evade actor-surface penetration tests.
The object-center signed-distance check therefore stays separate. It requires
the original mesh to be closed, consistently wound and have positive outward
volume. Inside, near-surface and unavailable outcomes fail the sampled conditions.
This volume interpretation assumes meaningful closed geometry; self-intersections
are not checked or certified. Partner checks retain all triangle crossing records
and bidirectional vertex containment diagnostics. A passing vertex test cannot
override a crossing or uncertain surface outcome. The audit does not cover
object/object collision or actor self-collision.

For algorithm context, the primary
[Trimesh triangle API](https://trimesh.org/trimesh.triangles.html) documents a
separate closest-point routine used by the independent sphere replay. The
[Trimesh proximity API](https://trimesh.org/trimesh.proximity.html) documents
signed mesh distance used for containment. Runtime studies use pinned Trimesh
5.1.0; online documentation currently describes 5.1.1. The in-repository analytic
primitive method remains separately tested.

## Saved development observations, 2026-10-03

The preceding commit `41dff3d` passes all four hosted CI jobs in run
37099966188. This geometry study uses the same retained sphere and high-five
source motions and their vector proposals, unchanged object trajectories and
placements. Limits are 5 mm penetration, 1 micrometre depth resolution and
10 nanometres surface tolerance. The explicitly declared Y=0 plane is a diagnostic
hypothesis, not a calibrated floor measurement.

| Pair of matched cases | Declared times per motion | Sampled result |
| --- | ---: | --- |
| Sphere source / vector proposal | 5, including hold boundaries and midpoint | Both pass these geometry conditions |
| High-five source / vector proposal | 3, including exact 2.5 s contact time | Both fail the explicit plane conditions |

All 36,108 triangles per actor are included. The sphere motions have no measured
surface penetration into either sphere at these five times, and object centers
are outside the closed actor mesh. This does not resolve their existing contact
or rate failures. High-five pair surface and vertex checks pass at the three
times, while A penetrates the test plane by 7.071–8.938 mm and B by
11.477–12.130 mm. The proposal does not improve those plane outcomes. No result
establishes geometry at unsampled times, correct action semantics, game-engine
imported skin, animator quality, training admission or release readiness.

Independent replay accumulates all skin influences separately, decodes raw face
bytes, compares every saved sphere face against a different closest-point
algorithm, and recomputes plane extrema and partner triangle-box/vertex checks.
The first verifier mistakenly assumed the entire partner AABBs must be disjoint;
that failed assumption stays recorded. The fresh verifier checks all triangle
boxes and containment instead. The detailed local study and verification live
under ignored `reports/native-scene-geometry-development-v1`; they are not public
downloads. Automated fixtures additionally cover actual interior penetration,
enclosed objects, nested partners, missing geometry, moving objects, actor
placements, all clock populations, source mutation and fitting integration.

Fitting records both the original policy digest and a derived policy bound to
the exported proposal's contact JSON. Only that binding changes; clocks, limits,
planes, object geometry and actor placement retain their authored meanings.
No geometry result changes the existing solver objective or relaxes a constraint.
Full scene/continuous/imported-skin validation, self-collision, calibrated
geometry, human review and the broad project release matrix remain outstanding.
