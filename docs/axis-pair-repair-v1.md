# Repairing registered axis-study exports

`scripts/native_axis_pair_repair_job.py` adds a repair entry point for two explicit completed-study formats: `strep-native-control-axis-pair-study-v1` and `strep-native-segment-axis-pair-study-v1`. Existing commands, scientific implementations and receipts remain unchanged. The new command reads each format directly and does not relabel a segment study as a legacy study.

The request schema is `strep-native-axis-pair-repair-job-v1`. Its fields are:

- `job`, `study`, `independent_replay`: each contains a file `path` and exact `sha256`.
- `settings`: integer `maximum_stages` from 1 to 8 and `maximum_probes_per_stage` from 1 to 64.
- `label`: a nonempty label for a separately appended diagnostic clip.

For example, with separately obtained, completed and independently replayed local study inputs:

```powershell
python scripts/native_axis_pair_repair_job.py --request reports/axis-pair-segment-repair-v1.request.json --output reports/offline-segment-axis-pair-repair-v1
```

The public repository does not bundle these ignored study receipts or character payloads. This command requires their original input and artifact files; a copied header alone is insufficient.

Both profiles require the exact original job, input hashes, complete current and archived scientific implementation, artifact inventory, native/geometry clocks, control count, model/export replay and identical replayed fraction records. The segment profile additionally binds the declared immutable cache, its original direct-study producer and replay, every source artifact, all cached derivative columns and the independently checked native segment endpoints. Missing, altered or incomplete lineage is rejected before output creation. Artifact populations and bytes remain bound after preflight. Output must be fresh and outside both the current study and any cached source study.

The command chooses the lowest geometry score among actual exported fractions whose centered motion and original reference bounds pass. Geometry score guides the search; it does not approve a fraction. The continuous controls stay fixed. The existing finite greedy search may add, remove or replace absolute one-neighbor quaternion storage choices within the original acknowledged policy, without accumulating component steps. Every probe is exported, decoded and archived under the original motion/contact/rate/reference constraints. Raw source files remain immutable.

A passing stored-motion and reference result receives the complete original geometry audit and separate appended diagnostic clips. Those clips preserve the existing animation library, binary prefix and scene metadata. Every appended native world must exactly match the repaired export. The original selection stays in place; successful repair does not imply collision-free geometry, physical plausibility or release approval.

The tests use actual GLB exports, decoded native worlds and geometry on generated fixtures. Synthetic protocol receipts exercise parser and lineage rejection; they do not represent a completed model or solver replay. Separate end-to-end experiment evidence is required. Hosted CI success and production-character realism are not inferred from local tests.



## Completed generated-fixture experiment

Added an explicit registered repair entry point for direct and cached-segment axis studies; older commands and receipts remain unchanged. It binds exact jobs, current/archived methods, every study/cache artifact and complete model/export replay, with format-specific lineage and unchanged-point/native-segment checks. Fresh output must stay outside both source study inventories; bytes and populations stay bound after preflight. Fifty-three actual-file fixture/protocol tests pass with zero skips in 277.02s. Synthetic fixture proofs are not model/solver evidence. Attempted the actual matched-segment full-step repair at ninety fixed controls under all original constraints: 7 neighbors, stored failure counts [4, 4, 4, 4, 4, 4, 4, 2], 35 absolute storage choices, final native pass False, contacts 0, original reference pass True. The finite search ends with two linear-acceleration violations on B nodes7/8 at frame48, excess3.368572e-5/1.980144e-4m/s2. Its existing planner only proposes angular-acceleration support, so there are zero planned moves for those remaining failures. No final geometry audit or appended variants are emitted after this failed motion gate; the raw proposal remains separately archived with failed geometry. An independent consumer reproduces every actual probe control/payload/world/residual, absolute choices and original rates/static/reference bounds, without repair/search/storage/job/model/proxy imports or receipt normalization. This failed-motion result has no final geometry or appended clips to replay; the consumer does not certify collision predicates. No original asset selected/approved. The cube-skin fixture does not establish production humanoid realism, action correctness, physics, engine playback or human cleanup. All fourteen release arrays remain empty; the single full-project goal remains active. Next add separately versioned, bounded search guidance for positional-acceleration support while checking every original condition, then continue collision correction under the original contracts and broaden action/rig/object/partner and human/engine validation. No new motion-model inference/training or hosted CI success is claimed.

Immutable ignored local receipts:

- Complete repair: `f9ff21a5beb6f8548bef8a972ae5012eb5e4e4da74090ae1c3b8abaa900269ae`.
- Independent every-probe replay: `8aa3b5858a19637ca9109f403b06676d76c67375a3d35762c73f4fce816de791`.
- Tests: `9a119178625f473b7353d36af3637583bd76e7e558b8f23a04c82d16417d62e5`.
