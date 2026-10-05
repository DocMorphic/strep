# Completed reserved static object import

The serial audit queued in `docs/reserved-object-engine-v1.md` completed on
**2026-10-05 at 01:03:50 UTC**, after the exact repair-replay predecessor exited
successfully. All five reserved static geometries pass actual headless Godot
4.7.2 import with compression disabled.

Local result: `reports/release-object-reservations-engine-v1/result.json`.
SHA256: `e31e59a2a6dd90c2aa63698c2a47be4536bbeb6020522379680bae53153b5b71`.
This is completed engine evidence, distinct from the earlier fifty synthetic
source checks and the original construction's primitive-distance checks.

| Object | Imported triangles | Maximum normal-component error | Maximum placement error |
|---|---:|---:|---:|
| box-tall | 12 | 1.5259254723787308e-05 | 5.9604643443123e-10 m |
| box-flat | 12 | 1.5259254723787308e-05 | 3.5762786898541066e-09 m |
| sphere | 2048 | 9.563565254211426e-05 | 7.033348070617507e-09 m |
| cylinder-tall | 128 | 5.46574592590332e-05 | 4.768371586472142e-09 m |
| cylinder-flat | 256 | 5.5223703384399414e-05 | 3.6954879711892374e-09 m |

Every triangle preserves its exact saved Float32 positions, allowing importer
vertex/index reordering and one consistent global winding reversal. All five
use that reversed winding convention. The complete population is **2456
triangles**, with **ten** observed placements: local origin and canonical
grounded position for every object.

The normal-component limit remained **1e-4** and placement limit remained
**1e-6 m**, both fixed before the engine executed. No threshold changed after
observing these errors. The sphere is close to the normal representation limit;
passing static representation does not establish precise dynamic contact normals.

The actual Godot script parsed and ran successfully. Native raw observations,
logs, method snapshots and failed/queued predecessor history remain local and
immutable. No motion, reachable grip, partner interaction, physics or GPU render
was tested. Five dimension sets across three convex primitive families remain
the scope; arbitrary/concave/deformable object generalization is unproven.
Task scenes, full held-out bindings, motion trials and human review remain open.
No release approval follows, and all fourteen release-evidence arrays stay empty.
