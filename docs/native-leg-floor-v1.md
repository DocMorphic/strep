# Native leg-only floor correction

A bounded leg-only correction removes sampled floor penetration from both
canonical development actors while retaining their hand contact and every
non-leg transform. It introduces knee-rate regressions, so it remains an
experimental alternative and has not changed a default selection or release gate.

## Method

The completed checkpoint-selected pair is the unchanged input. The previous
53 contact-window samples reported up to 6.003415 mm floor penetration. A full
native-key scan exposes larger defects, including endpoint poses: actor A reaches
8.268403 mm, and actor B reaches 10.664069 mm penetration.

At each original common leg rotation key, the correction selects vertices whose
positive skin influences all lie in that foot subtree. It measures the lowest
height against the existing stage floor, then moves the ankle along the floor
normal just enough for a 0.25 mm inward clearance. The existing exact two-bone
solver keeps bone lengths and foot world orientation. Only the thigh, shin and
foot local rotation outputs are replaced. All original key times, other channels,
root motion and upper-body world transforms remain exact after serialization.

This is a new full-clip leg authoring condition. Lower-body first and last poses
may change; the original contact window continues to define the matched rate
and partner-mesh evaluation interval. Whole-body protected spans are rejected.
Lifts greater than 30 mm, local edits above 45 degrees, scale/shear, unsupported
interpolation, mismatched leg clocks and unreachable ankle targets are rejected.
The current study names the canonical Left/Right Leg, Shin and Foot chains;
custom rig mappings are still required for broader product integration.

The minimum-height calculation is not a foot-contact or balance detector. It
retains horizontal foot trajectories at native keys and does not remove foot
skating or enforce whole-sole planting. Independent between-key decoding is
required; a correct IK solution at keys alone is insufficient.

## Measured results

Each serialized clip is decoded at 642 exact-deduplicated full-clip 120 Hz,
native-key, midpoint and original authored guard/event times. No acceptance
clock or original motion limit is relaxed.

| Measurement | Actor A | Actor B |
| --- | --- | --- |
| Source full-clip sampled floor depth | 8.268403 mm | 10.664069 mm |
| Corrected sampled floor depth | 0 | 0 |
| Minimum source-weight CPU height | 0.214695 mm | 0.217161 mm |
| Minimum imported-weight CPU height | 0.214640 mm | 0.217126 mm |
| Maximum native-key lift | 8.518403 mm | 10.914069 mm |
| Maximum local rotation edit | 11.403319 degrees | 13.370057 degrees |

All 53 original inter-actor full-mesh samples pass with zero crossings,
containment depth and degenerate faces. The source-weight authored palm gap
remains 1.000026 mm. Actual imported weights and observed engine joint poses
also pass the same contact target and 53 mesh checks, with a 1.049559 mm gap
and a maximum anchor error of 0.088439 mm. Imported-weight CPU reconstruction
passes floor checks at all 642 samples per actor. This reconstruction uses the
original source topology and the imported raw weights/binds; it is not a GPU
position readback or engine-physics collision test.

The unchanged engine pose and strict authoring-clock audit passes for both
actors, with maximum joint-position component error 0.534013 micrometres and
maximum seek difference 4.440892e-16 seconds. The GPU audit now exercises the
direct native-track authoring helper instead of ordinary playback seeking.
All 84 body/hand silhouette comparisons pass; all six 5 cm bad-forearm-bind
controls fail as intended. Minimum positive IoU is 0.999412517 and maximum
boundary distance is one pixel. Mesh rest positions and inverse binds are exact;
eight influences and bounded 16-bit weight quantization are retained. A local
body silhouette was inspected. This is engine rendering, not a fresh browser
render or an animator review.

## Motion tradeoff

Original motion caps still fail, and leg correction increases failure counts.
Maximum global excesses stay unchanged because upper-body defects still dominate;
that does not mean the legs avoid regression.

| Rate | Before failed rows | After failed rows | Unchanged maximum excess |
| --- | ---: | ---: | ---: |
| Position speed | 129 | 441 | 0.191452 m/s |
| Position acceleration | 297 | 338 | 25.282004 m/s² |
| Angular speed | 980 | 1,272 | 1.366928 rad/s |
| Angular acceleration | 144 | 193 | 138.945515 rad/s² |

Against the direct input, actor A's worst per-joint absolute increases are
0.064683 m/s position speed, 3.792400 m/s² position acceleration, 0.070075 rad/s
angular speed and 3.361884 rad/s² angular acceleration. Actor B's are 0.080562,
8.084936, 0.086524 and 11.259040 in the corresponding units. Shin motion accounts
for the worst increases. Both absolute peak guards fail. This candidate repairs
floor penetration, and does not qualify as a combined floor/rate improvement.
The next solver work must address knee trajectories while retaining floor,
contact and source-motion constraints together.

## Reproduce and review

```powershell
.venv/Scripts/python.exe scripts/study_native_leg_floor.py reports/checkpoint-guard-contact-v1 reports/new-leg-floor
.venv/Scripts/python.exe scripts/run_native_contact_engine.py reports/new-leg-floor reports/new-leg-floor-engine --native-tracks --authoring-seek
.venv/Scripts/python.exe scripts/audit_native_gpu_skin.py reports/new-leg-floor-engine reports/new-leg-floor-gpu
.venv/Scripts/python.exe scripts/diagnose_imported_native_contact.py reports/new-leg-floor-gpu reports/new-leg-floor-contact
.venv/Scripts/python.exe scripts/diagnose_imported_full_floor.py reports/new-leg-floor-gpu reports/new-leg-floor-full-floor
```

Use fresh immediate `reports/` folders and the separately acquired local runtime,
character and source chain. Every study binds inputs and archives implementations;
previous outputs remain immutable. The first GPU attempt failed because the
new preview helper was not copied into its temporary engine project. It is
retained in `native-leg-floor-gpu-v1`; only the fresh, repaired v2 is passing.

Studio's Scenes window now offers **Native contact comparisons → native leg
floor v1** after Refresh. Compare the checkpoint input against the floor-only
candidate; both original rate failures and the new leg regressions remain
visible. Four comparison GLBs pass offline format/Three.js loader checks with
zero errors or warnings. Browser rendering and human review remain unverified.

All 1,155 model-free Python tests pass. Separately, hosted CI exposed a Linux
import failure caused by the Windows-only generation lock. Deferring that import
for read-only routes preserves the Windows generation lock and allows the real
review API tests to pass on Windows and Linux; fix 980e6c1 passed both hosted jobs.
This does not establish Linux model execution. No training, held-out use, human
cleanup evidence or release approval was added; all 14 capabilities remain
unapproved and the full project goal stays active.

| Record | Result SHA-256 |
| --- | --- |
| Leg floor study | `1dbe615daa78f48515be163a5c521e69cb9ba60628d457f1195db34f480c0180` |
| Native authoring engine audit | `bae0d71bb176354e0e5a23c408044150df119a6d6133a5485d7a383026d8f62f` |
| Direct-authoring GPU audit v2 | `d78fee1eccdf5e7439df981a78f8209541f29a0a94f904568bb252d607aac168` |
| Imported-weight contact/mesh | `6cf4ef857ad3f67de25f9e45d6aaba488f7a13c3f117e9e1aa01de62e24f06c7` |
| Imported-weight full-clip floor | `bc80b83ec9b68f3f4be4f14e1d11aaeeacc8c0a10c63f4f04aac449bf03730cb` |
| Studio comparison build | `d1016e6c1abaa9421318967b73422ac80d11e492a2431ee98bf861ba77163871` |
