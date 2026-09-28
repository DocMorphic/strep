# Experimental contact calibration

These development probes change the authored surface binding. They do not pass the original fixed-point condition, approve a grasp animation, or change Studio defaults or release gates.

## Alternate fixed point

`study_joint_grasp_patch.py --left-contact-vertex 7159` preserves world targets and original edit limits while explicitly replacing vertex 14712 and its adjacent-triangle normal. All three starts fail full rigid-hand clearance: minimum signed distances are -3.817836, -3.850409 and -3.814302 mm. No arm projection ran. The original fixed-point failures remain separate.

The study snapshots its implementation and checks input/source hashes. The completed independent audit reconstructed the three shape records, six placement records and three alternate-binding joint records. The binding helper subsequently gained region support; the historical audit belongs to the saved implementation. The auditor deliberately rejects a replay against changed working-tree source. Retain the matching implementation when reproducing historical evidence.

## Declared region probe

`probe_sphere_region_support.py` enumerates anchors in the existing geometric palm region, retaining only triangles whose positive skin influences belong entirely to that hand's subtree. Collision checks cover all vertices wholly influenced by the hand subtree. This is an isolated rigid patch, not the full body or a projected skeleton pose.

Each anchor is placed 2.1 mm outward from the existing sphere grip target. Full-hand clearance must reach 2 mm, with the existing 1 micrometre numerical allowance. Three region vertices must lie within 2–3 mm of the sphere, within 20 mm of the grip target, at least 6 mm apart, span at least 25 square millimetres, and have a centroid within 5 mm of the grip target. Region normals use the area-weighted triangle sum. These criteria define a new contact condition; anatomical approval is pending.

| Probe | Placements | Full-hand clearance passes | Distributed region passes |
| --- | ---: | ---: | ---: |
| Left, centered normal | 191 | 0 | 0 |
| Left, centered plus 9.5-degree tilt ring | 1,719 | 3 | 1 |
| Right, centered plus 9.5-degree tilt ring | 1,701 | 2 | 0 |

The tilt ring uses eight azimuths at 45-degree intervals, inside the original 10-degree normal limit. The sole left candidate uses anchor 14814, tilt 9.5 degrees and azimuth zero. Its measured hand clearance is 2.004885 mm; contact vertices 7071, 7073 and 7146 span 32.966965 square millimetres, have minimum separation 7.595048 mm, and centroid error 2.779658 mm. These are generator-reported measurements: independent enumeration replay and actual bounded arm projection remain pending. The right-hand failure remains unresolved.

The result's `desired_region_normal` is the original authored normal. To project a tilted candidate, apply its selected `rotation_from_source` to the measured source region normal; do not substitute the untilted field. No candidate has yet been applied to the skeleton. Full-body/object/floor validation, self-collision, temporal quality, human review and all release capabilities remain open.

Local evidence is retained under `reports/grasp-contact-calibration-v2`, its `-audit` sibling, `reports/sphere-region-support-v2`, `reports/sphere-region-support-v3`, and `reports/sphere-region-support-right-v1`. The earlier `sphere-region-support-v1` preflight failure is also preserved. Asset-derived reports and source snapshots remain excluded from Git.

## Reproduction

These commands require the existing local fixture, restoration seed and separately acquired licensed model/skin dependencies. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/study_joint_grasp_patch.py reports/grasp-shape-seeds-v2 reports/grasp-shape-placements-v1 reports/grasp-pose-restoration-v2 reports/new-contact-calibration --left-contact-vertex 7159
.venv\Scripts\python.exe scripts/probe_sphere_region_support.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-left-region --tilt-ring-degrees 9.5
.venv\Scripts\python.exe scripts/probe_sphere_region_support.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-right-region --tilt-ring-degrees 9.5 --hand RightHand
```

Focused tests validate binding isolation, rejection of invalid or other-hand vertices, declared-region membership, and contact spread/area/locality/clearance rejection. They do not establish whole-pose feasibility.
