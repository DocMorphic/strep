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

## Scope

These checks cover sampled floor/contact geometry, correction bounds,
correction step bounds, serialization and engine agreement. They do not prove
continuous collision freedom, self-collision avoidance, anatomical plausibility,
action correctness, ordinary playback, physics or GPU skinning. No quality or
release approval follows from a successful checkpoint. The broad project goal
and frozen release criteria remain unchanged.
