# Native endpoint sampling agreement

The retained kick restoration pilot exposed a preview/decoder discrepancy before
its solver could run. At 3.966666666666667 seconds, the scalar decoder compares
a Python float with the original Float32 final key, 3.9666666984558105. In the
pinned numerical runtime that comparison rounds into the endpoint's cell and
clamps. The former Float64 batch comparison instead interpolates. This can also
affect the initial endpoint and translation tracks.

The shared batch helper now evaluates the same scalar endpoint comparisons as
the existing decoder. Rotation and native scene translation previews use it.
Native clocks, quaternion keys, exported assets, decoder behavior, geometry
tolerances and source-rate limits stay unchanged. Exact native-key overrides
remain in the scene preview. This corrects the proposal model, not the animation.

Across the retained kick's **2,017 declared times**, the maximum preview/captured
world-matrix element discrepancy falls from **1.935170135e-9 to 4.440893e-15**.
The largest selected rotation-matrix discrepancy falls from **5.226190e-9 to
5.551116e-16**. Both 33-observation resource traces replay; their original
captured asset and matrix arrays remain retained. The first restoration's strict
surface comparison failure is also retained with its 71-observation trace; no
tolerance was loosened to get past it.

**127 affected checks pass locally**: 46 rotation/edit/export checks and 81
scene norm, surface, plane, storage and boundary checks. New endpoint tests cover
both Float32 and Float64 clocks, inside/outside rounding cells, antipodal
rotations, and actual exported scene rotation/translation tracks. Restoring the
old mask behavior makes three new cases fail; the Float64 comparison case still
passes. The existing timed-rotation suite now also runs in the focused Windows
and Linux contact/rig workflow. The complete focused workflow at
[cc756d6](https://github.com/DocMorphic/strep/actions/runs/38171024531)
passes **569 Python checks per OS**: 502 contact/rig, 35 lineage and 32 game
package checks, plus the offline editor suite. The full model-free source checks
remain pending; this is not a claim that all 465 declared Python modules pass.

Local records: `reports/kenney-kick-proxy-alignment-v1` / `v2`,
`reports/native-endpoint-regression-v1`, and
`reports/kenney-kick-temporal-restoration-v1` / `v2`. The corrected restoration
rerun retains the original source caps and full geometry decisions. It completes
after a last execution observation of 184.890 seconds, with all 198 resource
observations replayed. Its 112,505-row affine model retains 108,471 native rows
and 2,017 separate worst-floor guards as a 110,488-row hard prefix. The local
solver reports `PrimalInfeasible` after 16 iterations at a 0.02 control trust
fraction, returning no direction or decoded candidate. This concerns that local
model and radius; it is not global infeasibility of the action. A separate frozen
row-group diagnostic reproduces local infeasibility with only the 108,471 native
rows hard and floor guards soft. Keeping only edit/displacement bounds hard
yields an affine direction, but it predicts **149 failed native rows**. No clip
is exported from that diagnostic direction. All 204 resource observations replay.
Passive extraction of the original 68 failed rows finds 33 position-speed and
four position-acceleration rows with zero source caps; the original 1e-5
tolerance still applies. These source-preservation limits are not anatomical
calibration. The next study must begin with a feasible original and examine its
temporal representation and source-rate compatibility before adoption. No motion
selection, training target, engine/support/semantic/human-quality or release
approval follows from sampling agreement. See the preceding
[kick permission and clip screens](kenney-kick-root-fixed-v1.md).

Additional local records are `reports/kenney-kick-restoration-row-groups-v1`
and `reports/kenney-kick-rate-failure-clock-v1`. The latter extracts retained
arrays only; it does not rerun motion physics or establish global infeasibility.
