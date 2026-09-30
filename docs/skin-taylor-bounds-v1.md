# Directional skin-motion bounds

The paired-character interval audit found one native span whose sixteen leaves
remained unresolved. Independent movement balls allow each vertex to move in
every direction, losing information about adjacent surfaces traveling together.
This diagnostic retains center velocity and bounds the nonlinear remainder. It
does not edit the motion, relax geometric tolerances or establish motion quality.

## Motion bound

`SkinTaylorBounds` evaluates the production GLB sampler at the interval center
and differentiates its local transforms analytically. World-transform derivatives
use the product rule through the entire hierarchy. Skin velocities use every
weight and inverse bind, including its homogeneous component; unskinned
primitives preserve their mesh-node transform. Constant scene placements rotate
velocity and rotate/translate position.

Each interval must lie inside one span of the union of native channel clocks.
Intervals crossing a knot are rejected because velocity can change there.
Changing STEP channels, cubic interpolation and animated scale drift remain
unsupported. Local matrices must have exact affine bottom rows; accepted tiny
static scale drift is included in the operator bounds.

For normalized quaternion interpolation `q = r / ||r||`, let `c` bound the raw
norm below, and `d`, `e` bound the raw first and second derivative norms above.
Differentiating the normalization gives the conservative bounds
`||q'|| <= d/c` and `||q''|| <= 2e/c + 6d²/c²`. Rotation-matrix operator bounds
then follow as `||R'|| <= 2d/c` and `||R''|| <= 4e/c + 16d²/c²`.

For the sampler's small-angle NLERP branch, `d = ||b-a|| / duration`, `e = 0`
and `c = ||a+b||/2` after normalization and shortest-arc sign selection. For its
SLERP branch, writing raw interpolation as `a*cos(u*theta) + v*sin(u*theta)`
allows the two-column Gram matrix's eigenvalues to bound all three quantities.
The code uses the same branch threshold and normalized keys as the sampler.

For a parent linear-transform bound `M`, first derivative `D`, second derivative
`E`, and position acceleration `P`, with local stretch `S`, derivative bounds
`d`, `e`, translation length bound `L` and translation speed `U`, propagation is:

```text
M_child = M*S
D_child = D*S + M*d
E_child = E*S + 2*D*d + M*e
P_child = P + E*L + 2*D*U
```

Local translation is linear within a native span. Weighted skin acceleration
bounds yield a per-vertex remainder radius `0.5 * acceleration_bound * h²`, where
`h` covers both endpoints from the computed center. Node bounds receive relative
inflation and outward rounding; remainder radii include 1e-10 m padding.
These allowances are explicit floating-point precautions, not exact arithmetic.

## Synchronized triangle projections

For any fixed direction, compare all nine pairs of triangle vertices at the
same time. A lower bound on the projected separation is the center difference,
minus `h * abs(projected relative velocity)`, minus both remainder radii times
the direction norm. Taking the minimum over all vertex pairs bounds the two
triangles' separation in that direction for the full interval. Both orientations
are tested using the existing center-geometry axes.

Subtracting velocities before projecting retains cancellation of shared motion.
Independent forward/backward speed balls cannot do this. The original swept
boxes, candidate budget, batching and 1e-8 m tolerance remain unchanged. The
projection reserve also accounts for velocity magnitude times interval radius.
Only checking and separating every broad-phase candidate permits a surface
separation bound. Unchecked pairs remain unresolved.

## Validation and limits

Analytic fixtures exercise linear translation, tiny-angle interpolation on both
sides of the branch threshold, sign-flipped rotations through 180 degrees,
moving hierarchical joints, blended skin, inverse-bind drift, static scale,
clamped channels and native-knot rejection. Finite differences check center
velocity and rotation acceleration; dense decoded replay checks remainders.
Projection tests include common travel, approach, an intersection between
separated endpoint poses, acceleration uncertainty, random bounded trajectories,
actor/winding/rigid-transform invariance and scene velocity placement.

`audit_skin_taylor.py` snapshots its implementation and binds input GLBs and
placements by hash. It compares both methods on identical swept-box candidates
and checks 17 actual decoded poses per actor per requested interval against the
Taylor remainder. Replay tests implementation consistency; finite samples cannot
prove continuous correctness. The runner neither repeats containment checks nor
replaces the original crossing observations or adaptive partitions.

```powershell
.venv/Scripts/python.exe scripts/audit_skin_taylor.py reports/<protocol>.json reports/<fresh-output>
```

No self-collision, continuous volumetric clearance, animator approval or general
interaction-quality claim follows from this diagnostic. The retained crossing
witnesses still require actual motion repair.

## Completed saved-clip comparison

The unchanged larger-trust paired clips and placements were evaluated on all
74 adjacent native intervals from 0 to 3.6666667461 seconds, plus all sixteen
previously unresolved leaves of native interval 37. The actual native-clock
union, original placements, input hashes, method snapshots and exact leaf
partition were checked after the completed run. It took 227.66 seconds locally.

At the native-root level, movement balls separate 53 intervals and leave 21
unresolved. Taylor projections separate 54 and leave 20 unresolved; all twenty
hit the unchanged 20,000-candidate budget. This standalone comparison does not
subdivide, so these numbers must not replace the earlier adaptive study's
63 separated roots, ten crossing roots and one unresolved root.

For the sixteen previously unresolved leaves, all original ball queries remain
unresolved, while Taylor projections check and separate every one of the
10,836 candidate pairs. The minimum tested separation margin is 2.470124 mm.
The first single-leaf probe also reproduces its old 685-candidate population,
then checks all 685 with a minimum Taylor margin of 2.716882 mm.

Across the full 90-interval comparison, 3,060 decoded actor poses and 55,251,360
vertex observations stay inside their Taylor remainder bounds. The largest
observed error/remainder ratio is 0.314832. These are development replay
observations, not independent animator evidence or an exact continuous proof.
All ten native roots with independently confirmed crossings remain unresolved
in this projection-only run; their original crossing evidence remains valid.

The complete minimal suite passed 845 tests before the final random-axis
fixture was added; all 17 Taylor tests then passed, including that additional
fixture. The CI list now contains 846 tests in total.

Local immutable evidence:

- Full result: `reports/skin-taylor-full-audit-v1/result.json`, SHA-256
  `9dbd0306e3b9784e123958654e4344d3d083f969accb32aac2d5cfed95452e12`.
- Protocol: `9405b53ac1ee810e2bdebefacff004db6df69cde7b38c37f827ab145728e2813`.
- Interval results: `89256d4967606ddd67908c097992dea17ff48dc8e82a8bb4b1a87521c9c939dc`.
- Checked summary: `reports/skin-taylor-full-summary-v1.json`, SHA-256
  `5c7e912ec26760225186d694c49d70baece6ab5b60c02c0c4c9f6af345eabfdc`.

The next correction experiment should use actual triangle-crossing witnesses,
including the existing crossing missed by vertex containment, while retaining
motion, contact and edit limits. Tighter separation bounds improve evaluation;
they are not a reason to publish an intersecting candidate as corrected.
