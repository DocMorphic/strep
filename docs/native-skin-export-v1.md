# Weight-conditioned export and partner surface proposals

`scripts/native_skin_export.py` creates a separate GLB with weights prepared for
Godot's unsigned-16 skin storage. It retains the original file, animation data,
joint bindings, vertex positions, topology and other scene metadata. This is an
optional export transformation, not a change to the source rig or checkpoint.
The output is never automatically selected or approved.

```powershell
.venv\Scripts\python.exe scripts/native_skin_export.py character.glb reports/weight-export
```

A fresh output directory is required. The job snapshots the source and methods,
appends new Float32 weight accessors, and verifies that the entire original binary
payload remains its prefix. Restoring the weight references and removing the
appended accessors/views must recover the exact original scene document. Source
and archived method hashes are rechecked before completion; mutation leaves a
failed job visible. Export completion alone does not establish fidelity.

## Encoding method and measured scope

`skin_weight_grid.condition` normalizes each four/eight-influence row, assigns
65535 integer units with deterministic largest-remainder rounding, and preserves
zero influences. Float32 accumulation can otherwise trigger loader normalization
that loses several units. A bounded adjustment of the largest coefficient avoids
that case. The modeled loader and storage encoding must leave at most one unit
of sum error, and each coefficient may change by at most 2/65535. Unsupported or
invalid weights fail rather than silently exceeding these bounds.

On the retained high-five rig, both actors have 18,056 vertices and eight weight
slots. Each export adjusts 70 rows by one Float32 ULP. Encoded sums are exact for
18,026 vertices and one unit short for 30. The largest coefficient change is
about 0.000011914. These figures describe this rig, not a universal accuracy bound.

Two actual headless Godot 4.7.2 studies retain the previous explicit geometry
clocks (0, 2.5 and 4.9666666984558105 seconds), world plane, contact limits and
0.1 mm imported/source skin tolerance. Ordinary import and native-resource
authoring seeks both pass sampled skin and point-contact conditions. Full mesh
geometry still fails because the hands intersect; neither study passes overall.

A separate raw-slot accumulator does not renormalize observed imported weights.
It rechecks all input, snapshot, method, executed-script and engine-output
receipts, then reproduces contact observations and full posed skin at each
geometry clock: 216,672 vertex observations across the two studies. It also
compares those observations against the **original unconditioned source**, not
only the newly exported mesh. The maximum original-reference error falls from
about 0.1367 mm in the previous export to 0.02760 mm in ordinary import and
0.02758 mm in native authoring. The conditioned native mesh differs from the
original by at most 0.001363 mm at these clocks.

Native reference sampling still uses the shared rig sampler. This is headless
CPU reconstruction and manual authoring seeking, with three sampled clocks; it
does not verify GPU rendering, runtime event dispatch, continuous collision,
other rigs, held-out actions, animator cleanup time or release quality. The
original mesh, prior failing exports and all local study outputs remain retained.

## Surface proposal groundwork

`scripts/native_partner_surface_rows.py` builds local scalar constraints from
complete actor triangle populations at the explicitly declared geometry clocks.
Every detected triangle intersection contributes all nine vertex-pair
separation inequalities along a local axis. Bidirectional containment queries
add penetrating-vertex constraints against barycentric target-surface points
when a target is a closed volume. Referenced vertices near explicit world planes
also contribute rows. A resource-budget overflow rejects the complete query;
it does not return a truncated subset. Object primitives are explicitly rejected
by this prototype.

`scripts/native_surface_lift.py` converts those affine scalar constraints to the
existing vector-norm representation. An offset computed for the declared trust
box makes the resulting norm residual equal the scalar clearance deficit
throughout that box. This is an affine algebra result, not a bound on nonlinear
poses or skin motion.

The surface rows and lift are proposal helpers. They are not yet connected to
the motion solver. Axes and barycentric witnesses must be rebuilt after edits,
and complete decoded contact, source-rate and mesh audits must remain the
acceptance authority. Synthetic tests cover crossing/coplanar triangles, full
closed-volume containment populations, budget/incomplete-population rejection,
and exact scalar/norm agreement throughout sampled trust boxes. Neither helper
establishes collision freedom or motion quality.

On the retained staged high-five, the query includes all 36,108 triangles and
18,056 referenced vertices per actor at the same three clocks. Its 451 crossing
pairs produce 4,059 inequalities; containment adds 345/242 penetrating-vertex
witnesses. All 4,646 rows fit within the explicit 20,000-row budget. The deepest
gap is -21.495 mm, or a 21.995 mm deficit against the proposed 0.5 mm clearance.
No motion has been changed and no solver run has repaired these witnesses.

All 380 focused regression cases pass in the model-free environment, including
22 new weight-export and surface/lift cases. Both new suites also run in the
public Linux and Windows source-check workflows.

Local evidence is retained under `reports/native-skin-export-development-v1/`,
including `verification-v2/` (a first verifier attempt stopped on an invalid
local path lookup before producing a result), and
`reports/native-skin-surface-validation-v1/`. Generated character payloads and
machine-specific evidence remain excluded from the public repository.
The complete surface query is retained separately under
`reports/native-partner-surface-rows-development-v1/`.
