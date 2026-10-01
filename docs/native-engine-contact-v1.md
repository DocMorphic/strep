# Native contact clips in Godot

Godot's default 30 Hz glTF import changes this development pair enough to fail
its authored palm target. Exporting the original joint keys as a Godot Animation
resource repairs the sampled pose/contact differences. The strict engine-clock
audit still fails at one sample just before the clip endpoint. No Studio selection
or release approval has changed.

## Matched evidence

The two inputs are the immutable selected GLBs from
`reports/checkpoint-guard-contact-v1`. Each has 77 joints, 154 LINEAR channels,
75 native keys per channel and a duration of 3.6666667461395264 seconds. The
authored event is 2.0917225950783 seconds; its preceding float32 key is
2.0917224884033203 seconds. They are separate audit samples.

Each actor is checked at 642 distinct times: the entire clip's 120 Hz grid,
all original channel keys and interval midpoints, and declared contact, window,
geometry-guard, plane and protected-boundary times. Only exactly equal times
are deduplicated. All world joints are compared to independently decoded GLB
motion. The pose/duration tolerance is the existing engine tolerance of 1e-4;
requested/actual clock comparisons allow only two double floating-point steps.

| Measurement | Default 30 Hz import | Native keys, saved/reloaded resource |
| --- | --- | --- |
| Maximum joint-position component error, A / B | 3.026 / 3.631 mm | 0.485 / 0.547 micrometres |
| Maximum basis-element error, A / B | 0.022183 / 0.022253 | 5.669e-7 / 5.974e-7 |
| Contact anchor errors, A / B | 1.586 / 1.738 mm | 0.0985 / 0.0629 micrometres |
| Palm gap at event | 3.9883 mm | 0.999965 mm |
| Authored contact target | FAIL | PASS |
| Duration error; loop mode; skinned surfaces | 0; none; one per actor | 0; none; one per actor |
| Strict seek-clock audit | FAIL | FAIL |

Contact measurements use observed engine world joints to drive the **original
full-weight CPU skin**, with the bound authored stage placements. They do not
establish that Godot's imported inverse binds/weights or rendered GPU skin are
equivalent. Neither contact diagnostic checks engine-driven mesh collisions.
The target uses the separately authored palm-region vertex 14683; it is not a
pass on the original fixed-point benchmark.

At 3.6666666666666665 seconds, Godot reports the actual seek position as the
duration, 3.6666667461395264: a 79.47286 ns difference. Every other declared
seek matches within two double steps, and the event seek matches exactly.
The stricter audit remains false, although the native resource's sampled poses
are well within the numerical pose tolerance. This limitation is retained rather
than changing the comparison to make the combined audit pass.

## Implementation and reproduction

`run_native_contact_engine.py` binds completed study evidence, archived methods,
candidate bytes and the local engine binary. It preserves complete observations
and per-time errors even when the measured comparison fails. Inputs and methods
are rehashed after evaluation. Fresh output folders are required.

The default runtime import uses `GLTFDocument.generate_scene(..., 30, false,
false)`. Godot's transform importer samples tracks at `1 / bake_fps`, including
LINEAR inputs. This explains the observed approximation around native keys;
the runtime comparison supplies the actual failure evidence.
[Godot importer source](https://github.com/godotengine/godot/blob/4.7-stable/modules/gltf/gltf_document.cpp),
[generate_scene documentation](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html).

With `--native-tracks`, `native_godot_payload.py` extracts original joint TRS
keys, and `native_godot_tracks.gd` installs corresponding Animation tracks on
the imported skeleton. The adapter writes `actor-0-animation.res` and
`actor-1-animation.res`, reloads them, verifies every channel's key count and
every key's original float32 time, and seeks the reloaded resources. These are
local experimental engine assets bound to the matching skeleton paths. General
non-joint animation, cubic/STEP interpolation and alternate skeleton mapping
are explicitly rejected by this adapter; other project import paths remain
separate. Loop wrapping is disabled for these non-looping clips.

```powershell
.venv/Scripts/python.exe scripts/run_native_contact_engine.py reports/checkpoint-guard-contact-v1 reports/checkpoint-native-engine-new
.venv/Scripts/python.exe scripts/run_native_contact_engine.py reports/checkpoint-guard-contact-v1 reports/checkpoint-native-tracks-new --native-tracks
.venv/Scripts/python.exe scripts/diagnose_native_engine_contact.py reports/checkpoint-native-tracks-new reports/checkpoint-native-contact-new
```

The first two commands currently return a nonzero exit after saving completed
failing audits. A failed numerical check is distinct from an engine launch or
source-binding failure. Read `pipeline.json`, `verification.json`, the per-actor
errors and `engine.log` before treating an output as usable.

The first observation attempts failed on timestamp JSON roundtrips. They remain
unchanged in `checkpoint-native-engine-v1` and `v2`. Full-precision Godot JSON
output and a two-ULP decimal-parser allowance repair that instrumentation issue;
they do not allow event quantization.
[Godot JSON precision documentation](https://docs.godotengine.org/en/stable/classes/class_json.html).
The first resource-key equality check also exposed double rounding from JSON
parsing; comparing to the original float32 source clock fixes that check. The
failed resource attempt is preserved in `checkpoint-native-tracks-v2`.
The initial native observations and final checked-resource observations are
byte-identical, while their archived implementations remain distinct.

## Remaining work

All 1,104 model-free Python tests pass, including explicit clock separation,
matrix layout, unchanged original payloads and rejection of unsupported mapping
or interpolation. The JavaScript fractional-clock checks also pass. Both engine
audits and both contact diagnoses are terminal. No fresh browser render or human
review was performed.

Next verify imported engine mesh skinning and resolve the near-end seek
semantics before gated Studio adoption. Integrate these as explicit native
region-conditioned candidates, keeping alternatives and motion failures visible;
they cannot be silently inserted into the older fixed-point paired job.
The original motion-rate failures, 6.003415 mm sampled floor penetration,
continuous collision uncertainty and human review requirements remain. No model
training or held-out evaluation was used; all 14 release capabilities remain
unapproved.

| Record | Result SHA-256 |
| --- | --- |
| Default engine audit v3 | `325af6431bbdbd64ee107cab1aec051e044521377351940c9b58c84cd04ff164` |
| Native resource audit v3 | `0882653d1482ebc3f8811c729674d0f80acd372789f8c334b1c4de53c70f9333` |
| Default engine-joint contact | `d793a4de0d60aba82e83678f29a117ab7caa13bf003aaec70d96098ce1b517ff` |
| Native engine-joint contact v3 | `d1cd4c7e30534ad92ff92f4591110c9cb63f2c88e33fe36f361c5a5e52b7b7d5` |
