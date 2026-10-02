# Guarded contact trials: lower worst error, retained failure

The opt-in [guarded search](guarded-mesh-trials-v1.md) reduces the worst contact
error on the fixed Cesium crawl from 130.100 to 61.173 mm. It still fails every
contact interval, regresses the previously passing left-shin proxy, and exceeds
the floor limit between keys. The exact original remains selected. This is
evidence about a bounded correction search, not usable crawl animation or
general motion quality.

## Fixed experiment

Reused the same original GLB, unchanged four proxy patches/targets active at
frames 54 through 56, 120 frames at 30 fps, 13 by 45 controls and ten-frame
control spacing. Floor/contact iteration budgets remain 30/60; the floor phase
finishes in two iterations and contact fitting exhausts 60 (SLSQP status 9).
Original edit limits, source rotation-step allowance and screens remain fixed.
The common normalized one-percent interior margin is stricter than the screens.
No inference, training or new seed was used.

Source SHA-256:
`393337840a57d4290731779668996be2588e79414af7882196e7113e2c8037bf`.
Draft: `47ee9ccc862ef2547c6331bd12b2f768056f6d63322ff04a8b9ec81f5e3bf1c8`.
The input/model provenance remains in the prior crawl/rig-transfer records.
These patches are unreviewed wrist/shin geometry proxies, not verified palms
and kneecaps or semantic annotations.

The new retention path examines finite SLSQP constraint evaluations, eight
segment fractions at each contact callback, and a common root-control lift
where the original motion limits and whole-mesh sampled floor allow it.
Matching iteration budgets do not imply equal computation: there are 1,038
recorded probes including duplicates, 33 in floor restoration and 1,005 in
contact fitting. Two floor updates and 55 contact updates are retained; contact
updates comprise 40 lifted segments, 14 unlifted segments and one endpoint
evaluation. Other contact probes are rejected for motion limits (403), floor
(267), or lack of improvement (280).

## Measured tradeoffs

| Clip | Worst contact, keys (mm) | Failed intervals / 4 | Deepest floor, keys (mm) | Deepest floor, dense clock (mm) | Failed dense floor samples |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 140.697 | 3 | 7.821 | 7.957 | 236 |
| Previous floor-guarded candidate | 130.100 | 3 | 4.491 | 4.491 | 0 |
| Guarded-trial candidate | 61.173 | 4 | 4.950 | 5.032 | 4 |

The contact screen remains 20 mm and the floor screen 5 mm. Left/right shin
errors become 61.166/61.173 mm; left/right hand errors 61.173/57.598 mm.
The previous left-shin error was 14.175 mm. Reducing a maximum does not imply
more successful contacts, and the minimax search can sacrifice an already
passing target. Root horizontal/vertical/step edits reach 40.000/91.190/15.000
mm, within the original bounds; joint edit/step and actual rotation-step checks
also pass. The original soft energy falls from 12.6880 to 6.6360, but is not the
selection metric or a quality score. All 120 frames are editable.

Independent replay checks all recorded motion proposals using parameter norms
and actual local rotation geodesics. Every retained update additionally passes
the original full-Jacobian motion constraints and a separate full-mesh
`RigAsset` evaluation. Contact-stage retained updates preserve the floor at
keys. Both selected phase endpoints are checked; final controls reproduce the
saved parameters and world poses. This accounts for 23,172,840 vertex
observations; rejected proposals' geometry is not exhaustively replayed.

Independent native interpolation checks original, previous and new clips at
701 poses each: 2,103 poses and 6,883,119 vertex observations. The clock combines
120 Hz, exact native keys, channel midpoints and declared float32 boundaries.
Four new-candidate sample observations exceed 5 mm near 1.875–1.892 seconds;
two are nearby, separately retained float32-midpoint and uniform-clock times.
The deepest point is 5.032364 mm at 1.8833333253860474 seconds. Under the full
half-open contact-frame hold, worst contact error reaches 69.477 mm; all four
intervals fail under both key-span and full-frame conventions. Neither convention
is silently substituted for an independently reviewed hold definition.

Fresh actual Godot 4.7.2 import checks all three clips at 360 poses, 19 bones
each. Maximum joint position/basis errors are 2.800e-7 m / 6.602e-7, with correct
duration and finite loop modes. Original skin driven by observed engine bones
reproduces keyframe floor/contact results over 1,178,280 vertex observations.
Imported skin weights, GPU rendering, continuous collision, anatomical contact,
force balance and semantic quality are not established.

## Export acceptance correction

The demonstrated between-key floor failure motivates a new independent gate
in the mesh-trajectory CLI. After encoding, `rig_subframe_floor.py` evaluates
the actual exported full mesh at 120 Hz, all exact native keys and channel
midpoints. Any floor violation rejects the candidate with
`decoded_subframe_floor_screen_failed`; evidence is saved and hash-bound.
This applies to both default and opt-in mesh fitting, without changing fitting
math or thresholds. It is a finite sampled check, not continuous certification
or a guard installed in every other Studio/export path.

A real synthetic export whose solver, keyframe floor and contacts pass is
rejected solely for its interpolated floor dip. STEP, exact clocks, immutable
source checks and long export inspection are covered separately. Sampling uses
an explicit duration override; ordinary existing-clip imports retain their
30-second limit. Saved requests retain strict implementation binding and refuse
to mix current code with older archived dependencies. Raw old requests are not
rewritten or silently migrated.

Applying the new gate posthoc to the three unchanged saved clips exactly agrees
with the separate dense floor observer. The real fitting experiment was not
rerun after adding this gate, and its raw result remains unchanged.

## Local evidence and remaining work

Fit: `reports/crawl-body-contact-guarded-trials-v1`; result SHA-256
`f4ace0c53f349d48734ce607e210f45779871a0be7e74fcf2f55817e9e8bc743`.
Candidate: `ee968740d4ed41c1bc9a2104d1004432676db6e4ec740b551e0e85e9b208afc5`.
Replay: `reports/crawl-guarded-trial-replay-v1`; dense inspection:
`reports/crawl-guarded-subframe-inspection-v1`; engine evidence:
`reports/crawl-guarded-trials-engine-v1` and its sibling study; posthoc acceptance
checks: `reports/crawl-guarded-export-floor-gate-v1`.

The initial receipt writer expected a flag absent from the older saved request;
its helper and failure are preserved. The corrected writer treats that absent
historical opt-in as disabled, without changing any fitting output. Its 146-file
receipt is `25304c6b0047092e4e71f03834443f089e2bd8620441923eb49617a3adab41d7`.
It binds the measured source revision; later source changes must use its
immutable method archives rather than expecting live code to remain identical.

Final evidence verification binds 167 files, the measured fitting classes and
optimizer archives, separate final export-gate source and source-check log:
`8795e33db8964f61f0cb5211571fe34e0b7683fee9d6c866a56dcb94051dbb6c`.
All 1,533 model-free Python tests and 14 JavaScript suites pass. The focused
mesh/version group passes 71 cases; the six existing-clip integration tests
also pass in the Torch-equipped project runtime. Their first model-free run
could not import a pre-existing Torch dependency; it was not a fitting failure.
The first full source check flagged the archived request/version mismatch
described above. Its failure is retained; neither the production version guard
nor the saved request was weakened. New portable cases require rejection for
changes to either current or archived code before actor payloads are loaded.

Next add between-key constraints to proposal fitting and protect already
passing contacts while pursuing the others, then review anatomical patches and
timing. Broader arbitrary actions, scenes/partners, editing/style, transfer,
loops/transitions and engine validation remain in the same project-wide goal.
Formal held-out prompts/seeds remain untouched. No developer/animator review,
timed cleanup or release approval occurred; all 14 capabilities remain unapproved.
