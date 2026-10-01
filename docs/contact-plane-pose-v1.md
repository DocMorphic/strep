# Distributed hand-plane contact-pose experiment

The shared-marker experiment placed the anchors 1 mm apart but left about
18.455 mm partner penetration at the meeting pose. The selected marker is
mostly influenced by the index, middle and ring finger bases. Matching this
one point and its local normal does not determine the rest of the hand.

This follow-up keeps that explicitly authored target and fits the surrounding
hand surface before attempting another whole-trajectory correction. It does
not replace the old frozen-contact benchmark or approve the new condition.

## Surface selection and proposal

For each hand, sum all eight skin weights belonging to the hand joint or any
descendant. Seed vertices have at least half their weight in that hierarchy.
Include every triangle touching a seed, then all its vertices, so blended seam
vertices are retained. On this rig that selects 2,872 vertices and 5,717
triangles per actor. This is an explicit hand region, not a whole-body partition.

The fixed plane passes through the authored midpoint and uses its original
facing axis. The two hand regions should occupy opposite closed half-spaces.
Linear triangle interpolation stays in the same half-space if all three
vertices do. A failed plane proposal does not prove collision or infeasibility;
separated nonconvex surfaces need not admit this particular plane. Conversely,
passing selected-region planes alone does not approve the rest of either mesh,
self-collisions, contact anatomy, or the moving clip.

Each actor has 66 controls: upper arm, forearm, hand and nineteen finger joints,
with one native-key correction peak at the meeting time. Original-reference
budgets stay at 45 degrees for the arm chain; finger budgets are 8 degrees for
the thumb base, 5 for other bases and 12 for distal joints. Extra arm controls
are limited to 15 degrees. Conservative component bounds also account for
already-used original edit angle. Export independently checks every budget.

Each actor receives at most 80 least-squares evaluations. Residuals include
anchor error divided by 10 micrometres, normal-vector error divided by 0.05,
positive plane excess divided by 1 mm, and normalized controls times 0.001.
These are proposal weights, not acceptance thresholds or a constrained-solver
convergence guarantee. The original authored contact screen remains unchanged.

## Independent validation

Decode both exported GLBs and check native channel clocks, unchanged root and
unselected channels, exact outside-window motion, and original per-joint budgets.
Measure the authored contact screen and original four motion-rate cap groups.
At the meeting time, query complete body triangle candidates and both full
vertex-depth directions. A contact-pose failure must be resolved before treating
a new temporal envelope as a solution. This experiment does not run another
53-time geometry audit or approve any candidate for Studio.

## Measured outcome

Both fits exhaust their 80-evaluation budgets; convergence is not claimed.
Independent exports preserve channel clocks, root/unselected channels, outside
motion and every original joint-edit budget. The authored pose screen passes:
anchor errors are 0.060316 and 0.069518 mm, gap is 1.127609 mm, and target-normal
errors are 17.366292 and 17.426414 degrees.

| Contact-pose measurement | Input marker fit | Surface-plane fit |
| --- | ---: | ---: |
| Selected vertices beyond plane, actor A | 1,733 | 229 |
| Selected vertices beyond plane, actor B | 1,733 | 224 |
| Maximum plane excess, actor A | 54.898143 mm | 7.313934 mm |
| Maximum plane excess, actor B | 54.898169 mm | 7.118887 mm |
| Proper triangle crossings | 560 | 204 |
| Maximum full-vertex penetration | 18.454936 mm | 11.688520 mm |

These are same-pose comparisons, not full-interval improvement or acceptance.
The deepest remaining vertices are thumb-base dominated for actor A and
pinky-base dominated for actor B. Both full-body directions still contain
vertices more than 5 mm inside the partner. The selected-plane screen fails.

Original motion caps also fail: 374 position-speed rows, 144 position-acceleration
rows, 777 angular-speed rows and 205 angular-acceleration rows. Maximum excesses
are 0.113415 m/s, 5.043975 m/s^2, 0.845394 rad/s and 154.214544 rad/s^2. No candidate
is promoted. Temporal fitting, contact anatomy, self-collision and full-interval
geometry remain unresolved.

## Control-limit diagnosis and next experiment

A read-only follow-up finds nine actor-A fingers and six actor-B fingers within
1% of their additional angle limits. Thirteen and eleven joints respectively
have at least one component within 0.1% of its box bound. The conservative box
limits each component to the joint radius divided by sqrt(3), excluding some
valid rotations within that same radius. In particular an axis-aligned control
can use only 57.735% of its allowed joint angle.

Next replace the inscribed component box with joint-vector norm constraints,
keeping the original angle budgets and acceptance checks. This tests a concrete
parameterization limitation before changing contact targets or raising budgets.
Neither saturation nor this finite failed fit proves physical infeasibility.
The source fingers do animate elsewhere in the clips (maximum native-key
variation about 34.461 degrees); this is not evidence of globally frozen fingers.

All 998 model-free source tests passed. Rehashing verified 3,241 bound inputs,
74 archived methods and six outputs. Result SHA-256:
`df22696f236e371dbbc58482085f800b47bc17e089d15c699e10f288a9baa4fb`.
Read-only diagnosis SHA-256:
`ac75da12f5134c4274ba756a52b3e711a97fcd9e0dd658ba5a05c931808a1610`.
No training, held-out use, engine import or browser validation occurred. All
fourteen release capabilities remain unapproved.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_contact_plane_pose.py reports/shared-palm-meeting-v1 reports/<fresh-output>
.venv/Scripts/python.exe scripts/diagnose_contact_plane_pose.py reports/<fresh-output> reports/<fresh-diagnosis>
```

The hash-bound local rigs and prior studies are required and excluded from Git.
Six model-free tests exercise all eight weights, triangle seam closure, the
half-space interpolation property, rigid transforms, invalid input rejection,
and the distinction between a plane screen and full-mesh approval.
