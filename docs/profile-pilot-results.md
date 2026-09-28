# Character profiles and varied takes — executed milestone

Completed 2026-09-24. [Open the local viewer](http://127.0.0.1:8767/reports/profile-pilot-v1/viewer.html), or serve the project root and open `reports/profile-pilot-v1/viewer.html`.

Five movement descriptions were genuinely encoded locally and generated at three shared seeds each. All 15 raw takes, processed loops and character exports are retained. Thirteen pass the combined source numerical screens. This demonstrates a working profile/take authoring prototype and measurable variation; it does not establish calibrated agility, strength or endurance controls, reliable prompt compliance, professional realism, or engine acceptance.

## What the author can do

Select neutral, parkour-trained, sprint technique, backpack running or fatigued running, then choose one of three takes. Compare the selected raw interval against loop/stance correction, or switch to the complete raw clip. Play, scrub, change camera/speed, inspect failures, and download GLB/BVH/NPZ assets. Each GLB contains full raw, selected raw cycle and processed loop animations. Repeated cycles accumulate root motion; playback stops at the end.

The viewer can hide profile labels for exploratory review and export user-entered ratings. This is label hiding, not secure or independently administered blinding. No human judgments were invented or recorded during implementation. A new movement description can be exported as a study JSON request for the local pipeline. It requires genuine new encoding and generation; editing text does not alter the saved clips in the browser. Capability numbers remain metadata.

## Protocol and provenance

The [research and frozen protocol](profile-pilot-research.md) links primary sources and explains the choice of concise descriptions, shared root-path constraints and separate quality/style measurements. Kimodo recommends moderate descriptive detail and cautions about conflicting constraints; dense root paths are a supported exception. [Official guidance](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html).

- Configuration: `benchmarks/profile-pilot-v1.json`, SHA256 `9d51d505f8ab35e0696731d92af6832ff884a7c243dd95915e8d35dead4fb487`.
- Seeds 11, 22, 33; 120 frames at 30 fps; requested straight path 3 m/s; 100 denoising steps; separated guidance weights [2, 2]. Four seconds of samples has its last key at 119/30 s.
- Unchanged motion checkpoint Kimodo-SOMA-RP-v1.1, revision `6c9233af1180b8151e3c4703477104af5dce3ad9`; source commit `58e781898b3d7e328a676a75d3e338c45dce3ad9`.
- Five new prompt embeddings in `models/prompt-cache-profile-pilot-v1/`. Exact prompts, tensor hashes, encoder revisions and loader hashes are recorded. The BF16/FP32 disk-offload encoder remains an experimental execution variant: tiny-model equivalence passed, full resident 8B equivalence remains untested.
- RTX 3070 Ti 8 GB, Ryzen 6900HX, 16 GB RAM. Encoding and raw generation ran offline in about 5 minutes 28 seconds; raw generation was approximately 7–8 seconds per take after model load. Measured encoder process-tree peak was 3.10 GiB. This excludes the earlier weight downloads and later processing/review.
- Frozen loop search and stance IK configurations were reused unchanged. Every candidate and failed take remains available. Target transfer uses the existing CesiumMan mapping and its 0.633 leg-length scale.

## Findings and failures

All 15 raw clips meet the mean-speed tolerance, but 14 fail the pelvis-path p95 screen. The path diagnostic compares pelvis XZ to the requested straight path relative to its initial point; it is not the vendor's smoothed-root constraint error. Selected/corrected loops are a different condition and must not be presented as full-clip raw compliance.

The final source pass counts are neutral 3/3, parkour 3/3, sprint 1/3, backpack 3/3 and fatigued 3/3. Sprint seed 22 fails the root-velocity seam check. Sprint seed 33 fails that check plus mean speed and pelvis-path tolerance; its processed speed is about 3.50 m/s. Both remain selectable and visibly flagged.

Source acceptance combines the pre-existing loop, distortion, sliding-regression and stance-improvement rules with speed within 5% and pelvis-path p95 at most 0.10 m. These are engineering screens, not perceptual standards. In particular, the sliding limit is relative to the source baseline: fatigued seed 11 passes while still having predicted-contact speed p95 of 11.8 cm/s. No pass badge means perfectly planted feet.

Backpack and fatigued descriptions increase forward lean. The sprint description often increases arm swing. The requested compact parkour arm swing is not reliably obeyed; its mean arm range exceeds neutral. Requested sprint forward lean is also not established. Three seeds do not estimate general reliability, and no animator has approved these clips.

Selecting a short repeated interval removes some full-clip characteristics: sprint mean arm range falls from about 103° over the full raw clips to 73° in selected raw cycles, then 66° after correction. Fatigued arm range falls from about 50° to 28° at selection. The full-raw comparison is essential for seeing this loss. Selection and correction must be evaluated separately.

Phase-aligned, root-centered pose distances also show within-profile variation. Among pairs where both source takes pass, median within-profile distance is 0.131 m raw and 0.126 m processed (12 pairs); matched-seed between-profile distance is 0.209 m raw and 0.208 m processed (22 pairs). Including failures gives 0.120/0.116 m within and 0.182/0.183 m between. These descriptive distances are not proof that people recognize the intended style, nor a trained classifier or significance test.

After retargeting, arm-swing and loaded/fatigued lean differences remain measurable. Absolute source and target torso angles use different joint/rest geometry and should not be equated. Target world speed is approximately 1.9 m/s because of rig scaling, with the failed sprint take around 2.22 m/s. Sampled character floor penetration reaches 0.80 mm; predicted-support foot mesh height reaches 3.33 cm. These are sampled mesh/label proxies, not continuous collision checks or independent contact annotations. Target foot placement remains unfinished.

## Measured profile comparison

Means over all three seeds, including flagged sprint takes. Angles are descriptor proxies. Individual values and every flag remain in the viewer and summary.

| Profile | Source passes | Full raw arm range | Selected raw arm range | Processed arm range | Target arm range | Source processed lean | Target lean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Neutral runner | 3/3 | 44.6° | 40.9° | 40.7° | 40.0° | 2.6° | -2.4° |
| Parkour-trained | 3/3 | 55.6° | 51.6° | 49.8° | 48.1° | 0.6° | -4.5° |
| Sprint technique | 1/3 | 103.0° | 72.5° | 65.9° | 64.0° | 0.9° | -5.6° |
| Backpack running | 3/3 | 14.5° | 7.8° | 8.4° | 7.3° | 17.3° | 7.9° |
| Fatigued parkour runner | 3/3 | 50.0° | 28.2° | 26.8° | 25.6° | 17.2° | 6.4° |

## Verification

- 31 tests pass, including path/speed screens, phase-distance behavior, safe identifiers, cache integrity, unknown-prompt rejection and returned-tensor isolation, plus the previous motion/correction tests.
- All 15 GLBs have zero Khronos validation errors. Each retains one inherited non-root skinned-mesh warning and 76 informational notices about unused original data. Validation is not a game-engine import test.
- Exported GLB animations were read back and CPU-skinned at every key; each maximum vertex round-trip error is below 0.00001 m. Processed BVH round-trip errors are recorded per take. Additional floor samples include midpoints.
- All 15 raw/processed/GLB hashes and all 25 historical raw-generation hashes verify. No earlier study was replaced.
- A separate neutral seed 11 generation reproduces all seven stored arrays exactly, including the NPZ hash. This checks one same-device cached-conditioning repeat, not all 15 reruns or full encoder equivalence.
- Browser checks cover profile/take changes, playback, scrub, cameras, full-raw comparison, failure status, label hiding and review fields. No browser console errors were observed. No fabricated human ratings were saved.

Machine-readable evidence is in `reports/profile-pilot-v1/summary.json`, `character-summary.json`, `character-quality.json`, `gltf-validation-summary.json`, and `verification/report.json`. Per-take records retain exact prompts, constraints, seed, timing, asset/checkpoint hashes and exports. The implementation snapshot records the files used to reproduce this milestone.

## Reproduce or generate another request

Use the prepared environment and local model files. Choose a fresh report directory when changing a study. The first command only encodes/generates; subsequent commands process, measure and build the viewer. This keeps original attempts available.

```powershell
cd C:\wassup\strep
.venv\Scripts\python.exe scripts/run_profile_pilot.py --study benchmarks/profile-pilot-v1.json --output reports/profile-pilot-repeat
.venv\Scripts\python.exe scripts/process_profile_pilot.py reports/profile-pilot-repeat --study benchmarks/profile-pilot-v1.json
.venv\Scripts\python.exe scripts/profile_metrics.py reports/profile-pilot-repeat --study benchmarks/profile-pilot-v1.json
.venv\Scripts\python.exe scripts/export_profile_characters.py reports/profile-pilot-repeat
.venv\Scripts\python.exe scripts/measure_profile_characters.py reports/profile-pilot-repeat
node scripts/validate_profile_exports.mjs reports/profile-pilot-repeat
.venv\Scripts\python.exe scripts/build_profile_viewer.py reports/profile-pilot-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

For an exported custom request, substitute its path for `--study` in the first three commands and use a fresh folder. Encoding unknown descriptions can take minutes on this laptop. If the viewer server has stopped, run `.venv\Scripts\python.exe -m http.server 8767 --bind 127.0.0.1` from the project root, then open the viewer URL.

## Next evidence needed

First make individual controls predictable: freeze speed and seeds, vary one requested feature at a time (cadence, arm range, lean or fatigue), test dose ordering and source/rig preservation, and collect blind identification/naturalness ratings plus animator cleanup time. Then define a versioned mapping from gameplay stats to measured motion targets. Do not relabel a prompt adjective as a calibrated agility slider. Compare deterministic controls with text-only generation before deciding whether training is justified.

Fix target foot placement and test an actual engine import alongside that study. Later test whether the selected identity survives runs, jumps, vaults, rolls and interactions on held-out rigs. Object/partner geometry, strength/load dynamics, endurance over time and cross-action character identity are still open problems. The broader authoring scope remains intact.
