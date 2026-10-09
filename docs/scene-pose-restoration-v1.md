# Direct native pose restoration

`scripts/scene_pose_restoration.py` diagnoses the remaining failures in the
authored-height box lift. It reconstructs one pose from the immutable V17 native
motion and holds the adjacent candidate keys fixed. It does not replace the
full clip, claim a usable grasp, or approve any release capability.

The pose model retains all 77 joints, 18,056 skin vertices and eight influences
per vertex. Editable local rotations use the original 40-degree body budgets,
8/5-degree finger-base budgets and 12-degree distal budgets relative to the
previous motion. The root retains its original XZ/heading and 220 mm lift bound.
Rotation budgets constrain the vector norm, not its individual components.

The direct inequalities include:

- The original 4.99 mm working point targets, derived from the authored tolerance
  and saved numerical margin.
- Actual area-weighted normals of the skinned triangles adjoining each anchor,
  under the original 10-degree solver limit.
- Original 2 mm floor clearance and complete vertex/prop clearance. The saved
  intentional-contact policy removes only the extra hand/foot buffer for the
  named prop at the original contact keys. Physical penetration remains a failure.
- Every joint's original 220 mm displacement bound against each of raw, limb
  and previous motion.
- Original 1.5 m/s added joint speed against each reference and both available
  adjacent candidate keys on the unchanged 30 Hz clock.

Small additional numerical headroom tightens the solve; acceptance limits remain
unchanged. SLSQP operates on normalized control variables with analytical
rotation-norm rows and Torch derivatives of the actual FK and skin. Constraint
population maxima express the intersection of all original inequalities.
`--grouping native-joint` partitions the complete skin by each vertex's dominant
joint and separates body bounds per joint, while retaining all eight skin
influences for motion and derivatives. No vertex or reference is removed; the
minimum grouped slack equals the original global slack. Tests check this
equivalence. The actual grouped pose has 298 geometry/body rows plus the local
rotation-norm rows.
The optional `restore_then_slsqp` strategy first minimizes violated inequalities
with bounded trust-region least squares and a declared seed regularizer. A
stationary residual or solver success does not establish feasibility.

Independent SciPy/NumPy FK and complete LBS recheck point positions, actual
triangle normals, complete prop/floor vertices, all reference positions and
neighbor speeds, and original rotation/root budgets. The runner archives methods
and hashes inputs, saves the seed audit, verifies point/normal derivatives by
finite differences, retains restoration and final stage outputs, and rehashes
inputs/implementation on completion. It holds the shared OS worker lock from
preflight through result publication. Fresh failures have terminal failure
receipts; existing output folders are never overwritten.

Example on a completed local V17 study:

```powershell
.venv/Scripts/python.exe scripts/scene_pose_restoration.py reports/box-lift-authored-height-v1 reports/my-fresh-pose-study --frame 72 --iterations 100 --seconds 300 --strategy restore_then_slsqp
```

This CLI needs the acquired native skin and completed study; the public repository
contains source and methodology, not those third-party payloads. Run heavy
experiments under the unchanged owned-process guard: 3600 seconds, 7 GiB process
tree RSS and at least 600 MiB available system memory. The per-pose solve also
has its declared wall-clock limit. These experiments perform no inference or
training.

## First actual attempts

The first attempt stopped before optimization because an anchor audit returned a
NumPy Boolean that JSON rejected. The failure remains in
`reports/box-lift-pose-restoration-v1/`; the conversion and a serialization
regression are fixed before retrying in a fresh folder.

The direct-only experiment in `reports/box-lift-pose-restoration-v2/` completes
both selected poses in 146.844 seconds with 633,163,776 bytes peak process-tree
RSS. Both solvers reach their 100-iteration limits; neither pose passes.

| Pose | Hand errors, left/right | Normal errors, left/right | Box vertex depth | Raw-relative joint displacement | Added speed to fixed neighbors |
| --- | --- | --- | --- | --- | --- |
| 72 | 5.866 / 16.959 mm | 10.568 / 11.091 degrees | 3.434 mm | 183.131 mm | 1.579 / 1.635 m/s |
| 98 | 5.334 / 20.834 mm | 10.498 / 12.277 degrees | 5.376 mm | 221.983 mm | 1.515 / 1.482 m/s |

The source's frame-72 vertex depth is 25.715 mm. Its reduction does not outweigh
the remaining contact, orientation and speed failures. Floor and local
rotation/root budgets pass the isolated checks; this does not establish planted
feet or preserve the full clip's support/slide constraints. Independent skin
replay differs by less than 0.081 micrometres in either candidate.

The restoration-first experiment in `reports/box-lift-pose-restoration-v3/`
completes in 181.469 seconds with 642,375,680 bytes peak tree RSS. Both trust-region
stages report numerical termination but neither passes independent checks.
Subsequent SLSQP also fails: frame 72 stops with an LSQ-subproblem iteration
error; frame 98 reaches its iteration limit. Retained final vertex depths are
4.693 / 9.157 mm, hand errors 7.568/5.981 and 12.439/9.902 mm, and normal errors
11.739/10.129 and 12.904/11.303 degrees. Frame 72 also violates a rotation norm;
frame 98 retains 220.560 mm raw-relative displacement. Added speeds pass in both
final attempts. These mixed outcomes do not repair the clip.

All four completed attempts' original input, archived method, protocol, pose and
intermediate restoration-pose hashes independently recheck. Their NumPy skin
replays agree with Torch within 0.085 micrometres. The grouped direct experiment
in `reports/box-lift-pose-restoration-v4/` finishes its supervisor in 1222.25 seconds;
both poses stop at their explicit 600-second solve limits and remain failed.
The overall resource guard is unchanged. Subsequent complete-replay protected
steps and their measured limitations are documented in
[guarded native contact repair](guarded-pose-restoration-v1.md).

## Portable source validation

Sixty-eight distinct focused checks pass: 41 model-free checks and 36 native
Torch checks with nine overlapping residual checks. The 41 model-free checks
also pass in a separate source copy containing no `vendor/` folder.

The prior hosted CI shard fails on both Windows and Linux because joint-offset
contacts read downloaded Kimodo definitions despite having a supplied skin's
joint names. `scene_constraints.joint_point` now uses that supplied rig order,
checks distinct names and matching joint/clock populations, and propagates the
mapping to partner targets. A reordered nonzero-pose regression forbids vendor
lookup. Calls without a skin retain the existing native-metadata path.
This fixes an actual source-only checkout failure, not just its test expectation.

The CI inventory now declares 403 model-free Python modules and 39 Node suites,
partitioned 101/101/101/100. Native restoration checks run in the separate CPU
Torch job on Windows and Linux. Hosted verification of these changes is pending;
the earlier failing run is not described as green.

All saved attempts are diagnostic and unapproved. A failed local solve is not an
infeasibility proof. A passing isolated pose would still require full-clock
correction, protected support/slide checks, between-key and imported geometry
evaluation, anatomy/dynamics review, and human motion/cleanup evidence. The
single goal continues to cover arbitrary actions, scene and partner interaction,
editing/style, rigs, transitions and engine delivery; all fourteen release
capabilities remain unapproved.
