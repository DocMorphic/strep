# Shared-prop collision comparison at 60 Hz

The existing two-actor/two-prop native playback fixture has a sampled floor-depth failure at 60 Hz. Both bodies already enable continuous collision detection (CCD). Lowering its activation threshold fixes this specific recorded failure: cylinder depth falls from **63.229 mm to 1.000 mm**, sphere depth from **13.229 mm to 1.008 mm**. Both ordinary and reversed body order pass the unchanged **10 mm** discrete depth screen. This is a procedural engine integration result, not acceptance of a generated animation or a production collision profile.

Godot documents the CCD activation threshold and allowed penetration as fractions of a body's inner radius. The former controls when CCD runs, even when the body flag is enabled. This motivated an explicit threshold comparison; it does not prove CCD solves every collision. [Official ProjectSettings documentation](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html#class-projectsettings-property-physics-jolt-physics-3d-simulation-continuous-cd-movement-threshold).

## Matched experiment

The pinned Godot **4.7.2-stable** binary reports build `ed1daf0bf001b61586d9930840f2f1394092c079`; its SHA-256 is `c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643`. All three runs use the same authored binary source clock, six ownership cases, two native animated three-bone fixtures, cylinder/sphere geometry and inertia, gravity, friction, zero damping/restitution, root modes, grip targets, release velocity/spin derivation and physics rate. The original native ownership, receipt, transport, pose/root and contact-response assertions all execute again. Every run records the actual engine settings and both actual body CCD flags; comparisons reject unrelated changes in the tracked controls.

| Profile | CCD movement threshold | CCD max penetration fraction | Cylinder floor depth | Sphere floor depth | 10 mm screen |
| --- | ---: | ---: | ---: | ---: | --- |
| `engine-default` | 0.75 | 0.25 | 63.229 mm | 13.229 mm | Fail |
| `ccd-threshold` | 0.05 | 0.25 | 1.000 mm | 1.008 mm | Pass |
| `strict-ccd` | 0.05 | 0.01 | 1.000 mm | 1.008 mm | Pass |

The actual pinned engine echoes the baseline threshold **0.75**, penetration fraction **0.25**, position/velocity iterations **2/10**, stabilization approximately **0.2**, speculative distance approximately **0.02 m**, gravity **9.81 m/s²**, zero collision margin fraction and the fixture's existing **0.001 m** penetration slop. These are recorded binary results rather than assumptions about a documentation version. The additional penetration-fraction tightening provides no measured depth benefit in this fixture.

Each profile executes six cases: shared ownership, reverse body order, and four deliberate grip/clock/callback faults. Both positive cases have 269 records and twelve actions; all four fault cases are detected for every profile. Release velocity/spin, held/action pose and whole-step root checks retain their original limits. Maximum inter-prop sampled penetration upper bound remains zero. All six positive cases still fail exact physical event timing: maximum application delay **11.6667 ms**, below a 60 Hz step but greater than zero. Source events visit the authored times; ownership changes apply at the next fixed physics boundary. No times are rounded and no higher rate is substituted.

Snapshots retain their existing `assigned_before_force_integration` phase. Depth measurements cover recorded states, not a continuous collision certificate, settled final-pose guarantee, arbitrary moving geometry or held-prop collision response. No rendering, humanoid naturalness, animator rating or cleanup evidence is supplied. All quality/release approvals remain false.

## Reproduction and bindings

With the separately acquired pinned Godot binary and cached model-free dependencies:

```powershell
uv run --offline --isolated --no-project --python 3.10 `
  --with-requirements requirements-ci.txt python scripts/run_guarded_job.py `
  --worker scripts/study_scene_collision_profiles.py `
  --output reports/your-fresh-collision-guard --expected-rss-mib 512 `
  --stable-seconds 3 --admission-seconds 60 --max-seconds 600 --poll-seconds 1 `
  -- --output reports/your-fresh-collision-comparison
```

The study stores all raw engine output, source copies, request/result hashes and compile/runtime logs. `study_scene_collision_profiles.compare(paths)` independently reruns the existing numerical/ownership/receipt verification against each retained raw output, then checks matched scene, engine, methods and tracked settings. The ordinary single-profile command also accepts `--collision-profile {engine-default,ccd-threshold,strict-ccd}`; default remains `engine-default`. Legacy results without recorded collision settings remain replayable and are explicitly labeled `legacy-unrecorded`; they cannot substitute for the matched three-profile comparison.

Local comparison: `reports/scene-collision-profiles-v1/engine/comparison.json`. Individual result bindings:

| Profile | Result SHA-256 |
| --- | --- |
| `engine-default` | `c00091996469a0ef6b221ad383d811bc85b287a8170040a986bacc3eeb2cde69` |
| `ccd-threshold` | `c03176e3527385bd4bbfd97a2d45a8905b1dceb1784955f648421bcee5b3e49f` |
| `strict-ccd` | `88f8ed0b3d5c4027c9e1c8ad85467e8cec48cd0f89acfe7beba589f28d158571` |

The guard completes with exit zero in **12.625 s**, sampled peak process-tree RSS **214,781,952 bytes**. Independent policy replay verifies all **14** observations, protocol `b0638cddfdff0898dbcf24986588435f0dca7cb94833d166c4e0f0146a7fba1b`, trace `27bd374c9d0654e318f382229506ccddb64c0cc5ba0461ccfb1729ff5d9c4c5b`. The 512 MiB estimate plus 600 MiB reserve applies only to this small headless procedural study; full native correction and independent geometry audit admission remain **2 GiB plus 600 MiB**. Serial whole-study times of 2.219/2.094/1.844 s are single measurements including setup, IO and verification, not solver performance comparisons.

All **90 focused checks** pass in 2.46 s, including 23 new checks covering actual-setting completeness, nonfinite/boolean echoes, declared-setting drift, hidden iteration/stabilization/speculative-distance changes, detached profile values, wrong backend and disabled actual CCD. The complete source inventory is **417 Python modules / 41 Node suites**, with every prior entry and CI policy preserved. Hosted CI remains separate and pending. No Studio server restart, global user-project setting, model weight or original animation is changed. The next engine work is end-to-end scene/package integration and explicit physical timing handling, plus broader shapes and production character validation. The full project-wide goal and all fourteen unapproved release capabilities remain active.
