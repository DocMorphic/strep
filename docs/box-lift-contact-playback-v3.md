# Longer lift: first completed contact fit

The longer lift fit completed after two retained memory-guard failures. The
unchanged Kimodo output remains the source; this experiment fits contacts around
that clip rather than training the checkpoint. The complete source and candidate
retain their six-second clocks and the explicitly authored anatomical grip
points on a 40 cm box. This source setup differs from the earlier wrist/palm
baseline and must not be presented as an unchanged replay of its contact errors.

V17 uses the existing sparse skin operator, 32-frame object playback checkpoints,
six outer optimization stages and unchanged populations/bounds. It completed in
765.812 seconds, peaking at 1,028,493,312 bytes of process-tree RSS under the
one-hour / 7 GiB tree / 600 MiB available-memory guard. Native results report
approximately 21.8/21.9 mm maximum grip error. That meets the authored 30 mm
contact tolerance but **does not meet the solver's approximately 5 mm working
target**. A finished optimization is not proof that all requested bounds hold.

## Independent imported playback

Actual Godot 4.7.2 reimport sampled each complete clip at 240 Hz plus its exact
exported keys: 1,601 poses per actor and object, including 537 contact samples
per hand over the authored 2–4 second interval. All 18,056 vertices, 36,108
triangles and eight skin influences were retained and identity checked.

| Measurement | Anatomical source | Fitted candidate |
| --- | --- | --- |
| Left grip maximum error | 390.057 mm | 21.797 mm |
| Right grip maximum error | 401.340 mm | 21.931 mm |
| Failed 30 mm samples per hand | 537 / 537 | 0 / 537 |
| Floor maximum vertex depth | 8.997 mm | 0 mm |
| Floor samples above 5 mm | 1,294 / 1,601 | 0 / 1,601 |
| Box maximum vertex depth | 0 mm | 1.369 mm |

Both candidate contacts first meet their tolerance at the exact authored start,
2 seconds. Provisional normal diagnostics measure 14.270° and 13.786° maxima
against a 15° diagnostic screen; this is not anatomical grip approval. Imported
skin displacement stays below 100 µm on both clips without applying the optional
precision derivative. Point and vertex measurements do not measure triangle
interiors or establish that the box center lies outside the character volume.

The stricter 4.99 mm working-target screen fails at every one of the 537 contact
samples per hand. Candidate minimum errors are 15.926 mm left and 14.637 mm
right. Passing the authored 30 mm tolerance therefore does not establish a
precise grasp, even for the best sampled pose.

The engine producer and independent input/method replay completed. A private
post-run summary writer then failed because it requested `scene_id` where the
row field is `id`. That wrapper failure remains intact; a separate verified
summary references the completed producer. The expensive engine study was not
rerun or relabeled to hide the wrapper error.

## Remaining failures

The fitted candidate has up to **615.699 mm joint displacement** from the raw
motion and 24.613° local rotation change. Review flags include
`pose_change_above_22cm` and `LeftHand_surface_slide_regression`; the latter is an
estimated surface support statistic, not an authored support contact. The fit
also adds up to 1.212 m/s joint velocity and 10.001 m/s² acceleration. These
measurements prevent a claim that meeting grip points made the action realistic.

## Full imported surfaces and volume

The full triangle/volume/floor audit now has independently verified results for
all 1,601 source poses and all 1,601 candidate poses. The unchanged limits are
5 mm penetration, 1 µm depth resolution and 10 nm surface tolerance. The actual
imported mesh retains all 18,056 vertices and 36,108 triangles at every pose.

| Full geometry measurement | Anatomical source | Fitted candidate |
| --- | --- | --- |
| Floor maximum depth | 8.997 mm | 0 mm |
| Floor samples above 5 mm | 1,294 / 1,601 | 0 / 1,601 |
| Box triangle depth upper bound | 0 mm | 2.225 mm |
| Box samples above 5 mm | 0 / 1,601 | 0 / 1,601 |
| Box center outside character volume | 1,601 / 1,601 | 1,601 / 1,601 |
| Geometry conditions available / degenerate | 1,601 / 0 | 1,601 / 0 |

The triangle interior maximum exceeds the earlier vertex-only 1.369 mm result.
It stays below the unchanged 5 mm acceptance limit. The candidate passes these
sampled geometry conditions; the original retains its floor failure. This is a
finite playback audit, not continuous collision detection or a physical grasp
test. Neither attachment correctness nor naturalness follows from this pass.

Two guard failures remain intact. The first stopped after 509 source poses; the
second completed the source but stopped after 1,462 candidate poses when system
available RAM fell below 600 MiB. The second parent run remains failed. Its
completed source artifact was verified separately, without relabeling the parent.
A fresh candidate-only audit then completed every original sample using the
model-free environment, with unchanged methods, geometry limits and populations.
It took 463.750 seconds and peaked at 865,222,656 bytes tree RSS under the same
one-hour / 7 GiB / 600 MiB guard. No partial candidate result was promoted.

Both complete per-scene numeric archives verify all 4,804 arrays and
2,312,369,128 logical bytes against the actual imported producer. Input, method,
clock, topology and archive hashes remain bound. Archive transport verification
itself does not certify geometry; the separate complete geometry reports supply
the measurements above. Generated receipts and bulk arrays remain local.

## Review and next correction

Studio offers a separate, unblinded developer comparison of the preserved source
and fitted candidate, with fit flags, dense contact measurements and full geometry
receipts. It does not replace a selected animation or submit a human rating.
The tighter hand target and excessive pose changes remain explicit failures.
Natural motion, attachment,
force balance, independent animator review, held-out performance and all fourteen
release capabilities remain unapproved. The next correction needs to address
the missed tighter grip target and excessive motion distortion without relaxing
the current contact or geometry limits.

## Opt-in body-preserving fit

Decomposing the saved motions identifies the source of the body distortion.
The limb/floor preprocessing changes joint positions by at most 48.962 mm.
The next body preprocessing stage leaves them unchanged. Contact fitting then
introduces the 615.699 mm maximum at `HeadEnd`, frame 102, with 2,664 joint/frame
observations above the existing 220 mm screen across 49 frames. The baseline
constrains local rotation edits and root lift; its body-position screen is a
post-fit diagnostic, not a guaranteed joint-position bound.

The scene experiment now has an explicit `--preserve-body` option with solver
17. It inserts the existing native body inequalities against separately copied
raw, limb-corrected and previous joint tracks. Their existing 220 mm displacement
and 1.5 m/s added-speed limits stay unchanged. Explicit point residuals use the
existing tolerance normalization. The full clock, object query populations,
quarter-key object queries, six optimizer stages and original acceptance limits
remain unchanged. The ordinary baseline command retains its prior behavior.

```powershell
.venv/Scripts/python.exe scripts/run_scene_fit.py <authored-scene.json> `
  --output <new-study-folder> --solver-version 17 --preserve-body `
  --preview-base <saved-preview-folder>
```

This is an opt-in constrained optimization experiment, not a newly trained
checkpoint or a promise of feasibility. The existing augmented penalties may
still miss constraints. Keep any misses and independently reimport and review
the resulting clip before interpreting it as an improvement. Forty-nine local
tests pass: 37 reference/mode/reach checks and 12 existing body-objective checks,
including gradients and independent raw/limb limits. Model-free CI now declares
401 Python modules and 38 Node scripts; hosted checks are separate evidence.

## Proven target/body-budget conflict

The original requested lift cannot simultaneously satisfy its grip targets and
the 220 mm joint-position budget against raw motion. An unchanged LBS skin point
can move by at most the weighted joint budget plus the weighted bind-point
rotation radius. The new preflight uses actual source matrix operator norms,
allows arbitrary new proper rotations, retains all eight influences and
subtracts 1 µm arithmetic slack from its error lower bound. Reverse triangle
inequality then supplies a conservative minimum remaining target error.

| Native contact keys (61 per hand) | Left hand | Right hand |
| --- | --- | --- |
| Largest error lower bound with 220 mm body budget | 103.431 mm | 115.247 mm |
| Keys incompatible with 4.99 mm working target | 27 | 36 |
| Keys incompatible even with authored 30 mm target | 22 | 33 |

These are native-key impossibility results, independent of optimizer iteration
count. A zero lower bound for another key does **not** certify feasibility:
anatomy, coupled joints, speed, normals, geometry and between-key behavior remain
additional requirements. The bound applies to the original skin, target track
and raw reference; changing any of these requires a new explicitly bound request.

The opt-in mode records `body-reach-preflight.json` and rejects a proven conflict
before the expensive scene evaluation, floor preprocessing or optimizer. The
ordinary baseline remains available. An integration check with the actual source
and compiler verifies that the incompatible request retains failed pipeline
status, its input/method archive and its preflight receipt, produces no candidate,
and never invokes the three expensive callbacks (they are replaced by rejecting
test callbacks). That test completes under the unchanged guard; it is not an
animation-generation or engine-playback study.

Two attempted body-preserving fitting launches remain failed: the first missed
the available-RAM precondition before starting a worker; the second stopped at
38.782 seconds on the same 600 MiB guard, with 1,030,934,528 bytes peak tree RSS.
Neither produced a candidate. The independent model-free bound and the subsequent
preflight integration test provide useful evidence without promoting these runs.
Only the owned Studio processes were temporarily closed, and Studio was restored.

The next authored scene must review box placement, trajectory and contact timing
explicitly while retaining the measured baseline. Increasing optimization time
cannot reconcile the proven conflicting limits in this original request.
