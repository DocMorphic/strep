# Explicit scene placement with retained native motion

`scripts/native_scene_stage.py` applies one explicitly supplied translation to
every actor placement, object trajectory and world contact target. Object-local
contact points, partner vertex references, rotations, animation indices and clip
bytes remain unchanged. World planes stay fixed. This is a scene-authoring
operation; it does not infer the ground or repair a skeleton, foot plant or loop.
Moving world targets changes their absolute authored locations, so the operation
must be chosen deliberately for the whole scene.

The control file binds the exact source contacts and geometry policy:

```json
{
  "schema": "strep-native-scene-stage-v1",
  "contacts_sha256": "<source contacts SHA-256>",
  "policy_sha256": "<source geometry policy SHA-256>",
  "translation_m": [0.0, 0.015, 0.0],
  "maximum_translation_m": 0.02
}
```

The explicit translation norm must stay within the declared bound, which is at
most 0.1 m. A fresh output directory is required. The command snapshots and hashes
the inputs and methods, copies the original clip bytes, and measures both scenes.
Contact clocks, residuals, position/speed metrics, limits and acceptance must
remain consistent. The complete existing sampled geometry audit then measures
the proposal against the same planes, limits and clocks. Only the policy's
contact binding changes. Sources and snapshots are rechecked before completion;
mutation produces a failed job. Source scenes remain retained and proposals are
never automatically selected or approved.

```powershell
.venv\Scripts\python.exe scripts/native_scene_stage.py contacts.json policy.json control.json reports/stage-proposal
```

Fourteen regression cases cover world, moving-object and partner targets;
unchanged clip bytes and rotations; explicit fixed-plane repair; invalid or
rebound controls; input/archive mutation; and non-mutating proposal construction.
These synthetic cases do not prove motion quality or engine playback.

## Retained high-five: contact is only one condition

The second completed-fit continuation reaches 29.999466 mm against the original
30 mm point-contact limit after 13 further accepted iterations, or 33 cumulative
primary iterations. Original sampled positional/angular rate conditions still
pass. No cap, source, checkpoint, frame clock or contact target is relaxed. Its
very small contact margin warrants further robustness testing; this is one
development seed rather than held-out quality evidence.

The initial 77.223038 mm starting exports match the previous final exports
byte-for-byte. Independent verification replays all 49 proposals and 98 GLBs,
rechecks the source caps and restoration calculations, and hashes 325 fitting
files. Native and imported point contact passing does not establish a usable
high-five: complete mesh checks expose hand intersection at the contact time.

A separate explicit 15 mm common scene rise, within a 20 mm placement budget,
preserves all clip bytes and the measured contact residual. All actor-plane
conditions pass at the three previously declared times; the Y=0 plane and 5 mm
penetration limit remain fixed. At 2.5 s, native mesh geometry still reports 451
proper triangle crossings, with 217/147 vertices deeper than 5 mm and maximum
containment depths of 19.603/21.495 mm. Common translation cannot change relative
actor intersection. Both the failed fit geometry and the stage proposal remain
saved; neither is selected for release.

Ordinary and native-resource headless imports are evaluated separately before
and after scene placement. Actor placements are applied after raw CPU skin
reconstruction. GPU rendering, physics, real-time scene placement, gameplay
events, continuous collision, between-sample geometry and human review remain
unverified. The separate 0.1 mm imported/source skin-fidelity condition also
remains a failure. The next correction must include the complete contact-region
surfaces and partner geometry rather than optimizing one point alone.

The CPU skin-error decomposition accounts for the measured 0.136 mm error almost
entirely through unsigned-16 weight encoding. At these clocks, separate loader
normalization and imported-pose contributions stay below 0.00026 mm, and imported
bind-function differences stay below 7e-13 mm. The four component vectors sum
exactly to the observed error vectors. This uses the existing encoding/identity
helpers and raw imported poses; it is not an independent renderer implementation.
At the peak vertex, encoded weights sum to about 0.999924 while native weights
sum to one. No weights or fidelity limits are changed in this study.

For subsequent renderer validation, Godot's
[pinned RD skeleton shader](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/servers/rendering/renderer_rd/shaders/skeleton.glsl#L228)
unpacks unsigned-16 weights, accumulates weighted matrices and retains the
transformed position's xyz components. The current headless audit project uses
the compatibility backend; reading this RD source does not verify that backend
or any GPU buffer. Renderer-specific validation remains separate.
