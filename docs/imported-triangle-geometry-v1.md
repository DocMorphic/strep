# Full sampled imported scene geometry

`scripts/imported_scene_geometry.py` consumes the unchanged simultaneous Godot
observations from the [imported-skin measurements](imported-scene-measurements-v1.md).
It rechecks the complete clock, source poses, skin functions, triangles, actor
placements and object tracks before using the existing full geometry evaluator.
It runs no model, edits no motion and substitutes no source-skinned poses for
imported skin. Raw quantized weights remain unnormalized; authored actor
placement is applied after skinning.

## Reproduction

With an existing terminal `--measure-skin` scene playback result, create a policy:

```json
{
  "schema": "strep-imported-scene-geometry-policy-v1",
  "producer_result_sha256": "SHA256_OF_THE_ORIGINAL_RESULT_JSON",
  "limits": {
    "penetration_m": 0.005,
    "depth_resolution_m": 0.000001,
    "surface_tolerance_m": 0.00000001
  },
  "planes": {
    "floor": {"normal_world": [0, 1, 0], "offset_m": 0}
  }
}
```

```powershell
python scripts/imported_scene_geometry.py reports/imported-reference-measurements-v1 reports/my-policy.json reports/my-imported-geometry
```

Use a fresh output directory and the local geometry dependencies. Optional
`--scene-id` selects whole bound scenes; it cannot remove samples, triangles,
objects or partner pairs within a scene. The original producer retains its
frozen implementation rather than being rebound to today's source. The new
audit independently validates its raw observations and saves its own method
snapshot. Changed input assets, missing evidence or unavailable geometric
conditions fail. Numeric archives have complete transport receipts; verifying
an archive alone grants no geometry or animation approval.

## Measurement contract

Every original shared sample and actual stored key is retained, including
closely spaced float32 keys. Each actor has 18,056 vertices, 36,108 oriented
triangles and eight influences. Analytic object queries bound penetration
across triangle interiors and test object-center containment in the complete
closed actor volume. Partner checks retain all candidate triangle crossings
and both directions of vertex containment. Every actor also meets every
declared plane check. Watertightness, winding and degeneracy remain explicit.

A conservative whole-mesh bounding-box rejection skips building the triangle
index only when every expanded triangle box is strictly separated. It still
reports all face populations and degenerates. Overlapping or near-touching
bounds retain the existing complete indexed checks and independent containment
tests; no candidate cap or sample reduction is introduced.

The 5 mm penetration limit is a development diagnostic, not a newly frozen
release gate. These are sampled surface/volume checks, not continuous collision,
self-collision, GPU-renderer, dynamics or naturalness certification. An outward,
watertight skin does not establish absence of self-intersections.

## Actual retained results

All four audits complete on the unchanged imported observations: 2585 actor
poses and 1407 object poses. Input/method hashes and all four numeric archive
receipts were independently rechecked after completion.

| Development scene | Shared samples | Full sampled geometry outcome |
|---|---:|---|
| Corrected V16 reference, seed 7103 | 261 | Pass: zero floor and bounded triangle/box depth; box center outside actor at every sample |
| Corrected V16 reference, seed 7104 | 261 | Pass: zero floor and bounded triangle/box depth; box center outside actor at every sample |
| Original lift, seed 11 | 885 | Fail: floor depth 8.996512 mm; 716 samples exceed 5 mm. Triangle/box depth is zero and box center remains outside |
| Original high-five, seed 11 | 589 | Fail: partner surfaces cross at 33 samples; maximum vertex containment depth 21.010368 mm. Floor depth is 6.233599 mm per actor |

The high-five's crossings span sampled times 1.091667–1.3 seconds. The complete
audit accounts for 83,505 candidate triangle pairs, including 15,334 proper
crossings; these counts are repeated pair/sample observations, not unique
collision events. Whole bounds reject 550 of 589 partner poses; the remaining
39 retain the full index path. Peak containment is actor B vertex 11363 inside
actor A at 1.216667 seconds. The combined partner/floor conditions fail at 503
shared samples. Floor checks fail at 490 poses per actor. All volume predicates
are available and no sampled faces are degenerate.

Both short references still pass their previously measured 1 mm point contacts,
but their imported-versus-source whole-skin displacement still exceeds the
existing 0.1 mm precision screen. Passing these geometry diagnostics does not
erase that separate failure. Neither reference is evidence of a natural grasp,
lift, high-five or held-out action performance.

The guarded reference audit takes 125.547 seconds with peak process-tree RSS
485,003,264 bytes; the longer audit takes 446.813 seconds with peak RSS
1,679,253,504 bytes. Both finish without triggering the unchanged one-hour,
7 GiB process-tree or 600 MiB available-system-memory guards. Failed earlier
longer lift fits remain retained without a completed candidate.

The focused model-free geometry/clock/skin suite passes 146 tests, including
corrupted-evidence rejection, complete topology/clock replay, partner overlap,
raw-weight placement and a forbidden source-skin fallback. CI declares 397
Python modules across four shards (100/99/99/99) and 37 Node scripts per OS;
declaring coverage does not claim a hosted run has passed.

## Next work

Investigate the quantized-weight whole-skin discrepancy with derivative exports
and actual engine playback while preserving original assets and acceptance
tolerances. Then resume the longer constrained lift and repair partner overlap.
Natural interaction, attachment, held-out rigs/actions, independent animator
review and cleanup-time evidence remain required. All fourteen release
capabilities remain unapproved and the single project-wide goal stays active.
