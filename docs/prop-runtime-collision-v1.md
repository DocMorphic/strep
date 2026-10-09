# Explicit collision settings in native packages

An optional `collision_profile` in a `strep-scene-prop-runtime-request-v1` request now travels from the explicit Studio grip editor into the complete native Godot ZIP. The exporter resolves a named profile into ten explicit physics settings and writes them to `project.godot`. The runtime checks the complete declared setting population, backend, physics rate and actual project values **before importing actors or installing bodies**. It rejects a mismatched project without changing global settings. Bodies continue to enable continuous collision detection themselves.

The editor's **Collision profile** selector offers project defaults, recorded baseline, earlier continuous detection and earlier detection with tighter penetration. Saving or building a request includes the selected name. Project defaults omits the field entirely; the legacy compiled configuration and startup bytes remain unchanged. A supplied invalid/null/boolean profile is rejected rather than silently replaced. Existing completed Studio jobs without a profile can retain their older complete method archive; new workers and explicitly profiled jobs require both collision helper sources, their recorded hashes and the original complete archive.

For a command-line package request, add:

```json
"collision_profile": "ccd-threshold"
```

The named profiles are `engine-default`, `ccd-threshold` and `strict-ccd`. These are explicit settings from the [procedural 60 Hz collision comparison](scene-collision-profiles-v1.md), including 0.001 m slop and zero collision margin. `engine-default` means that study's recorded CCD baseline, not an arbitrary engine version's unrecorded defaults. Every named profile pins gravity, solver iteration counts, stabilization, speculative distance, margin, slop, rate and both CCD fractions. Selecting one affects the packaged project's global physics settings; importing into a project with different settings requires a deliberate integration decision and revalidation.

The measured cylinder/sphere improvement in the earlier matched fixture does not establish correctness for arbitrary production objects, speed, scale or moving-world geometry. Sampled depth screens are not continuous collision certificates. Physical ownership changes still apply at a fixed boundary; exact source event times are preserved, and the known application delay remains visible. Original character/resource/intent bytes and failure reports are preserved. Package creation, import and baking do not grant animation realism, physical contact, human-quality or release approval.

The editable prop bake must preserve and check the same optional collision configuration during capture. Its independent capture audit checks actual recorded settings for a profiled source before evaluating pose, clock, ownership and physical failures. This avoids accepting a capture from a differently configured project merely because its output files import.

This is a source/build integration. The running Studio backend is not restarted in this work; live browser/backend delivery is separate from the rebuilt source and offline editor checks. Third-party engine binaries, models and assets remain separately acquired. The full general-purpose project goal and all fourteen release capabilities remain unapproved.

## Executed validation

The initial seven-module package/editor/bake source suite passes **180 checks** in **268.84 s**. After completing the capture/profile audit and legacy bake archive handling, the final three-module profile/bake suite passes **99 checks** in **127.10 s**, including **43 new profile tests**. These are overlapping suites; they are not 279 distinct checks or a claim that all 180 reran on the final bake hooks. Two existing Node editor suites pass. The shipped Studio HTML is rebuilt from its editable source and its source/preservation checks pass. Inventory becomes **418 Python modules / 41 Node suites**, preserving every older entry and CI policy.

Four actual pinned Godot **4.7.2-stable** package studies execute separately generated tiny GLBs, saved native animation resources, the packaged main scene, embedded/extracted root modes, one physical prop and an authored reference prop. Each has placed/rotated-parent playback plus an exported-main-scene boot run: **eight playback cases and four boots**. All native pose/root, source-bit event clocks, complete byte/ZIP preservation, visibility/mode, contacts, pause/preview/resume and restart checks pass. Each profiled playback rejects fourteen malformed configurations, including unknown/changed/incomplete profiles and an actual project-setting mismatch before participant installation. Each legacy playback rejects its original ten malformed cases: **104 rejections** total.

| Package run | Physics rate | Maximum sampled floor depth | Maximum physical application delay | Boot samples |
| --- | ---: | ---: | ---: | ---: |
| Legacy defaults | 120 Hz | 0 mm | 6.25 ms | 361 |
| Recorded baseline | 60 Hz | 48.979 mm — fails | 14.5833 ms | 181 |
| Earlier CCD activation | 60 Hz | 1.000 mm — passes | 14.5833 ms | 181 |
| Tighter CCD profile | 240 Hz | 0 mm | 3.3333 ms | 721 |

These are integration fixtures with separately generated source ZIPs, not a controlled comparison of model quality or CCD performance. The earlier [matched cylinder/sphere comparison](scene-collision-profiles-v1.md) provides the isolated settings comparison. All eight package playback cases still fail exact physical timing; increasing the rate does not make this exact. No gate is relaxed and the failed baseline is retained.

The 60 Hz earlier-CCD package also completes the **actual offline editable bake and native engine import**. Its raw capture is checked against all ten declared settings, complete finite physics/source clocks, ownership, held/authored poses and source inputs. It exports editable GLB curves/native resources and unchanged actor/intent references. Sampled physical floor depth is **0.99998 mm**, so the 10 mm screen passes; **14.5833 ms** application delay remains. Successful import grants only the existing engine-import field; all physics/animation/human/release approval fields remain false. Mesh and actor bytes remain unchanged. The study preserves **770 Python fixture source files**, rather than treating generated test assets as production humanoid evidence.

Local result bindings under ignored `reports/prop-runtime-collision-v1/`:

| Result | SHA-256 |
| --- | --- |
| `legacy-120/result.json` | `4c300570cbb83d8fc66ef4a272c7fe38e8ca9ef36e0686c5a1ca8020990484ae` |
| `baseline-60/result.json` | `19a030803416f57e6734f867ec0e23ea7808d77da86fb3390cf7ead6128f45b3` |
| `threshold-60/result.json` | `037e6e9e02b7b16fd5ab411ad35e4bfec493007155dbed7a5bea560f3fc322f9` |
| `strict-240/result.json` | `43993264141425d3efb85331aa4ba0a0ea68ad3332e7fac63a841413a1199509` |

The editable ZIP SHA-256 is `5302edb4719ba301fe2146aaf258aa80db2faf0f7e7d167260db61f111b10964`; capture binding is `fab1430ea563a0db373f27e854396b590fc075762fd5e062406a746d4feae004`. The owned guard exits zero in **79.329 s**, peak sampled process-tree RSS **303,341,568 bytes**; independent resource replay verifies all **77 observations**. Protocol binding: `0bdf3dff3d409fb12e6c4c9b9653fa668cc13fb002868223067d6116016a1cd7`; trace: `0556f7fa42f55406e867ee3adf5274b889b085d831df8a1376b36b4ecdac2a59`. Admission remains 512 MiB plus 600 MiB for this small procedural engine study. Full native motion fits and geometry audits retain their separate 2 GiB plus 600 MiB profile.

Separate numerical replay verifies executed source/fixture bindings and raw-output hashes for all four package studies, reconstructs the complete capture audit from original scene/request bytes and the actual recorded setting echo, and reevaluates the editable GLB and native-import component errors. Maximum errors are **2.07532e-7 / 1.11055e-7** for default-import/native-authoring paths under the existing 3e-5 component limit. The retained diagnostic import at 30 fps still fails with **0.0166357** default-import error; the exported native resource uses the declared 60 fps. The shipped HTML exactly matches its UTF-8 editable-source render. An initial verifier invocation used Windows' default text encoding for that comparison and failed after numeric replay; explicit UTF-8 corrects the verifier, and the complete replay reruns successfully. That diagnostic remains in the local verification record. No engine study is rerun just to replace it.

Reproduce a single actual integration study with a fresh reports path using `scripts/study_scene_prop_runtime.py --output reports/your-fresh-study --physics-fps 60 --collision-profile ccd-threshold` under the existing resource supervisor. Omit the profile for legacy behavior. The existing `scene_prop_bake.py` command takes the resulting runtime ZIP, an explicit parent/floor request and a fresh bake output. Logs, source copies, requests, native outputs and failures remain local. No model is sampled/trained, no reserved held-out motion is tuned, and no production rendering or human review is inferred. The next work is explicit physical timing handling, production scenes and broader action/rig/edit/style/transition validation under the existing full-project goal.
