# Independent partner-motion contexts

This experiment places independently generated actor pairs from the breadth study into explicit scenes: five right-hand handshakes and five left-hand high-fives. All twenty original motion and GLB payloads are preserved. The two actors use distinct prompts and distinct motion payloads; this extends the earlier fixture that reused one generated take for both people.

Initial root XZ positions are 1.1 m apart along Z, with authored yaw 0°/180°. Initial root height and the entire native motion remain unchanged. Handshake palm contact is requested over frames 60–119 of the 180-frame clip; left high-five contact is requested at frame 75 of 150. These placements and times were absent from source generation. The test measures how independently prompted clips behave in this additional context; failure is not presented as failure to obey a constraint the model was never given. There is no per-seed placement, timing search or pose correction to disguise a miss.

The auditor uses the existing geometry-derived palm candidates and all eight SOMA skin weights. It records requested-interval point distance, opposing surface normals, closest approach and timing to an actual qualifying point contact. If no frame meets 30 mm, timing remains null. Handshake grip/fingers, force transmission, balance, reactions and action correctness require additional evaluation. All skin vertices are checked against the other actor's closed triangle mesh in both directions at every discrete frame, with a 5 mm diagnostic; this is not continuous collision, self-collision or triangle-intersection certification. Each scene subsequently imports both actors together into Godot and checks every world bone transform at every frame.

## Preserved memory failure and recovery

The first attempt, `reports/breadth-partners-v1`, exposed excessive RAM use in the existing unpartitioned signed-distance query. The process reached approximately 8.6 GiB working set, reducing system available RAM below the unchanged generation guard's 600 MiB threshold. The breadth supervisor stopped during round 04-b, with 247 earlier clips complete. The partner process was deliberately terminated only after its PID, creation time and command were verified. Partial point diagnostics, progress and `memory-termination.json` remain available; no complete collision result exists for that attempt.

The failed generation attempt is preserved byte-for-byte under `reports/failed-attempts/breadth-v2-round-04-b-memory-01`; `reports/breadth-baseline-v2/memory-recovery-01.json` retains its file hashes, failed state and the recovery decision. No generated takes existed in the failed batch. After checking the frozen implementation, no live worker and restored RAM headroom, the unchanged breadth supervisor resumed, skipped verified completed batches and recreated that batch at its original path. It has since completed round 04-b and advanced to round five. Seeds, requests, model, numerical screens and resource guards were unchanged.

`bounded_partner_surface.py` now partitions the same signed-distance query into groups of 32 vertices. Selection, closed-mesh checks, signed-distance convention and tolerances are unchanged. Tests compare the original and partitioned measurements and verify batch size, counts and global deepest-vertex identity. A two-frame actual handshake probe took 35.74 seconds with a 731.74 MiB peak working set and measured 14.24 mm partner penetration. It is only a two-frame probe, not the full collision result.

The new ten-pair study is frozen under `reports/breadth-partners-v2`. A revision check proves identical actor payloads, placements and contact requests to v1; only copied motion paths and the audit implementation/resource supervisor change. `supervise_partner_study.py` enforces 2 GiB available system headroom and a 2.5 GiB process-tree working-set guard, preserving an interrupted attempt if either is exceeded. These CPU audits still share machine resources with generation; timings are not isolated benchmarks.

## Current evidence and review

The study is running. The first handshake pair (seed 1301) completed its full discrete-frame audit and shared-clock Godot import on September 27 at 14:53 UTC. Its point audit never meets the 30 mm tolerance. Closest palms are 59.3 mm apart at frame 43, before the requested interval. Over the requested interval, maximum distance is 1.022 m and maximum opposing-normal error is 53.3°. Peak partner penetration is 23.43 mm, with 22 of 180 frames exceeding 5 mm. Godot verifies both actors across all 180 frames and all 77 bones, with maximum position discrepancy below 0.00000050 m. This is one pair's completed development diagnostic, not success across seeds or semantic approval; the remaining nine pairs still have independent outcomes to record.

[Open both characters on the shared clock](http://127.0.0.1:8767/reports/breadth-partners-v2/review.html). The page loads original checksum-verified GLBs, retains eight skin weights and exposes every pair/seed, contact-time and closest-approach jumps, pending measurements, source downloads and the frozen protocol. It is a separate diagnostic viewer, not a newly registered Studio scene collection or blind human-review packet. Scene recipes are engine/audit inputs and do not yet have all fields required by Studio's richer scene bundles.

Four focused tests cover placement/height preservation, undefined timing for a miss, opposing-normal direction, query equivalence and bounded partitioning. Four actual served GLBs from handshake/high-five pairs match their retained SHA-256 hashes. No full-suite run or human review is claimed. The full-project goal and all interaction release gates remain open.


## Complete population verified 2026-09-27

The guarded worker finished all ten pairs at 16:11:55 UTC; its original exec handle returned exit code 0. `completion-verification.json` checks the frozen population, original source hashes, all bilateral collision-frame records, twenty actual engine actors, every 77-bone frame count, and 96 retained artifact hashes. All 3,300 actor-frame imports match within 8.35e-7 m position and 2.69e-6 basis-element discrepancy. These are structural checks, not interaction approval.

No pair satisfies its complete requested palm-point interval. Four pairs stay within the 5 mm partner vertex-penetration diagnostic; six fail. One handshake reaches the point tolerance for only 16 of 60 requested frames. No independent ratings exist.

| Action | Seed | Requested contact frames met | Largest requested point gap (mm) | Peak partner depth (mm) | Frames above 5 mm |
|---|---:|---:|---:|---:|---:|
| Handshake | 1301 | 0/60 | 1022.4 | 23.43 | 22 |
| Handshake | 2089 | 16/60 | 1041.8 | 18.99 | 29 |
| Handshake | 3253 | 0/60 | 1135.6 | 20.82 | 3 |
| Handshake | 4099 | 0/60 | 1136.6 | 21.25 | 46 |
| Handshake | 5101 | 0/60 | 1109.9 | 21.20 | 15 |
| Left high-five | 1301 | 0/1 | 273.0 | 0.00 | 0 |
| Left high-five | 2089 | 0/1 | 684.6 | 0.00 | 0 |
| Left high-five | 3253 | 0/1 | 1175.1 | 3.24 | 0 |
| Left high-five | 4099 | 0/1 | 679.2 | 0.00 | 0 |
| Left high-five | 5101 | 0/1 | 206.2 | 26.19 | 4 |

The fixed context and independently generated actors remain unchanged. Placement/contact timing is authored, not inferred from a scene-aware model. This study covers these two development interactions only; its observed failures motivate coupled surface/posture editing but do not establish general interaction capability. The original memory incident, guarded recovery and all outputs remain preserved.
