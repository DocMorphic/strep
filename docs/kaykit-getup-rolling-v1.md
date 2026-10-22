# Preserving verified motion while extending a get-up correction

This development study extends the local candidates from
[the interpolation study](kaykit-getup-interpolation-v1.md) into a growing
prefix of the 180-key KayKit get-up clip. A passing prefix does not approve the
rest of the clip or establish believable movement. Human review and timed
cleanup evidence remain outstanding.

## Export contract

`scripts/surface_pose_key_export.py` writes explicit native key edits after a
declared preserved prefix. It checks the original binary prefix, asset and
channel layout, common clocks, LINEAR interpolation, complete finite controls,
and all unchanged key values after serialization. Original accessor and
buffer-view definitions must also be retained; appended animation data can use
new definitions. Rotation channels that share
a sampler are split when edited. Each output rebases on the immutable source
while retaining current values outside the selected keys, so repeated exports
do not continually append old correction buffers. The whole mesh at each
changed key must agree with the requested pose within 10 micrometres.

The initial 11 focused tests cover prefix pose preservation, shared samplers, repeated
buffer size, incompatible assets and clocks, invalid key indices, existing
outputs and nonfinite edits. They passed. The two CI inventories include the
test file; the full CI suites were not rerun for this change.

Two later regression cases close a metadata-redirection gap: preserving the
original bytes alone did not prevent a current file from redirecting an original
inverse-bind accessor or buffer view into newly appended data. Both fixtures
retain the original byte prefix while moving the bound mesh by 50 mm. The
exporter now rejects either redirection before creating an output. All 13
focused tests pass. Existing valid append-only exports remain supported; the
saved development checkpoint is rechecked before continuing with this version.

## Rolling protocol

Eleven independently fitted static or boundary poses initialize correction
parameters across the source clock. This interpolated seed is explicitly
unapproved: its initial full-clip audit fails at 6,898 samples, with maximum
floor depth 132.002424 mm and contact error 298.372289 mm.

Each solve covers three consecutive keys. The incoming key is fixed to the
decoded current GLB; the next two are edited jointly. Both intervals constrain
quarter, half and three-quarter poses. Full-mesh checks use all native keys,
eight subdivisions of each interval and a 960 Hz clock. Violations can add
floor vertices and sample times between optimizer calls. All 25 existing contact
phases, material targets and original acceptance limits remain unchanged.

Only a passing serialized window advances the checkpoint. Its middle key is
finalized; the final lookahead key can change during the next solve, which must
recheck the incoming interval. Every output retains all earlier key values.
Failed candidates and optimizer histories remain separate from accepted state.
Soft time limits checkpoint between windows; resource guards remain active.

A continuation compares the current initialization against holding or
extrapolating the last correction. It can stop at a densely verified feasible
iterate before optimizer convergence, with an explicit numerical margin. This
changes search initialization and stopping, not acceptance limits, and makes no
claim of optimality. Resumption verifies source hashes and independently
rechecks the saved prefix before extending it.

Engine verification independently remeasures the saved prefix, then captures
actual Godot native-authoring observations in bounded batches. Each batch
includes zero and the exact full-clip endpoint for the engine clock contract;
including the endpoint does not approve the intervening unvalidated motion.

## First checkpoint

The first run accepts eight consecutive windows and checkpoints at its soft
time limit after 640.375 seconds. Keys 0–8 are finalized; key 9 is a validated
lookahead. All 361 prefix samples pass the decoded geometry and correction
bounds. Actual Godot capture covers 362 times including the full-clip endpoint;
all 361 prefix samples pass floor and contact checks, with pose and skin
agreement. Maximum engine skin disagreement is 0.024467 mm. These results
approve only the measured prefix and engine agreement, not motion quality.

Local evidence is retained in `reports/kaykit-getup-rolling-v1` and
`reports/kaykit-getup-rolling-engine-v1`. The accepted clip SHA-256 is
`dbacb3c809b8a827719a79b757114edc8dfbc28e799efa0135c324c9a9732a12`.
The decoded prefix audit SHA-256 is
`56ad1d695f135450412c0f951e6206dd34dc34288d88bbd44446dfb8233451c2`.

## Continuation checkpoint

The resumed pass accepts all 26 attempted windows in 628.062 seconds and stops
at its soft time checkpoint. Eleven initial guesses pass without optimization;
the remaining windows require 380 optimizer iterations in total. This is a
different motion section, not a controlled timing comparison with the first run.
An intermediate attempt in the last window passes floor/contact checks but
exceeds the 5-degree correction-step cap at 5.143158 degrees. It is retained in
the history and rejected. A subsequent attempt passes the original limits.

Keys 0–34 are finalized, with key 35 a validated lookahead: 36 of the clip's
180 poses, covering approximately 1.167 seconds. Independent decoding checks
1,390 times with zero failed samples. Maximum floor depth is 4.740287 mm,
contact error 19.756263 mm, root correction step 9.481136 mm, and rotation
correction step 4.999558 degrees. These are sampled acceptance limits, not a
claim of zero penetration or natural movement.

The accepted clip SHA-256 is
`4c88b2bd1360b4abe39073cd82c968e9093af225dd7ae38fa49e9b405625f544`.
Its prefix audit SHA-256 is
`9b4c72977cff16d7f207f24f37e1a039d31a554cda15c560e389da5d96f22645`.
Local continuation evidence is `reports/kaykit-getup-rolling-v2`. All remaining
keys and the full clip remain unapproved.

Actual Godot verification in `reports/kaykit-getup-rolling-engine-v2` covers
four batches and 1,397 engine observations. The required 1,390-time prefix clock
is independently reconstructed from the source keys before replay; every prefix
sample appears exactly once in the combined results. All prefix floor/contact
checks and engine pose/skin agreement pass. Maximum skin disagreement is
0.024576 mm. The engine result SHA-256 is
`43f11a5b0d524afb5f99dbbbc5d93585b69692b34727e0c5110b452f1ec6bb30`.

Across the two fitting and two engine runs, all source bindings and recorded
resource checks replay: 1,366 resource observations, with peak observed worker
tree memory of 316,329,984 bytes. The memory guard and release requirements
were not weakened. Continue in a fresh study from the saved second checkpoint;
the next window begins at key 34. Do not rerun an existing report directory or
overwrite its accepted or rejected outputs.

## Third continuation

The third fitting run uses the metadata-integrity guard and freshly runs all 13
exporter tests. It independently rechecks the previous 36-pose prefix, accepts
all 14 attempted new windows, and checkpoints after 647.532 seconds. Keys 0–48
are finalized, with key 49 validated as lookahead: 50 of 180 poses. The prefix
includes the first hand-contact boundary and passes all 1,946 required sampled
checks. Maximum floor/contact errors remain 4.740287/19.756263 mm; maximum root
and rotation correction steps are 24.995616 mm and 4.999697 degrees.

`reports/kaykit-getup-rolling-engine-v3` independently reconstructs the clock
and verifies all prefix observations in Godot: five batches, 1,955 engine
observations, passing floor/contact and pose/skin agreement, with maximum skin
disagreement 0.024898 mm. These two new resource traces replay across 721
observations, with peak worker-tree memory 305,926,144 bytes. Historical studies
retain their original source versions; their receipts are not rewritten.

The third fitted result SHA-256 is
`4c4bb0fca28f979785080a1903abac35d17659716dd84ca5f973be26b4c73587`;
the engine result SHA-256 is
`c40dcb6773046a4cc766f23f1267cfaea8c4b9343656a68ba9aceb6df59d3a78`.
Resume in a fresh report from `reports/kaykit-getup-rolling-v3/state.json`,
starting at key 48. The rest of the animation remains unapproved.

Broader hosted tests on `89f6d29` exposed six clock-consistency failures in
timed rotation sampling, scene-edit interpolation and vertical-root interpolation.
Those failures are separate from this independently decoded prefix result and
must be repaired; this study does not claim full-suite success.

## Fourth continuation and unresolved contact transition

`reports/kaykit-getup-rolling-v4` resumes the third checkpoint with the same
geometry, contact phases, correction limits and memory policy. It allows 1,200
seconds between-window work before checkpointing, with a 1,500-second hard
guard. All 13 exporter tests pass. Of 29 attempted windows, 28 pass; the window
covering keys 76–78 remains unresolved after three refinement attempts.

The accepted result finalizes keys 0–76 and validates key 77 as lookahead:
78 of 180 poses. All 3,061 required prefix samples pass. Maximum floor depth
is 4.740287 mm, contact error 19.756263 mm, root correction step 24.997139 mm,
and rotation correction step 4.999863 degrees. The accepted clip SHA-256 is
`d82f9c419be71035950842d666b5e89527f970ce2e4fc1465a93b064ed17ea99`.

The rejected window's final pre-export check measures 26.444266 mm contact
error, a 25.065058 mm root correction step and a 5.263341-degree rotation
correction step. Its candidate and decoded audit remain separate from the
accepted state. This is a bounded local search failure, not a proof that the
contact transition is impossible. A next experiment should explicitly reopen
earlier keys and test a longer joint planning window, retaining all limits and
rechecking the changed intervals; simply replaying the same failed window is
not evidence of progress.

`reports/kaykit-getup-rolling-engine-v4` independently reconstructs the full
prefix clock and checks eight Godot batches: 3,076 observations including batch
endpoints. All prefix floor/contact and engine pose/skin checks pass. Maximum
skin disagreement is 0.028418 mm. These two runs replay 1,404 resource
observations, with peak worker-tree memory 317,792,256 bytes. Neither run stops
for insufficient memory. The engine result SHA-256 is
`fbb0855e73050e281f3887f81dee1a4cc6c6719265c3854b4b630c1e56091f46`.
The receipt is `reports/kaykit-getup-rolling-publication-v3/summary.json`.

## Reopening the approach resolves the next contact

The next experiment explicitly reopens keys 74–77 and jointly solves keys
73–78. Key 73 stays fixed, and serialization preserves every unselected key,
including the entire earlier prefix. All original contact phases, targets,
correction budgets and step limits remain unchanged. This is a development
study; automatic backtracking is not yet integrated into the Studio workflow.

The first six-key run, `reports/kaykit-getup-backtrack-v1`, is rejected after
three 40-iteration passes. Its decoded floor/contact samples pass, but root
and rotation correction steps still exceed the limits. Its candidate is kept
as failed evidence. A separate run,
`reports/kaykit-getup-backtrack-warm-v1`, compares that failed candidate against
the original, hold and velocity seeds. It selects the failed candidate only as
an initialization, then refines it with the unchanged acceptance checks. The
result passes: local maximum floor depth 4.376569 mm, contact error 19.019899 mm,
root correction step 24.991299 mm and rotation correction step 4.999759 degrees.
The prepared deterministic step-projection fallback was not run or needed.

The new saved state finalizes keys 0–77 and validates key 78 as lookahead:
79 of 180 poses. All 3,101 full-prefix samples pass; the prefix's worst values
remain 4.740287 mm floor depth, 19.756263 mm contact error, 24.997139 mm root
correction step and 4.999863 degrees rotation correction step. Candidate SHA-256:
`4d5ed66dfc35ea42add4de4f3995a1a4b865f953543efd20d95f65c2f502a5b5`.

`reports/kaykit-getup-backtrack-warm-engine-v1` reconstructs the prefix clock
independently and verifies all 3,101 samples in eight Godot batches, totaling
3,116 observations with the required batch endpoints. Floor/contact checks and
pose/skin agreement all pass; maximum skin disagreement is 0.029540 mm. Engine
result SHA-256:
`80476b230b897c39ff499cae68916d29d9666a699df46c42a0613234abf2d6da`.

Forty existing exporter, coupled-window and interpolation tests pass in each
fitting run. Three new regressions check three-, six- and eight-pose windows
against independently interpolated native skin positions and derivatives in
every pose's parameter block; incorrect later-interval endpoint bindings must
reject. Those tests pass and are included in both CI inventories (647 full and
196 focused Python files). Across the two fitting runs, engine verification and
new test run, 967 resource observations replay, with peak worker-tree memory
346,902,528 bytes. Publication checks are retained in
`reports/kaykit-getup-backtrack-publication-v1/summary.json`.

Continue from the warm run's state at key 77. Reopened keys supersede their old
values only in the new candidate; original checkpoints and failed studies stay
unchanged. The remaining clip, human review and broader release gates are still
unfinished.

## Fifth continuation

`reports/kaykit-getup-rolling-v5` starts from the repaired 79-pose checkpoint.
All 13 exporter tests pass. Fifteen of sixteen attempted windows pass, finalizing
keys 0–92 with key 93 as validated lookahead: 94 of 180 poses. The next window,
keys 92–94, is rejected with floor/contact and step failures; its candidate stays
separate from the saved state. All 3,699 prefix samples pass, with maximum floor
depth 4.740287 mm, contact error 19.867673 mm, root correction step 24.997139 mm
and rotation correction step 4.999863 degrees. Accepted clip SHA-256:
`d7c3465e050c24b57286b0939c4e6f3c1d859f1590b8a37f4b0f722ef2d6159d`.

`reports/kaykit-getup-rolling-engine-v5` independently reconstructs this clock
and verifies ten actual Godot batches, totaling 3,718 observations. Every prefix
floor/contact and engine pose/skin check passes; maximum skin disagreement is
0.032340 mm. Engine result SHA-256:
`bf2542ccfecb81bcd5617109bd1bee2f07880ea9bb1b278e61ee355d0ab1933a`.

A separate [correction-step projection study](surface-step-projection-v1.md)
validates a reusable proposal helper on an earlier failed window. It does not
replace this continuation. Across the fifth fitting run, its engine check and
the separate projection/native-engine comparison, all 1,038 resource observations
replay, with peak worker-tree memory 324,255,744 bytes. The receipt is
`reports/surface-step-projection-publication-v1/summary.json`. The next study
reopens the approach to the new contact failure, rather than treating small
step projection as sufficient for its larger geometry errors.

## Next contact: reachability and timing diagnostics

The six-key 89–94 attempt remains rejected and preserves the 94-pose checkpoint.
Floor clearance passes, but contact and correction-step limits still fail.
[Target timing and contact attribution](contact-phase-speed-bounds-v1.md)
identify a 4.854650-m/s necessary toe-speed requirement without introducing a
new acceptance threshold. A separately exported static key-94 pose passes the
original pose budgets, providing another initializer for a subsequent bounded
transition search. Neither the failed transition nor the static diagnostic is
adopted as a complete animation.

## Scope

The subsequent [fitting-buffer comparison](contact-phase-speed-bounds-v1.md)
repairs the 89–94 transition under the original acceptance limits. The latest
independently engine-checked checkpoint is
`reports/kaykit-getup-feasibility-margin-v1/state.json`: 95 poses, finalized
through 93 and validated through 94, with the next window starting at 93.
All 3,740 prefix samples pass; ten Godot batches contain 3,759 observations.
The new candidate supersedes the 94-pose checkpoint only as this validated
development prefix, not as a complete or human-approved clip.

These checks cover sampled floor/contact geometry, correction bounds,
correction step bounds, serialization and engine agreement. They do not prove
continuous collision freedom, self-collision avoidance, anatomical plausibility,
action correctness, ordinary playback, physics or GPU skinning. No quality or
release approval follows from a successful checkpoint. The broad project goal
and frozen release criteria remain unchanged.
