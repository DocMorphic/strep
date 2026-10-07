# Native material witnesses for mesh clearance

`scripts/native_material_witness_guides.py` adds explicit vertex-to-triangle material-point guidance for existing native clips. It addresses the [previous guide mismatch](uniform-control-comparison-v1.md): lower all-pair guide error did not imply lower actual penetration. This is a local proposal component for arbitrary existing actions, not an action whitelist or animation-quality gate.

```python
from native_material_witness_guides import linearize_material_guides

guides = [{
    "actor_a": "A", "vertex_a": 56,
    "actor_b": "B", "face_b": 90,
    "barycentric_b": [0.2, 0.3, 0.5],
    "time_s": existing_native_time,
    "axis_world": [1.0, 0.0, 0.0],
    "clearance_m": 0.0001, "scale_m": 0.03
}]
model = linearize_material_guides(original_problem, controls,
    authenticated_decoded_worlds, guides)
```

Every descriptor has exactly those nine fields. Actor names must identify distinct existing scene actors. The source vertex and target face index use original rig/skin topology, including the original ordered triangle corners. Barycentric coordinates must be finite, nonnegative, at most one and sum to one within 1e-12; the API does not clip or renormalize them. Times must already occur exactly once in the original native clock, and directions must be explicit finite unit world vectors.

The target point is the barycentric combination of its three deformed, placed triangle corners. Both the source vertex and target point move with their supplied rigs. The gap is `(source - target) dot axis`; positive means separation in the declared direction. Each descriptor records all twelve source/triangle point coordinates. Face identity, barycentric weights and direction stay fixed during the local proposal. This is not a changing nearest-face query or a signed-distance function.

The complete population validates before any world query. Up to 4,096 guides and 96 original controls are allowed, with complete native-Jacobian and material-point/control budgets up to 60 million elements. Every original norm, cap, scale, control column and clock remains present. Guides share the entire native central or recorded one-sided stencil population; no extra world stencil is added for each guide. Observation callbacks receive copies, and failures leave the original problem method intact.

Exact repeated descriptors reject by default. An explicit boolean `allow_duplicate_descriptors=True` retains every repeated objective contribution in its original order. This makes weighting visible when different crossing records contribute the same inequality. It does not remove duplicate rows or silently change the original motion constraints.

Caller authentication of the original problem, decoded worlds and stored inputs remains required. The helper neither authorizes storage corrections nor scans complete scene geometry, changes library selection or adds Studio controls.

## Geometry extraction and sources

Trimesh's [official proximity API](https://trimesh.org/trimesh.proximity.html) returns a closest surface point, distance and original triangle ID. Its signed-distance convention is positive inside and negative outside, with a special near-surface tolerance region. Its [triangle API](https://trimesh.org/trimesh.triangles.html) provides barycentric conversion. Those primitives locate proposal witnesses; they are not a rig-constrained motion solver. Installed Trimesh 5.1.0 remains unchanged, and the experiment pins its proximity and triangle source hashes.

For the generated-fixture experiment, retain every crossing record at the seven previously declared original times. Each record contributes all nine pairs of its original triangle vertices, using the existing complete local triangle-axis family and stable support-gap choice. Query every original source vertex in both actor directions, in batches of 32. Every positive signed distance exceeding the unchanged original surface tolerance contributes its original nearest triangle and material point. The explicit direction points from the penetrating vertex toward that nearest point.

The extraction records raw barycentric values and only cleans rounding discrepancies bounded by 1e-12; reconstructed points must agree with the queried nearest point within 1e-12 m. This cleanup belongs to the recorded proposal extraction, not the public descriptor validator or geometry acceptance. The input meshes must retain original topology, closed consistent winding and positive volume. Self-intersection and continuous collision remain unproven.

## Tests and measured outcome

83 focused local tests pass with zero skips: 35 new material cases, 28 existing multi-time guide cases and 20 existing single-guide cases. They check actual placed/deforming meshes, reversed actor order, mixed units, original indexed triangle corners, every full native/material derivative column, boundary differences, resource/type rejection, observer isolation and explicit repeated-row contributions. The new suite is registered once in Linux/Windows CI; hosted success remains unverified.

At the genuine 53-choice Job, the experiment preserves all 90 controls, 30,450 original norms, 1,707 native samples, 1,673 geometry times and every original limit. It retains 964 material guide rows: 954 contributions from all 106 declared-frame crossing records, plus ten penetrating-vertex witnesses. There are no crossing/containment guides at the exact contact event or final frame. Every original central stencil is recomputed for the new material points; all 180 native stencil populations and the native Jacobian exactly match the previously verified same-point model.

The original-norm and uniform-increment variants both return `InsufficientProgress`, with no verified finite candidate. This is a numerical solver outcome, not proof of infeasibility. The event-preserving variant produces four actual exports:

| Fraction | Continuous scalar failures | Stored scalar/vector failures | Contact failures | Seven-frame depth, mm | Triangle records |
| --- | --- | --- | --- | --- | --- |
| Starting seed | 0 | 0 | 0 | 5.102497259 | 106 |
| 1 | 9 | 15 | 0 | 5.244799322 | 102 |
| 1/2 | 0 | 8 | 0 | 5.219763571 | 102 |
| 1/4 | 0 | 8 | 0 | 5.161567728 | 102 |
| 1/8 | 0 | 4 | 0 | 5.132031935 | 106 |

Every export passes original contact/reference/control/trust bounds and reduces its own actual guide loss from 7.11975335625. All fail original decoded motion, so none qualifies for a full scene scan. Reduced crossing counts coexist with worse maximum depth. Material-point guidance alone has not solved the misleading aggregate objective or the stored-motion discrepancy.

A separate original-context manual decoder reconstructs all 964 crossing/containment descriptors, material weights, finite triangle-axis choices, full point/gap stencils, all 90 native/material columns, 18 event and 72 uniform rows, strict ray diagnostics and every actual export with all seven frame queries. The first consumer pass failed because it paired descriptor rows with frame-grouped reports. A second pass matched every export but treated an unavoidable indirect module import as guide-API use. Both failed sources/reports remain retained. The final consumer completes the replay with explicit frame grouping and a call audit proving the indirectly imported partner-guide code was never invoked. Closest-point, signed-distance and collision kernels are shared, so this is not independent geometry arithmetic or solver optimality evidence.

Next, distinguish the numerical-stall outcomes from genuine motion feasibility and measure worst penetration and crossings separately from aggregate guide error. Any finite proposed correction still requires strict original norm/trust validation and actual stored export checks. A successful optimizer status or a falling proposal loss cannot replace those gates. Rejected geometrically worse proposals are retained as failures, not promoted through further storage repair solely for motion feasibility.

Raw studies remain immutable under ignored `reports/`. Original assets remain selected, all fourteen release evidence arrays remain empty and the full-project goal stays active. These results establish no production-anatomy, arbitrary-action semantics, engine, continuous-physics, human-review or cleanup-time approval.
