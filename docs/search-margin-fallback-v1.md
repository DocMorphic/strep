# Retry search margins while retaining physical limits

Contact repair can stop because its extra search margins make a proposal infeasible. The original physical requirements do not become infeasible merely because this initializer fails. `--margin-fallback` now retries initializer margins at factors `1`, `.25`, `.0625`, and `0`, stopping at the first complete usable proposal. The entire sequence shares the existing maximum twenty-second initializer budget. The feature is opt-in; legacy defaults remain unchanged.

Only extra search headroom decreases. Explicit point-feasibility requirements remain in every proposal. Original references, keyed timing, exterior neighbors, control bounds and all nonlinear physical thresholds stay fixed. Retention still requires complete nonlinear improvement, preservation of every protected row and the original exact tangent check. A successful initializer, query or optimized proposal never approves a motion by itself.

The selected factor also controls the ensuing nonlinear solver's search margins. Complete earlier attempts remain archived, sharing only unchanged vector populations and bounds. Window continuation checks ordered factors, failed earlier attempts, the shared declared budget, exact cap floors and policy bindings before replaying every saved observation and accepted decision. Legacy histories retain their original margin policy.

## Source and archived-proposal verification

A fresh isolated fixture passes **332 focused checks across twelve modules**, including native derivative, window, lifecycle, retention, policy and provenance tests. Separately, **115 checks across three modules pass without Torch**. Coverage includes a constrained motion that the original search margins reject but the fallback repairs without losing its passing distance constraint; explicit infeasible grip targets remain failures; unmeasured starts cannot be promoted; changed fallback order, caps, budget, policy and attempted promotion are rejected. The model-free inventory remains 406 Python modules and 39 Node suites.

The saved V3 iteration-six initializer fails after ten supporting-plane rounds. Replaying its recorded cut system remains infeasible even after removing the descent requirement. Removing extra margins makes that cut system feasible, but its proposals fail complete vector replay; they are not usable corrections.

Complete archived vector searches with explicit point feasibility intact reproduce the full-margin failure and find usable proposals at `.25`, `.0625` and `0`. The `.25` proposal requires 37 cut rounds and 5.843 seconds. This supports the bounded fallback experiment; it does not establish nonlinear feasibility or animation quality. No recorded LP optimality certificate is inferred.

## Native experiment

V4 resumes fully verified V3 on box-lift frames 97–99, with eight requested outer iterations, ten inner iterations, trust `.03`, a 300-second local solve budget, row chunks of four and fallback enabled. All original physical limits and the 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM supervisor guards remain unchanged. Raw trials are immutable and retained under ignored reports.

```powershell
.venv/Scripts/python.exe scripts/guarded_window_restoration.py reports/box-lift-authored-height-v1 reports/new-margin-window --frames 97 98 99 --iterations 8 --trust .03 --seconds 300 --solve-iterations 10 --row-chunk 4 --resume-window reports/box-lift-window-restoration-v3/window-97-99 --margin-fallback
```

Both native outer iterations fail at full margins and find complete usable initializers at `.25`; their shared search times are 6.297 and 5.094 seconds. The first initializer's eight nonlinear backoffs all regress protected forearm collision rows. One later optimized 1/32 step passes complete nonlinear and tangent retention. The second iteration reaches the local time limit without another accepted correction; its inner queries are never promoted.

The fully published terminal window has status `interrupted_resource_guard`, with stop `time_or_measurement_budget`, local time 300.812 seconds and 53 measurements. The owned supervisor exits 0 after 485.797 seconds; peak tree RSS is 1,347,657,728 bytes. Unlike the earlier V2 external interruption, this result publishes its retained motion, diagnostics, complete history and hashes and can be replayed before resume.

Independent NumPy replay verifies **54 windows, 162 poses, one retained correction, four margin attempts and twelve proposal archive files**. It checks complete native solver/saved geometry, hashes, recorded epigraph/cap/vector/cut data and nonlinear/tangent decisions. Solver-row error is at most `7.11e-14`; maximum normalized solver-versus-saved-representation difference is `9.31e-6`. The accepted saved float32/projected motion also preserves every conservative margin row. Dense/assembled values match exactly at the resumed seed, with maximum derivative difference `5.329e-15` and measured times 58.000/7.843 seconds.

| Frame | V3 → V4 grip distances, mm | V3 → V4 normal errors, degrees | V3 → V4 box penetration, mm |
| --- | --- | --- | --- |
| 97 | 4.590 / 4.807 → 4.597 / 4.810 | 20.182 / 16.645 → 20.181 / 16.641 | 13.537 → 13.439 |
| 98 | 4.986 / 4.975 → 4.987 / 4.976 | 19.831 / 19.542 → 19.827 / 19.534 | 7.173 → 7.160 |
| 99 | 4.529 / 5.074 → 4.532 / 5.065 | 19.634 / 15.065 → 19.630 / 15.064 | 15.804 → 15.678 |

Maximum normalized violation decreases `1.581510 → 1.568860`; squared violation decreases `53.504345 → 52.771208`. **All three poses still fail.** Normal errors exceed 10 degrees, raw-reference body displacement is 221.578 / 221.868 / 221.553 mm against 220 mm, frame 99's right grip exceeds 4.99 mm, and penetration remains failed. Passing grips, floor and added-speed limits retain passes; raw neighboring speeds are 0.194/0.568, 0.568/0.533 and 0.533/0.314 m/s against 1.5 m/s. This is a small measured improvement, not a solved box lift or a full-clip performance claim.

The subsequent [candidate-curvature repair experiment](candidate-curvature-repair-v1.md) tests bounded local repair of rejected trials and preserves a saved-precision failure. Next enforce retention against the actual saved representation and scale useful correction over the contact interval, then verify complete temporal/surface behavior, rig transfer, engine import and broad arbitrary-action/object/partner/edit/style/held-out cases. No source clip or preview was replaced, and no generation, training, engine import or human review was added. The study provides no full-clip, between-key, dynamics, anatomy, self-collision, engine or human certificate. All fourteen capabilities of the full animation-authoring goal remain unapproved.
