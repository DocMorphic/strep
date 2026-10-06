# Explicit repair of control-aware study exports

`scripts/native_control_axis_pair_repair_job.py` accepts completed `strep-native-control-axis-pair-study-v1` results directly. The older repair command and receipt schemas remain unchanged. This adapter does not relabel a new study as a legacy result. It binds the original job, every input and saved artifact, the complete current/archived producer implementation, every original native/geometry sample, and the completed exact model/export replay. Replay records must equal producer records; incomplete bindings, populations, clocks and approvals are rejected before output creation.

The request uses schema `strep-native-control-axis-pair-repair-job-v1`, with these fields:

- `job`, `study`, `independent_replay`: each contains an explicit `path` and SHA256 of the original file.
- `settings`: `maximum_stages` from 1 to 8 and `maximum_probes_per_stage` from 1 to 64; booleans are invalid.
- `label`: a nonempty name for a separate diagnostic clip.

Run against a fresh output directory outside the saved study:

```powershell
python scripts/native_control_axis_pair_repair_job.py --request reports/control-axis-pair-repair-v1.request.json --output reports/offline-control-axis-pair-repair-v1
```

The existing finite greedy storage search remains unchanged. It chooses the lowest complete geometry score among actual centered-motion and original-reference passing fractions as search guidance. Continuous controls are fixed. Absolute one-neighbor quaternion component choices may add, remove or replace a choice within the existing acknowledged storage envelope, without accumulating steps. Every probe exports and decodes all actors, retains every original native condition and saves its observations. A native/reference passing result receives the complete original geometry audit and separate appended diagnostic clips. Passing export or motion checks does not select an asset or approve its geometry.

## Completed experiment

The [completed control-aware study](control-axis-pair-study-v1.md) supplied its full-step depth fallback, with one stored motion failure and zero centered failures. Original source/static/reference/rate/contact/edit/geometry contracts, all ninety controls, **1707 native samples** and **1673 geometry samples** remain. The request allowed eight stages and 32 probes per stage.

The search tested **two** neighbors at fixed continuous controls. The first, a negative neighbor of A's node8 rotation key253 component3, still fails; the positive neighbor passes. The absolute choice count increases **31 → 32**, within the original 64-choice policy. All three actual probe exports remain: failed motion counts **1 → 1 → 0**, zero final contact failures. Original reference limits pass: joint displacement remains about **4.31 mm** within 30 mm, and all six track changes remain below five degrees.

Final complete geometry is **unchanged** from the raw full-step result: maximum penetration **4.941718 mm**, **30474** triangle intersection records, zero vertices exceeding the five-millimetre containment limit, and **1608** failed geometry samples. Complete geometry still fails. The two appended clips retain every original library entry, binary prefix and scene metadata; their complete native worlds match the repaired exports. These are diagnostic variants, not production selections.

A separate consumer imports no repair, search, storage, job, proxy, new model or axis implementation. It uses a legitimate original completed-study context and separately binds the new study/request, without schema normalization. Manual absolute choices reproduce every probe's payload, controls, native worlds and residuals exactly. Original rates and Float64 static references are recomputed/replayed, all final reference bounds match, and both appended libraries/metadata/native worlds match. Geometry clocks, limits, scores and archives match as transport; collision predicates and greedy-search completeness are not independently certified.

**37 tests pass**, zero skips, in **109.71 seconds**. Actual GLB fixture tests cover both original job versions, complete artifact/implementation binding, schema/replay/population/clock rejection, false raw observations, immutable output boundaries, input mutation, appended libraries and release of archived probe worlds. Protocol fixture replay fields do not claim a real model/solver replay; the separately completed experiment above supplies that evidence. The tests join existing Linux/Windows source checks; hosted CI success is not claimed.

A separately pinned next request changes only the anchor's controls/files/32 storage choices. An actual `Job` preflight reproduces every repaired control, world and residual exactly, with zero native failures and the same passing original-reference bounds. No new surface solve or geometry audit is claimed for that preflight. It provides a motion-feasible starting point for further collision correction under the original limits.

This generated cube-skin experiment does not establish production humanoid realism, action correctness, physical plausibility, engine playback or animator cleanup time. Those and broader action/rig/object/partner evidence remain required. All fourteen release evidence arrays stay empty and the single full-project goal remains active.

Immutable ignored local receipt identities:

- Complete repair: `52e1257e44f3818a0b0f45ce63ab4b42317f6a83c46227b03400d4d2f21a2535`.
- Independent every-probe and appended-library replay: `473f81bdf202a0e90052d6e88f92486a475a6591a624a06239648c8b97e646aa`.
- Actual native/reference preflight of the next anchor: `f11c6b13ac17d9ab0bb14f3ef72574ff83a7b93d94944eee4c1e5a79468df4b1`.
