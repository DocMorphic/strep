# One source-bound object and character authoring job

`native_scene_authoring_job.py` connects the existing native contact, object-edit,
asset, engine and replay tools into one reproducible offline job. It accepts
supplied animated rigs and declared scenes across action types; action names
are not a whitelist. Prompt generation and rig transfer remain separate prior
steps. This job currently needs at least one declared primitive object; actor-only
scenes use `native_scene_engine.py` directly.

Create a recipe, inspect its exact input hashes, then execute it:

```powershell
python scripts/native_scene_authoring_job.py plan contacts.json policy.json path/to/Godot_console.exe reports/my-scene-recipe.json
python scripts/native_scene_authoring_job.py run reports/my-scene-recipe.json reports/my-scene-job
```

For an explicit bounded two-grip object-trajectory edit, add
`--object-edit object-edit.json` to `plan`. That request must bind the original
contact JSON, identify two existing matching holds, and declare its edit window,
translation/rotation bounds and key budget. It retains the
[existing object-edit contract](native-object-hold-fit-v1.md); it does not infer
grips, attachment, release, forces, anatomical roles or new actor motion.
An invalid edit is rejected, rather than silently omitted.

The recipe records exactly `schema`, `contacts`, `geometry_policy`, `engine` and
`object_edit`. Each non-null input records `path` and `sha256`; the versioned
schema is `strep-native-scene-authoring-job-v1`. Plans use absolute local paths.
Execution also accepts recipe-relative paths with the same binding checks.
The contact specification binds every actor file and selected animation. The
geometry policy retains its original complete declared clock, limits and planes.

The job runs these stages in order:

1. Measure and preserve original source contacts, including failures.
2. If explicitly requested, propose the bounded object edit and check its saved
   contacts, bounds and complete declared geometry. All actor bytes stay unchanged.
3. Export actual Float32 rigid object GLB tracks.
4. Prepare a separate common-clock bundle containing original policy times,
   original object audit times and actual stored object key times.
5. Observe actual default-import and saved/reloaded native object resources.
6. Observe complete imported character skin with native authoring tracks.
7. Query complete declared scene geometry using imported character skin and
   actual native object-resource observations, with pose/contact checks.
8. Replay all recorded skin/contact/object observations and saved geometry
   reductions through the separate [evidence verifier](native-object-scene-replay-v1.md).

Numerical failures do not stop later diagnostic stages or disappear from the
result. Execution, input-integrity and nonterminal-stage errors stop the job,
retain completed stages and partial files, and write a failed pipeline. Existing
outputs are never overwritten or restarted automatically. A completed job can
have `sampled_conditions_pass: false`; completion describes execution, while
the separate fields preserve measured conditions. An edited job additionally
requires its original-relative edit bounds for numerical success.

Every job archives its executing methods and snapshots original recipe, contact,
policy, optional edit and actor inputs. The executable is hashed and referenced,
not copied. Original inputs, snapshots and current/archived methods are rechecked
between stages and at completion. Derived contact/policy inputs and every
completed stage result also remain bound. Each stage's returned result must match its
saved result; the final replay must bind the actual combined result and agree
with its decision. Stage result hashes and artifact locations are recorded.

Execution refuses an active study worker and checks again between stages; each
heavy component retains its production worker lock. If another worker acquires
that lock between checks, the resulting execution failure is retained. The
wrapper does not bypass locks or create parallel model jobs. Recipes can be
prepared while a study runs, without dispatching another study.

Outputs remain workspace artifacts, not a portable game project or bundled
installer. Python dependencies, a compatible Godot executable and separately
licensed character assets must already be available locally. The recipe does
not download assets, models or runtimes and executes no network requests.
Source selection and Studio selection remain unchanged. Quality, training,
release, GPU rendering, physics, real-time playback and human review approval
remain false. Existing runtime events, attachment/release semantics, contact
normals, balance, self/object-object/continuous collision and semantic action
quality are not established by the wrapper.

Unit tests explicitly mock stage execution to exercise failure retention,
recipe bindings, changed inputs/methods/snapshots, interrupted/nonterminal stages,
worker contention and replay identity. A component integration test executes the
actual contact, GLB, clock, imported skin, geometry and replay Python code on
small closed meshes, with only engine execution mocked. Neither test type is
actual Godot, model generation, developer feedback or release evidence. The
separate expanded humanoid engine study and its original-method replay have
since completed; they are not rerun merely to exercise this wrapper.
All release capability gates stay open.

Local validation passes 41 cases. The initial component integration retained
37 passes and one real API mismatch: the synchronous source contact audit saves
its versioned result without an execution-status field. The job now validates
that tool's actual schema/source hash explicitly and still requires terminal
status for subsequent producers. The original failed pipeline and implementation
are archived; the component rerun and current whole suite pass.

A recipe is also prepared and validated against the actual retained humanoid
sphere source, original full geometry policy and installed Godot binary. This
is input/preflight evidence only; this wrapper has not executed that humanoid
recipe. Complete streamed producer validation is documented
[separately](native-geometry-stream-v1.md).

A separate actual procedural two-rig/object job now completes all eight stages
at 1,101 times, including saved resources, partner/plane geometry and replay.
Its original contacts and default object import fail; the bounded proposal and
sampled native conditions pass. An initial decimal-clock transport failure is
retained and repaired with exact binary clocks without widening tolerances.
This validates execution on small procedural rigs, not realistic humanoid
motion, general rig transfer, prompt semantics or human quality.
The previous replay commit's hosted checks pass on both Windows and Linux.
