# Complete-clock Kenney ground scenes

Four unchanged development transfers were assessed as explicit one-actor scenes
with no invented point-contact targets. The declared plane is Y=0 and the
penetration screen remains 5 mm. The clock combines all original keys and the
versioned engine frame-population contract; no sampled subset or temporal
decimation is used. Every original mesh vertex and triangle is retained.

| Motion | Assessed times | Geometry-failing times | Peak floor depth (mm) | Start depth (mm) | End depth (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Crawl | 2,017 | 2,017 | 263.015 | 261.423 | 204.544 |
| Kick | 2,017 | 234 | 49.728 | 0 | 0 |
| Get-up | 3,033 | 1,771 | 662.259 | 629.567 | 0 |
| Run/roll/stand | 3,541 | 465 | 994.774 | 0 | 0 |

In total this covers **10,608 times** and **10,915,632 vertex position
evaluations**. The roll's peak is about 16.497 mm deeper than its original-key
peak of 978.276 mm. A key-only clearance test would miss that larger crossing.
The declared sampled clocks still do not certify continuous-time clearance.

Each scene also retains an explicit V1 recipe: root translation plus nine body
rotation tracks, 30 control components, 22-cm track/joint displacement limits,
30-degree rotation limits, three knots and frozen clip boundaries. All permitted
tracks have actual first/last keys at the common clip endpoints; those keys are
excluded from the editable set. The crawl and get-up fail the floor screen at
such a frozen endpoint. **No candidate under these exact permissions can clear
the entire requested floor clock.** Passing endpoint checks for kick and roll
is only a necessary condition; it does not establish overall solver feasibility.

An additional start-pose reach screen permits every skin joint to rotate
independently by any proper rotation, while allowing each joint origin to move
22 cm in the most favourable vertical direction. For joint-local vertex offset
`q`, the maximum possible vertical contribution is `p_y + 0.22 + ||q||`;
combine contributions with the original nonnegative normalized skin weights.
This relaxation is more generous than the actual coupled, bounded hierarchy.
The actual inverse binds have affine homogeneous coordinates exactly equal to 1.

For get-up, **27 vertices** still cannot reach the 5-mm floor screen under that
relaxation, with the lowest computed upper height **-74.037 mm**. The screen uses
an additional 10-micrometre numerical reserve. Separate scalar-influence
arithmetic and legacy first-key decoding reproduce all 1,029 bounds. This is a
conditional floating-point reach diagnostic, not interval certification. Under
the stated proper-rotation and all-joint displacement assumptions, boundary
permissions alone cannot repair that start pose within the current budget.
The original remains a measured failure; do not enlarge the budget to claim a
pass. Crawl has no such excluded vertex at time zero, which is only a necessary
reach check, not proof of feasible correction or support. Bound and replay
evidence is retained in `reports/kenney-plane-start-bound-v1` and
`reports/kenney-plane-start-bound-replay-v1`.

This evidence motivates [explicit boundary permissions](native-scene-boundaries-v2.md)
and a bounded correction attempt that retains the original clips. It does not
justify increasing correction budgets to force a pass, altering the character,
claiming planted feet or approving an interaction. No point-contact intent was
declared or verified by these scenes.

The first study wrapper stopped before evaluating motion due to a tuple/list
method-manifest assembly error. Its failed worker and resource record remain
saved. V2 corrects that assembly and completes all four scenes; its 68 recorded
resource observations replay with all archived bindings matching. Local evidence
is retained in `reports/kenney-ground-scenes-v2` and guarded/resource records
under `reports/central-hand-physical-v1`. Raw outputs, generated payloads and
downloaded assets remain excluded from public Git. Human/cleanup, force/balance,
engine playback, continuous-time and release approval remain incomplete.
