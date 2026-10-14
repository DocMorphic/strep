# Native transfer across actions and character rigs

The population runner `scripts/native_transfer_population.py` applies the existing model-free rig-to-rig transfer to every caller-declared source/target pair, then evaluates source and output skin against an explicit horizontal floor at a shared clock. Action names are metadata, never a supported-prompt whitelist. Transfer fidelity, sampled floor clearance and motion quality remain separate.

## Reproducible protocol

The protocol schema is `strep-native-transfer-population-v1`, with `rate_hz` (60, 120 or 240), explicit `floor` (`y_m`, `tolerance_m`), a scope description and 1–96 unique cases. Each case has an ID, string metadata labels, a source GLB/profile with exact SHA256 digests and animation index, and a target GLB/profile with exact digests. Relative input paths resolve against the protocol. The prepared study stores canonical absolute bindings, original protocol bytes, implementation snapshots and the fixed frame-clock contract.

```powershell
python scripts/native_transfer_population.py prepare protocol.json fresh-study --protocol-sha256 TRUSTED_PROTOCOL_DIGEST
python scripts/native_transfer_population.py run fresh-study
```

Use the existing guarded job workflow for resource admission and owned-process limits. The runner's 700-second default budget is checked before starting another case, not a hard per-case deadline. It leaves all remaining rows explicitly pending and marks a phase-budget deferral. After verifying that the old runner really exited, an explicit `run fresh-study --resume` revalidates original inputs, methods, complete per-case artifact inventories and sealed summaries before skipping terminal rows. Interrupted attempts remain preserved, and a new attempt is written separately. A completed population cannot be restarted.

Every transfer preserves the existing original-target-payload and interpolation checks. A measured failed-fidelity export remains eligible for a separate floor diagnostic and stays a failed-fidelity candidate. Unsupported inputs or other execution failures are retained as failed rows with unavailable floor measurements. No row is discarded or assumed to pass. The diagnostic clock unions every source and target native key and midpoint, both endpoints and all twelve predeclared 30/60/120-Hz phase populations. Exact deduplication is used; there is no temporal decimation. Every loaded mesh vertex is evaluated.

The result records complete rows, execution failures, fidelity passes and floor passes separately. A floor pass cannot establish planting, semantic correctness, balance, contact with objects/partners, continuous collision freedom, engine playback or animation quality. The tool neither edits source motions nor selects proposed assets for production.

## Development population

The frozen study uses all seven existing seed-77 Kenney development transfers (jump/land, crawl, dance, wave, kick, get-up and run/roll/stand), plus the previously sampled-passing corrected crawl. Each is transferred to CesiumMan and Quaternius female/male: 24 planned source/target cases. These are three target assets from two skeleton families, reused development motions and one previously corrected action; they are not held-out release evidence. Original input, failed correction and model records remain unchanged. Native source profiles retain the prior transfer's explicit role mapping and default reference, with their checksum rebound to each actual source GLB.

The first read-only preflight retains 21 eligible raw-transfer rows and three rejected corrected-crawl rows. The latter are an authoring mistake: the requested index 1 does not exist in the single-animation corrected GLB. No transfer is attempted for them. A separate v2 protocol selects its actual index 0, as recorded by the native developer packet, while retaining the other 21 cases. The first preflight and its 55-observation resource trace remain saved and independently replayed; this is not a generator failure or an omitted action.

The population/source regression batch passes **33 checks in 45.10 seconds**, including real generated-rig exports, complete fractional clocks, exact original payload retention, malformed protocol rejection and resume/summary/artifact tamper checks. Its guard completes in 92.391 seconds including 45.469 seconds admission, with all 93 observations independently replayed. Software fixtures are not production anatomy or independent animator evidence. The actual 24-case study is recorded under ignored `reports/native-transfer-generalization-v2`; source/preflight records remain under `reports/native-transfer-generalization-v1`.

Source models and weights remain unchanged. No new inference/training or human cleanup review is performed. All fourteen release capabilities and calibration gates remain unapproved under the full-project goal.

## Scope of source corrections

The source crawl correction previously passed its own 2,017-time geometry clock and original source motion caps. This transfer study does not inherit that pass automatically. Each target is a separate rig with its own proportions/reference calibration and a newly combined source/output clock. Source and target skin depth are measured again. Contact annotations are absent from native rig transfer; low penetration cannot establish that hands, knees or feet meet an intended support surface. Floor-only outcomes therefore remain diagnostic even if every source/target pair clears the declared plane.

This runner currently assumes one coordinator per study. Numerical phases use the shared project OS lock, and explicit resume checks the recorded runner PID/birth before reusing a started study. Simultaneous initial submissions to the same newly prepared folder are not a supported orchestration contract. This does not affect the single-coordinator measurements here; a per-study coordinator mutex is still a software follow-up.

The final ten new runner tests additionally force a known floor failure while the generated transfer still passes fidelity; the two results remain separate. All ten pass in 10.18 seconds, with a 27.406-second guard and all 29 resource observations replayed. The original broader 33-check batch remains preserved separately.

The actual first phase completes 19 rows, then defers before starting case 20 at its unchanged phase-start budget. Its guard completes in 728.703 seconds (712.532 seconds execution; 15.125 seconds admission), peak worker-tree RSS 147,152,896 bytes, with all 716 recorded resource observations replayed. This is successful bounded partial execution, not a complete-population result. The five pending rows retain their identities. The resumed phase revalidates complete receipts and source/method bindings before reusing the 19 terminal rows.

The raw/corrected crawl comparisons retain identical source static node/mesh/skin/scene/material/texture JSON, mappings, scale, root offset, reference calibration and exact comparison clocks. Raw target floor failures are 0/0/672 for CesiumMan/female/male; the corrected variant has 0/0/0. This is a controlled sampled-floor effect of the changed source motion in these pairs, not a semantic or physical approval. Other action rows remain required for the complete population.

## Completed 24-case outcome

All 24 transfers and paired floor measurements complete, with no execution failures. All 24 pass the original interpolation fidelity and original target-payload checks. Seventeen pass the sampled target floor screen; seven fail. The table reports failing floor observations, with the complete denominator retained:

| Source condition | CesiumMan | Quaternius female | Quaternius male |
| --- | ---: | ---: | ---: |
| Jump / land | 0 / 2,829 | 0 / 2,829 | 0 / 2,829 |
| Raw crawl | 0 / 2,829 | 0 / 2,829 | 672 / 2,829 |
| Corrected crawl | 0 / 2,829 | 0 / 2,829 | 0 / 2,829 |
| Dance | 0 / 3,560 | 0 / 3,560 | 0 / 3,560 |
| Wave | 0 / 2,829 | 0 / 2,829 | 0 / 2,829 |
| Kick | 0 / 2,829 | 0 / 2,829 | 0 / 2,829 |
| Get-up | 1,473 / 4,292 | 2,086 / 4,292 | 2,165 / 4,292 |
| Run / roll / stand | 303 / 5,024 | 310 / 5,024 | 330 / 5,024 |

The raw male crawl reaches 20.646 mm target floor depth; its corrected counterpart has zero measured depth. The get-up target peaks are 131.841, 224.082 and 297.651 mm; the roll sequence peaks are 209.026, 221.728 and 272.269 mm. These failures remain in their original exports. Compared bodies have different proportions, so source/target peak changes alone cannot isolate a causal rig defect or certify natural motion.

The resumed phase completes the five pending rows without repeating the first 19. Its guard completes in 323.875 seconds (307.735 seconds execution; 15.109 seconds admission), peak worker-tree RSS 154,406,912 bytes. All 320 observations independently replay. Together the two phases account for every declared source/target case. The complete result SHA256 is `4a17b6a622da9e968f800fafcf14d78bab33f0a05e8cdb63302182a4bde684a0`.

An additional retained lineage ledger binds all seven original native motion hashes and transfer reports, the corrected crawl receipt, target catalog and attribution files. Generated characters, snapshots, model data and detailed study outputs remain excluded from public Git. The public source snapshot still requires separately acquired inputs/runtime.

The next correction target is ground recovery and roll clearance under explicit movement/contact bounds, with get-up kept distinct from the already corrected crawl. A root-only proposal must first demonstrate feasibility under its own unchanged source epoch and declared displacement limits; it cannot silently enlarge budgets or count a floating body as planted support. Source/target skin checks, contacts, temporal bounds, engine behavior and human motion review remain separate requirements. No release gate or production selection changes from this population.

A final read-only verification rehashes all **576 sealed case artifacts**, validates original source/method bindings, rebuilds every expected source/target native/midpoint/twelve-frame clock and reduces all recorded floor minima/depths/gates again. It checks **81,063 paired clock observations** (162,126 source/target pose-time entries) and all 24 case summaries. Every case has exactly one retained export attempt, confirming that resume reused the original 19 completed cases. This check does not rerun transfer, sample poses or independently reconstruct full floor geometry. Its guard completes in 22.344 seconds with all 24 resource observations replayed. Exact exported poses/skin floor measurements remain the producer's recorded observations; no independent physics or human claim follows. Public inventories now declare 502 Python/45 Node files and 65 focused Python/5 Node files.
