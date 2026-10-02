# Native support import and skin evidence

Two new standalone auditors verify completed native support studies in a local
Godot executable. They preserve the source and every proposal, including
failed motion. An import pass never overrides support or motion-rate failures.
The unchanged Kimodo checkpoint is not run or trained by either auditor.

## What is measured

`run_native_support_engine.py` binds the completed four-trial support study,
its source/draft, selected candidate, ancestors, archived methods and outputs.
It checks the input and all four proposals, not just the selected clip. Each
clip is imported in headless Godot. Original LINEAR joint keys replace the
fixed-rate import bake and are saved/reloaded as binary Animation resources.
The existing native authoring scrubber samples the full 120 Hz clock, original
keys and midpoints, and authored stance/edit boundaries with exact deduplication.

Observed world-bone transforms are independently compared to
`NativeSupportSampler`. The pose/basis/duration tolerance is 1e-4; requested
and actual scrub clocks use the existing two-double-ULP check. Original GLB
skin driven by observed engine bones provides a separate sampled foot-height
check. A pose pass does not imply that foot heights pass.

`audit_native_support_skin.py` then imports the same bound clips using the same
bound engine executable. It records actual positions, bind matrices, bone
mapping and raw imported weights. Correspondence uses the established limits:
1e-6 m rest positions, 1e-5 bind elements and 1/65535+1e-7 effective weights.
Reordered vertices/binds are supported; missing or ambiguous correspondence
rejects reconstruction. Weights are never renormalized to hide import rounding.

Actual imported data is combined with the preceding bound bone observations
to reconstruct every original vertex at every audited time. The resulting
sampled foot minima use the unchanged authored nonpenetration and maximum-gap
bounds. Vertex differences are measured without inventing a realism threshold.
This is CPU reconstruction of imported data; GPU deformation is not established.

Both requests bind executable hashes, evidence, executed methods and copied
GDScript. Inputs and methods are checked before/after execution. Every raw
observation, saved resource, diagnostic and failed result remains local. The
auditors require all primitives to use the same validated skin, unique plain joint names,
LINEAR joint TRS, one imported skeleton and a completed four-trial native
support study. They do not infer anatomical mappings or convert other studies.
The original completed evidence below used one primitive. The subsequent
[surface audit](native-support-surfaces-v1.md) extends the auditors to multiple
surfaces; the subsequent [rig study](native-support-rigs-v1.md) records actual
multi-surface fitting and Godot support imports.

```powershell
.venv/Scripts/python.exe scripts/run_native_support_engine.py `
  reports/completed-support-study reports/fresh-support-engine
.venv/Scripts/python.exe scripts/audit_native_support_skin.py `
  reports/fresh-support-engine reports/fresh-support-skin
```

Pass `--engine path/to/godot` to explicitly choose an installed executable.
The skin auditor requires the executable already bound by the engine audit.
The default points to the development cache; the public repository does not
bundle this engine or its character/model assets.

## Completed development evidence

The actual audits use `native-support-coordinate-repair-v1`, whose four warm
starts belong to one clip/rig. Trial 2 passes its original bin-rate selection
but still fails the separate stricter peak guard. The subsequent
[strict minimax study](native-support-strict-peaks-v1.md) retains its input.
No result is promoted to a release-quality or Studio selection by these audits.

Godot 4.7.2 imports five clips with 19 bones each and samples 701 times per clip:
**3,505 poses**. Every pose/clock/import screen passes. Maximum position error
is 2.2871e-7 m (0.2287 micrometres), maximum basis element error 5.5393e-7,
duration error zero, and maximum scrub-time error 4.441e-16 s. The input fails
both authored foot planes; all four proposals pass at 142 stance times per
foot when driven by engine bones. Reference-skin height differences are at
most 1.856e-7 m.
Foot checks use the existing fully foot-owned regions, 52/53 vertices; they
do not certify whole-body or blended sole-patch contact.

Actual imported correspondence passes for all five clips: 3,273 vertices,
four influences, exact rest positions and inverse binds, maximum effective
weight error 1.5244e-5 and weight-sum error 4.5819e-5. All **11,504,595 vertex
observations** are reconstructed. Maximum vertex difference is 5.4028e-5 m
(0.05403 mm). This measured rounding remains visible.

All four proposals also pass sampled support using the imported data.
For selected trial 2, left/right lowest heights range from
0.250835 to 1.470682 mm and 0.250794 to 1.339250 mm above the authored plane.
The input retains left/right penetration minima of -2.583013/-0.784085 mm.
Correspondence success cannot hide these input failures.

Twenty-four engine-auditor tests cover native/nearby fractional clocks,
shuffled bones, reference-skin height propagation, missing/corrupt observations,
failed pose/clock/loop/skin gates, candidate/ancestor bindings, archived output
and changed-source rejection. Ten additional imported-skin tests cover vertex
and bind reordering, raw weight rounding, invalid bindings/clocks/populations,
visible source penetration and complete fixture routing. These are CPU
fixtures, separate from the actual Godot studies above.

All **1,363 Python tests and 14 JavaScript suites** pass locally. All **1,405**
bound ancestor, engine, resource, imported-data and diagnostic files rehash
without mismatch. Preceding commit `8867927` passes hosted Windows/Linux
checks (run 36954599587).

Result hashes:

- Engine: `057726e3ece9996a45d4b227bb4f0860141eeb5cd0b682fd0fe27c699bd89ea7`.
- Imported skin: `93b02aeb8cde89496266e26220ac667404cf1487e3f1f2cc2f7d34d7e160ab3a`.
- Rehash receipt: `36419ee4af9a44242a39a304bebf57a485b1343a33b75f0581ba124495f8033f`.

This verifies native resource import and authoring scrubbing on one development
clip/rig. Ordinary playback/event dispatch, strict derivative preservation in
the engine, GPU deformation, stationary sole patches, continuous collision,
force/balance, broad rig/action/scene coverage and human cleanup remain open.
All 14 release capabilities remain unapproved and the full-project goal remains
active. The stricter coordinate study subsequently completed with all four
proposals rejected; its result and replay are recorded in the surface audit.
