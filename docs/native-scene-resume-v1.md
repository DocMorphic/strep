# Source-bound native scene continuation

`scripts/native_scene_fit.py --resume-from <completed-job>` replays the final
normalized controls from a completed native scene fit. Supply the same original
contacts and permissions; do not use the previous proposal as the new source.
The default remains a fresh fit. This option is currently available through the
CLI, with originals retained pending scene, engine and human review.

Before optimization, continuation verifies the prior final receipt, archived
original actors, implementation hashes, source-rate arrays, frame sampling
contract, and exact authored contact/permission bytes. Paths must remain within
the prior job. The current exporter must reproduce every final edited GLB
byte-for-byte, and its decoded starting motion must pass all original protected
edit, displacement and sampled rate constraints. Contact failure may remain;
it is the quantity the next job attempts to improve.

The new job copies and hashes the required prior artifacts and any ancestor
snapshots. It checks both the prior files and the copies again before completion.
Source caps are recomputed from the original actor samplers and compared with
the prior arrays exactly; they are never recomputed from the repaired motion.
Corrupt, unfinished, rebound or source-unsafe checkpoints fail visibly. These
consistency checks do not authenticate an artifact's author or establish quality.

This is a warm start of controls, not restoration of optimizer internals. Trust
radius, Jacobians and decoded-error reserves start afresh. Each job retains its
existing limit of 1â€“16 primary iterations and records the cumulative completed
primary count across its ancestry. Counts alone do not measure compute: optional
restoration solves and decoded storage probes also consume work. A completed job
with failing contacts is not a quality-approved animation.

Example (paths refer to local, separately acquired inputs and saved jobs):

```powershell
.venv\Scripts\python.exe scripts/native_scene_fit.py contacts.json permissions.json reports/continued-fit --proposal-model storage-vector --iterations 16 --restoration-steps 3 --resume-from reports/prior-fit
```

The regression fixtures exercise chained byte-exact replay, unchanged source
arrays, unsafe starting-motion rejection, artifact corruption, altered input
limits, contained paths and mutation during execution. They use a small synthetic
rig and do not establish humanoid motion quality, continuous collision safety,
animator approval, training improvement or release readiness.

## Retained humanoid development trial

The retained high-five continues from 177.976173 to 77.223038 mm hand
separation against an unchanged 30 mm contact limit. It attempts 16 further
primary iterations and accepts 16 steps (20 cumulative
primary iterations). The larger budget and up to three additional restoration
solves per iteration are not a comparison at equal compute. All sampled original
positional/angular rate conditions remain passing, with source arrays exactly
matching the preceding vector baseline. Originals remain selected; the contact
target still fails. No new inference or formal held-out trial runs.

Independent verification replays 44 controls and
88 GLB exports byte-for-byte, with 25 restoration
margin updates and 256 fitting files rehashed.
The initial exports exactly match the prior final exports; ancestor snapshots
rehash. Full independent skin verifies contact effectors within
2.22e-16 m. Partner target
interpolation remains shared; margin arithmetic uses implementation Jacobians
and is not an independent derivative or solver proof.

Two actual headless Godot jobs measure 77.179256 and
77.179221 mm contact separation in import and native-resource manual
authoring modes. Combined sampled conditions remain failing. The diagnostic
plane and the separate 0.1 mm skin-position condition still fail; skin maxima
range 0.135614–0.136711 mm. The geometry policy changes
only its contact binding. Independent raw imported-slot reconstruction checks
2 contact point samples and 216672 complete geometry-clock
vertices, rehashing 115 engine files. Between-geometry-time
skin-error curves are not independently replayed. No GPU, physics, event,
continuous collision, human quality, training or release approval is established.
All 344 focused model-free tests pass, including 14 continuation cases.

A second continuation subsequently passes the unchanged point-contact limit.
See [scene placement and complete mesh checks](native-scene-stage-v1.md) for the
new evidence and the remaining hand-intersection and engine-fidelity failures.
