# Foot pin correction before platform carry

Two bounded fits reduce position error on the existing translating/rotating platform fixture, but **both fail the authored 5 mm foot-target screen and worsen right-foot motion**. Neither replaces the source or gains quality approval. A global joint-rate guard reduces the clip-wide acceleration peak while still allowing a local foot jerk.

The reproducible experiment is:

```powershell
.venv\Scripts\python.exe scripts/study_carrier_support.py reports/scene-carrier-v1/input reports/carrier-support-v1
.venv\Scripts\python.exe scripts/study_carrier_support.py reports/scene-carrier-v1/input reports/carrier-support-rate-v1 --rate-guard
```

Outputs must be fresh directories. These commands require the earlier local fixture and licensed SOMA preview asset; the repository does not bundle them. Existing outputs are retained and must not be overwritten.

Both trials use the same 180-frame original clip, mesh, scene, explicit points, initialization and solver implementation. Each foot uses its lowest material vertex at frame 90, pinned to that position over inclusive frames 30–149. The editable window is 20–159; its boundary poses and all outside poses are held. Other support regions are disabled. The original box-lift hand/object interaction is absent from this platform fixture and is not constrained by this experiment.

The solver uses two stages of 60 iterations, the existing 40-degree rotation and 0–220 mm root-lift budgets, sparse eight-weight skinning and physical bounded root coordinates. Both stages in both trials hit their iteration limit without convergence. The unguarded fit took 8.11 seconds / 135 evaluations; the guarded fit took 42.62 seconds / 195 evaluations. These are fitting times, excluding export and auditing. Only the runner changes between implementation snapshots, to expose the guard flag; numerical solver files are identical.

Independent full-mesh export measurements use 717 quarter-frame times across the clip, including 477 times per foot within the requested interval. These are fixed material points, not whichever vertex happens to be lowest at each sample.

| Measurement | Source | Pin fit | Pin fit + global rate guard |
|---|---:|---:|---:|
| Left foot maximum target error | 17.698 mm | 6.936 mm | 5.487 mm |
| Right foot maximum target error | 32.061 mm | 14.361 mm | 17.571 mm |
| Left / right samples above 5 mm | 380 / 242 | 39 / 58 | 37 / 73 |
| Left foot p95 point speed | 0.04154 m/s | 0.03553 m/s | 0.04480 m/s |
| Right foot p95 point speed | 0.04924 m/s | 0.05950 m/s | 0.06114 m/s |
| Right foot maximum point speed | 0.06835 m/s | 0.26767 m/s | 0.24667 m/s |
| Whole-clip maximum joint acceleration | 44.7182 m/s² | 45.8332 m/s² | 43.9895 m/s² |

The right-foot joint's angular-acceleration peak also rises from 10.16 to 103.55 / 89.25 rad/s². A lower whole-body maximum therefore does not establish locally preserved dynamics. The guarded solver's reference ceiling is the largest rate anywhere in the original body; it is not a per-foot or surface-point ceiling.

Actual maximum rotation edits are 14.970 / 11.095 degrees and root lifts are 5.492 / 7.113 mm. Both remain within the unchanged budgets. All 160 outside-window export samples, including the six adjoining fractional samples, preserve the mesh within 0.081 micrometres. Sampled full-mesh ground and platform depth are zero. Carrying the candidates onto the moving platform retains the measured object-relative foot errors and speeds; carry does not repair them.

Actual Godot checks pass 407 pose observations per candidate (814 total), two authored events each, four callback mutation rejections each, automatic/reverse playback and unload. Maximum actor matrix component error is 8.94e-7, with platform error 1.80e-7. Native export roundtrips retain all eight skin weights. No browser/HTTP or human review is claimed.

Evidence is retained in `reports/carrier-support-v1` and `reports/carrier-support-rate-v1`: hashed protocols and implementation copies, original input hashes, optimizer records, native target errors, NPZ/BVH/GLB outputs, per-joint rates, full exported window checks and platform-coordinate audits. A focused regression test deliberately inserts a between-key error invisible at native frames and verifies that the audit reports it. Passing export, preservation or engine checks does not approve the motion.

The next solver change should constrain individual requested foot trajectories at the exported sampling rate and measure their angular and linear behavior, including approach/release intervals. It should preserve the existing target tolerance and edit budgets, compare against both retained candidates, and report infeasibility rather than compensate with a looser global threshold. Sole orientation, balance reactions, forces, continuous collision, other motions/rigs and developer/animator review remain unproven. This is development evidence on one authored fixture; all fourteen release capabilities remain unapproved.
