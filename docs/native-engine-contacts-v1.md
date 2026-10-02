# Imported native foot-contact validation

An editable-native planting pass does not prove that an imported game asset
meets the same contact requirement. The new offline audit imports the actual
source and candidate GLBs into Godot, seeks their animations at the authored
stance sample times, reads imported skin bindings and reconstructs the foot
vertices on the CPU from the engine's world bone poses. It measures the original
source anchors, support height, gap and tangential speed without changing the
authored limits. A failed engine result remains a failure.

## Reproduction and scope

In an environment with the project's Python dependencies and the separately
acquired Godot 4.7.2 executable under `.cache/godot/4.7.2-stable/`, run:

```powershell
.\.venv\Scripts\python.exe scripts/native_engine_contacts.py source.glb candidate.glb draft.json plant-policy.json reports/my-engine-contact-audit --base input.glb
```

Choose a fresh output directory. `--base` is the unmodified input bound by the
planting policy; it defaults to `source.glb`. The policy must independently bind
the exact source, base and draft hashes. The source and candidate must retain
the same geometry, skin identities, duration and native track clocks. One named
skeleton and one non-looping animation are required. Four/eight influences and
multiple imported surfaces are read; only equivalent imported mesh/skeleton
spaces are supported. Blend shapes or a displaced mesh instance are rejected.
This tool does not widen the underlying rig import contract.

The run acquires the shared worker lock and archives the input files,
implementation, requested clocks, full imported bindings, engine samples and
version/executable hash. Inputs and methods are checked again at completion.
Inspection or contact failures do not modify assets or Studio selections.
Engine import failures produce a terminal failed pipeline record. A completed
audit can contain failed contact checks.

The original 120 Hz stance population includes the exact stance boundaries.
Native keys within the stance form a separate population; they are not merged
into velocity intervals. The imported pose observations use their union. Every
reported contact population retains its actual intervals, including nearly
coincident endpoints. Reports include the minimum interval, worst speed pair
and tangential displacement. No interval is filtered and the candidate's start
position never replaces the source anchor.

Vertex matching uses the pre-animation skin function for each named bone,
including weighted bind-space positions. It does not assume imported vertex
order or match nearest posed points. Equivalent duplicate vertices can map to
the same binding. For the pinned engine, the source's float32 weights are
multiplied by 65535, truncated to unsigned 16-bit integers and decoded to
float32 **for matching only**. This encoding must independently match the
imported binding functions. The binding identity tolerance is 2e-6 per
component; each result also reports the actual matching and position errors.
Native metrics retain the original weights and engine metrics use the imported
weights without normalization. Quantization is therefore included in the
measured engine/native difference.

The APIs follow the official [Skin](https://docs.godotengine.org/en/stable/classes/class_skin.html)
and [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html)
interfaces. The mesh bake API is deliberately excluded: its
[documentation](https://docs.godotengine.org/en/stable/classes/class_meshinstance3d.html)
describes GPU-buffer retrieval and ignored blend shapes. This run is headless
imported-pose plus independent CPU skin evidence, not rendered/GPU skin,
continuous collision, physics, force/balance, angular-rate or human review.

## Preserved development results

Four completed studies each import a preserved source and candidate. Together
they contain 960 engine pose observations, 77 named bones and one imported
skinned surface per scene. The wave candidates are actual editable-native
preview GLBs. The kick and crawl candidates are the earlier **rejected raw**
proposals; this audit cannot promote them or substitute for native conversion.

| Candidate | Imported anchor error | Imported maximum patch speed | Original stance contact limits |
| --- | ---: | ---: | --- |
| Studio selected-source wave | 0.509842 mm | 4.999588 mm/s | Pass |
| Earlier CLI original-source wave | 0.513114 mm | 198.579683 mm/s | Fail |
| Rejected kick proposal | 18.028331 mm | 332.722818 mm/s | Fail |
| Rejected crawl proposal | 331.478212 mm | 1625.073108 mm/s | Fail |

The wave limits remain 1 mm anchor error and 5 mm/s speed. The Studio candidate
has a minimum imported region height of 0.253440 mm and maximum lowest-region
height of 1.936270 mm, satisfying its 0.250 mm clearance and 5 mm gap. Its
native-key population also passes. Imported/native foot position differences
are at most 7.36 micrometres across all four studies; small position error alone
does not establish a speed pass.

The CLI candidate's failing pair is 2.4 to 2.4000000953674316 seconds: about
19 nanometres of tangential position change divided by 95 nanoseconds produces
the reported 198.58 mm/s. Its original native check passes at 4.999738 mm/s;
its imported native-key population passes at 4.989751 mm/s. A separate diagnostic
of ordinary intervals above one microsecond gives 4.999197 mm/s, but **that
diagnostic does not replace the failed original population**. This is a
conditioning/FP32 import issue to resolve in the sampling/export contract;
neither a universal visible motion defect nor an excuse for overriding the gate
has been established. Original anchors, limits, earlier studies and selections
remain unchanged.

The selected-source Studio and original-source CLI waves have different
reference anchors/caps by design. They are separate experiments, not a matched
quality comparison. Kick/crawl failures remain visible and rejected. No formal
held-out population, human realism decision, training admission or release
approval follows from these studies.

Evidence is local under `reports/native-engine-contacts-studio-wave-v5/`,
`reports/native-engine-contacts-cli-wave-v2/` and
`reports/native-engine-contact-action-canaries-v1/{kick,crawl}/`. Earlier parse,
weight-encoding and clock-validation attempts remain archived separately.
The public repository contains the implementation and concise methodology,
not model/character payloads or generated study exports.

Analytical fixtures cover binding reordering/duplicates, incorrect bone
assignment, retained weight deficits, invalid imports/clocks, source anchors,
strict over-limit speeds and nanosecond endpoint amplification. These are
software checks, not motion-quality evidence. All 14 project capabilities
remain unapproved and the formal 72x5 population is untouched. The full project
goal remains active, including broad actions, scene/partner contacts, editing,
styles, rig transfer, exports and human cleanup evaluation.
