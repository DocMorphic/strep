# Correct against the exported motion after every proposal

This development experiment tests export feedback on wave seeds 11/22 and crawl seed 22. It keeps the original contact, rate, floor, root-edit and outside-window limits. It preserves the original eight-case benchmark and the earlier rejected alternatives.

The previous [combined correction](preserved-export-repair-v1.md) repaired crawling's approach/global acceleration while introducing a release-acceleration excess. Native checks alone did not prevent that regression.

## First feedback method

Each nonlinear proposal is serialized and exported to BVH/GLB before acceptance. The method measures every requested pin, full-mesh floor depth, point-phase rate, global joint rate and outside-window difference. It preserves previously passing exported groups and serialized native rows, rejects new body flags, and requires the worst normalized exported violation to improve. Failed trial files remain available. Final selected outputs receive actual Godot playback checks.

A rejected exported rate group supplies its measured export/proxy discrepancy to the next search. Search headroom is bounded by horizontal motion. These targets guide proposals; they never change the original acceptance ceilings.

Both waving cases pass after one accepted proposal each, with maximum root adjustments of 1.194783e-6 m and 1.236345e-7 m. Their original exported pin/rate/floor limits, serialized constraints, exact outside preservation and body-regression checks pass.

For crawling, the first proposal reproduces the new release-acceleration excess of 1.610748e-6 m/sÂ². The export gate rejects it even though it improves the worst error and preserves previously passing serialized rows. The following proposal is infeasible with the extra release search target. No change is accepted; the final selected native motion is byte-identical to the restored seed and remains rejected for its original approach/global acceleration failures.

All three final selected outputs pass 284 actual Godot observations each: 852 new observations, with requested events, callback protections, forward/reverse playback and unload. Engine success does not approve the retained crawling motion.

## Joint search margin diagnosis

The newly added release target has approximately 1.76e-8 normalized measured discrepancy plus 1e-4 optional headroom. Its individual horizontal capacity is sufficient, but that does not prove that all groups' search targets can be satisfied together.

A separate read-only diagnosis tests optional-headroom multipliers 1, 0.1, 0.01, 0.001 and 0 while retaining every measured discrepancy and original limit. The full optional target is infeasible in the local linear subproblem. Multipliers 0.1, 0.01 and 0.001 yield proposals with nonnegative unrounded and serialized constraints. Discrepancy alone yields a small negative serialized slack. These are numerical proposals, not verified exported repairs.

The follow-up method therefore reduces only optional headroom after linear infeasibility. It retains the maximum observed discrepancy for every learned group and applies the same actual-export acceptance checks. No original budget is relaxed, and no failed group is removed.

## Second method: all three alternatives pass

The second method preserves the two waving native outputs exactly. Crawling rejects the first exported regression, finds the full optional margin infeasible, then retries at 0.1 of the optional headroom. The measured discrepancy allowances remain intact. This second proposal passes and is accepted; no failing exported group is moved elsewhere.

| Crawling check | Final result | Original ceiling |
| --- | ---: | ---: |
| Requested hand-pin error | 4.761054 mm maximum; 0/81 failures | 5 mm |
| Approach acceleration | 107.768438 m/s² | 107.769558 m/s² |
| Release acceleration | 89.816353 m/s² | 89.817280 m/s² |
| Global joint acceleration | 113.578111 m/s² | 113.579188 m/s² |
| Full-mesh floor depth / added depth | Both zero | No added depth |
| Outside-window joint/basis/skin difference | Exactly zero, 80 observations | Preserve held motion |

All other point/global rate limits pass, serialized minimum constraint slack is nonnegative, and body evaluation adds no flags. Maximum root change is 1.750220e-6 m. All three second-method outputs pass 284 new Godot observations each, another 852 observations with events, callback protections, forward/reverse playback and unload. Native BVH/GLB and eight-weight checks pass. The two experiments therefore produced 1,704 new engine observations in total; they do not alter the original benchmark's one-of-eight contact-screen result.

The measured function bodies are published in `scripts/study_export_feedback.py`. The command-line wrapper accepts explicit paths and requires a new output folder. The archive, licensed character assets and pinned local Godot acquisition must already exist; this is an experimental study runner, not a standalone installer or a Studio default.

```powershell
.venv\Scripts\python.exe scripts/study_export_feedback.py --suite reports/contact-breadth-v1 --output reports/export-feedback-reproduction
```

All seven solver/export/engine function bodies were checked for identical syntax trees against the measured second implementation. Seven self-contained policy tests pass for the published runner, and its help command passes without launching a study. The path wrapper was not used to rerun the expensive experiment; the equivalent measured prototype supplied the actual results above.

## Evidence and scope

The first experiment is retained in `reports/contact-breadth-v1/export-feedback-v1/`; its diagnosis is `crawl-22/optional-margin-diagnosis.json`. The second implementation and policy tests are retained separately under `export-feedback-v2.py` and `test_export_feedback_v2.py`. Seven isolated policy checks pass for the second method, including the real prior crawling regression, unchanged acceptance ceilings, geometry-limited search margins and retained discrepancy during optional-margin reduction. Six corresponding checks pass for the first method.

These tiny root adjustments address measured numerical failures. They do not establish visible naturalness, whole-foot support, force balance, or a general joint-pose solution. Larger crawling/kicking pin failures and all release capabilities remain unresolved. No human rating or cleanup time is claimed.
