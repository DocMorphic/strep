# Preserve fractional authoring times at native keys

`NativeSupportSampler` now performs key searches, endpoint comparisons and
interval arithmetic in Float64. Stored Float32 key times are exactly promoted
for calculation; the clock arrays, animation values and source GLB stay intact.
Exact-key values retain the previous direct-key behavior. Effective control
bases use this same sampler, so the parameter model follows the actual motion.
The shared `AnimationSampler` uses the same precision for imported clips.
Historical reports remain tied to their previous code; the original samplers
are retained with the regression evidence.

The old endpoint comparisons mixed Python times with NumPy Float32 scalars.
Under NumPy 2, a nearby query could round to the key before comparison. For
example, a request at `119/30` seconds is earlier than the stored Float32 end
`3.9666666984558105`, but previously clamped to that final key. This can change
a STEP animation to its final pose too early. Subtracting two Float32 key times
also rounded some nonuniform interpolation intervals. These are precision
errors, not permission to move keys or relax motion limits.
[NumPy promotion documentation](https://numpy.org/doc/stable/reference/arrays.promotion.html)
describes the Python-scalar precision behavior.

Six failing regression cases reproduce the defects before the change:
near-final linear and STEP samples, near-first translation and rotation, and
nonuniform LINEAR/CUBICSPLINE intervals. A seventh checks exact keys and stored
clock-byte preservation. The original sampler and failing evidence remain in
`reports/native-clock-precision-red-v1/`.

## Separate engine timing from spatial errors

`native_import_clock_diagnostic.diagnose` examines every recorded frame and
the complete imported skin, retaining requested and reported times separately.
It reports spatial differences at both clocks without rewriting captured times,
discarding duplicate reported samples or treating reported-time agreement as
requested-time acceptance. The same 1 ns seek, 1e-4 pose and 0.1 mm skin limits
remain in force. The normal engine acceptance path is unchanged.

Godot 4.7.2 deliberately snaps positions near a non-looping playback endpoint.
This is separate from the corrected Python sampling defect. The existing
native-resource authoring seek avoids that processing; ordinary playback is
still subject to it. [Version-pinned Godot source](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/animation/animation_player.cpp#L195-L211).

The initial diagnostic tests found two existing mocked-engine tests trying to
acquire the live worker's lock. Their simulated jobs now use isolated fixture
locks, while the real numerical worker continues to hold the shared machine
lock. Both failures and their successful rerun are retained. No production
locking rule was relaxed.

Historical diagnostics in `reports/native-import-clock-diagnostic-v1/` and
`-v2/` used the old reference sampler. In particular, their zero native pose
shift between the endpoint clocks is not evidence of exact continuous-time
agreement. Recomputed evidence uses the corrected sampler and a new report.
No earlier motion-quality, rate, contact or release failure is cleared by this
change.

## Verified results

The first native-sampler correction passes 244 tests across twelve modules,
including real planting fits, clock/control-basis checks, mesh contact clocks
and imported-scene comparisons. Extending the same arithmetic to the shared
clip importer passes its precision checks. The CesiumMan round-trip test then
exposed two unused ground-audit imports that pulled in Torch; removing those
imports lets all six existing clip-import tests pass in the model-free runtime.
Generated-motion contact loading remains in its existing conditional path.

Across the guarded epochs, 257 distinct final test cases are covered. The
initial lock-fixture and optional-runtime failures remain recorded, along with
the six intentionally reproduced precision regressions. The complete 701-frame
diagnostic is byte-identical before and after extending the fix from native
sampling to the shared importer: the additional promotion is a no-op for
already-promoted native queries. This is targeted evidence, not full CI or
release approval.

An independent comparison evaluates every local channel of the actual KayKit
clip using NumPy's linear interpolation and SciPy's quaternion Slerp on exact
promoted key times. All **25,236 queries across 36 channels** agree within
6.67e-16; all **4,320 exact-key observations** remain bit-identical to the old
native sampler. Nineteen channels improve relative to the independent
reference; the old maximum component error was 1.477e-8. This independently
checks interpolation, not the world-transform or skinning implementation.

The unchanged ordinary-import capture still fails its clock gate at sample
699. Both requested-time pose and complete skin comparisons pass their existing
limits; maximum skin error is **0.0319645 mm**. The corrected native sampler
measures **2.108e-8 m** of skin movement between the requested and reported
endpoint times. It is small but nonzero; neither that fact nor the spatial pass
waives the 1 ns clock requirement. The earlier correction's contact/rate failures
remain unresolved, and the original animation stays selected.

Evidence is retained in `reports/native-clock-precision-v1/` through `-v3/`,
`reports/native-clock-independent-v1/` and
`reports/native-clock-publication-v1/`. Seven resource traces replay without a
RAM-guard stop. Source files and captured engine output remain unchanged within
each run. No engine rerun, model generation, training or human rating was used.

## Batch and editing consistency follow-up

Hosted checks on `89f6d29` exposed six remaining disagreements with the promoted
scalar decoder: timed rotation sampling, scene-edit preview interpolation and
the sparse vertical-root basis still subtracted some Float32 key intervals.
The rotation path also retained weak scalar endpoint comparisons. A local
seven-case reproduction fails the same six cases and passes the Float64 control.
The failed evidence is preserved in `reports/native-clock-batch-baseline-v1`.

`timed_rotation_edit` now promotes clocks and queries before endpoint comparisons
and interval subtraction. `native_scene_edit` and `native_vertical_root` use
the same arithmetic. `SupportRateProblem` reuses the shared promoted endpoint
masks, removing an older override that could still snap an interior query to
an endpoint. Its bend, swivel and foot-orientation modes retain their existing
edit and motion limits. The scalar decoder, stored keys, source GLBs and all
test tolerances are unchanged.

The first affected-path run covers 172 cases in 14 modules: 167 pass and five
fail. Two failures expose a missing CesiumMan fixture in the isolated test copy;
three expose the remaining support endpoint override. Both causes and the
original failed run remain recorded. The follow-up binds and copies the local
licensed fixture with its license/provenance, fixes the override, and passes
all 53 importer, support, swivel and orientation tests. Across the two final
validation epochs, all **204 distinct test cases** have passing evidence. This
includes every reproduced failure, real export/decode comparisons, unchanged
clock checks, zero-edit behavior, derivatives, protected intervals, and direct
rotation-edit consumers. Already-passing unaffected tests are retained rather
than rerun solely to produce a single green receipt.

Each test epoch uses an isolated source snapshot while the parent holds the
shared project numerical lock. Tests can exercise their own fixture locks in
that copy; production locking is unchanged. Original and snapshot hashes,
test XML and resource traces remain in `reports/native-clock-batch-fixed-v1`
and `reports/native-clock-batch-fixed-v2`. Full hosted regression on the repair
commit is still required; targeted tests do not confer motion or release approval.

All three resource traces replay across 420 observations; peak observed process
tree memory is 148,111,360 bytes. Snapshot bindings, current runtime sources,
unchanged scalar decoders, and unchanged test sources are independently checked
in `reports/native-clock-batch-publication-v1`. The final follow-up test XML
SHA-256 is
`b94f7a23de07bb08b31921f4a68278a04395da9699db77c5bbf2caaab608c9ef`.
