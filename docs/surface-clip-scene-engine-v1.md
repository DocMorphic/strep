# Completed correction through a real scene build

The completed corrected CesiumMan wave now passes through the actual Studio
scene preparation, headless Godot native-authoring export, observation replay
and asset packaging. The package retains all nine correction-history files
byte-for-byte. This establishes the direct source-to-scene path, but the scene
does **not** pass its geometry conditions.

The unchanged candidate SHA256 is
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.
The study declares one actor at identity placement, no contacts or objects,
a floor at Y=0, a 5 mm penetration limit, and 17 evenly spaced times including
both exact endpoints. These are a bounded integration screen, not the earlier
4,737-sample correction or forward-playback populations. No inference about
times between these 17 samples is made.

| Measurement | Result |
| --- | --- |
| Imported joint pose agreement | Pass |
| Imported skin agreement | Pass; maximum 0.05623 mm, limit 0.1 mm |
| Sampled floor clearance | Pass; maximum penetration 4.66127 mm |
| Self-surface screening | Flags at all 17 poses; geometry acceptance fails |
| Numerical observation replay | Exact recorded observations and decisions |
| Correction history in scene ZIP | All nine files preserved |

The actual scene job is `reports/native-scene-jobs/surface-wave-scene-v1/`
in the primary checkout. Its wrapper, predeclared draft, guarded execution,
source bindings and independent artifact verifier are in
`reports/surface-clip-scene-engine-v1/`. The guard completed in 74.219 seconds,
with 74 replayed resource observations and peak process-tree RSS 195,969,024
bytes. The source and generated resources retain their existing licenses.

## Locate the geometry failure before changing motion

A follow-up compares the original and corrected native clips with recorded
Godot geometry at those same 17 times. Every native triangle is included;
no mesh welding, exclusions or tolerance changes are applied. Raw per-pose
records and their hashes are retained in
`reports/surface-clip-scene-self-diagnostic-v1/` in the primary checkout.

All three populations have flagged surfaces at every sampled pose, with
15–106 proper-crossing records per pose and many ambiguous boundary contacts.
The largest crossing segment is approximately 40.94 mm in each population;
segment length is not penetration depth. Ambiguous contacts cannot be assumed
to be harmless seams.

The corrected native clip introduces zero proper-crossing pairs absent from
the original across these observations. Godot introduces one pair absent from
the corrected native records: triangles 591/3546 at 1.487500011920929 seconds,
with an approximately 0.07377 mm crossing segment. This distinction remains
recorded; similar aggregate counts do not establish identical geometry.
The diagnostic guard and its 83 resource observations replay successfully.

Next, locate the recorded pairs on the original character, distinguish authored
mesh boundaries from motion-driven intersections, and evaluate any proposed
repair against the immutable original. Keep the failed geometry result until
that work supplies evidence. Later correction/transition ancestry transport
also needs validation beyond the direct scene/game-package path.

The subsequent [location diagnostic](native-surface-locations-v1.md) preserves
all pairs and identifies the arm/head and shoulder/torso regions. Proper
crossings are absent in the original default-node reference pose but present
in the sampled animation; duplicate vertex attributes do not exempt them.

This study uses the separately exported/reloaded native Animation resource and
authoring seeks. It adds no ordinary-import or forward-playback acceptance,
live browser test, GPU rendering, physics, loop/transition, partner/object
interaction, foot-planting or human-quality approval. Broader action and rig
validation and the pending developer review remain part of the project goal.
