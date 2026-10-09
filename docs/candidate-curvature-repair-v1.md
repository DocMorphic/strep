# Repair rejected curved contact trials

An apparently feasible linearized pose step can regress collision rows after complete native geometry evaluation. Strep now offers `--trial-correction`: a bounded local repair of rejected geometry-start backoffs at fractions `.25` and `.125`, with at most two repair attempts per outer iteration. The feature is opt-in and preserves legacy defaults.

The motivation follows bounded corrective trial steps in [Ipopt's line-search documentation](https://coin-or.github.io/Ipopt/classIpopt_1_1BacktrackingLineSearch.html). Strep's implementation uses a minimum-L1 linear program at the measured candidate Jacobian. It retains the original acceptance rules and does not supply a Hessian, global convergence or curvature certificate.

Each correction includes every original scalar row and the original seed-tangent protection rows. Explicit point-feasibility requirements remain in its proposal targets. Correction coordinates are limited to one quarter of the original normalized trust radius and clipped to the original rig/control/trust bounds. Each LP has at most twenty seconds within the existing overall solve budget. Complete nonlinear geometry, original worst/squared-error improvement and exact original tangent preservation determine retention.

Correction archives bind the candidate, original base, parent rejection, full candidate Jacobian, slacks, targets, limits and LP output. A separate attempt identity permits multiple immutable corrections in one outer iteration. Window resume checks policy, unretained proposal status, parent identity, full linear replay, local/original bounds and the resulting child controls before replaying nonlinear retention. Partial, unmeasured or rejected proposals cannot replace the last accepted pose.

## Verification

A fresh isolated fixture passes **346 focused checks across twelve modules**. Separately, **126 checks across three modules pass without Torch**. Coverage includes a curved surface that rejects an ordinary geometry step, an accepted repaired step preserving the original surface constraint, call-budget expiry, invalid candidate derivatives, correction-archive identity and attempted proposal promotion. The model-free inventory remains 406 Python modules and 39 Node suites.

The owned V5 diagnostic study evaluates existing rejected V4 trials without changing the source motion. A single local repair makes the `.125` and `.25` candidates eligible under complete native nonlinear/tangent retention. They remain diagnostic and unpromoted. These measurements motivate the integrated V6 experiment; they do not provide a release certificate.

## Integrated native experiment

V6 resumes fully verified V4 on authored-height box-lift frames 97–99 with eight requested outer iterations, ten inner iterations, trust `.03`, a 300-second local solve budget, row chunks of four, bounded search-margin fallback and trial correction enabled. Original timing, references, exterior keys, physical limits and 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM supervisor guards stay fixed.

```powershell
.venv/Scripts/python.exe scripts/guarded_window_restoration.py reports/box-lift-authored-height-v1 reports/new-corrected-window --frames 97 98 99 --iterations 8 --trust .03 --seconds 300 --solve-iterations 10 --row-chunk 4 --resume-window reports/box-lift-window-restoration-v4/window-97-99 --margin-fallback --trial-correction
```

V6 completes all eight requested iterations in 250.485 local seconds, with 66 measurements and no nonlinear inner-solver queries. Two repaired steps are accepted, at `.25` and `.125`; five ordinary 1/64 steps and one ordinary 1/128 step are also accepted. Fifteen local correction proposals are recorded, including thirteen whose repaired children are rejected. The owned supervisor exits 0 after 506.703 seconds, with peak tree RSS 1,333,104,640 bytes. This is a measured local study, not a matched full-clip speed comparison.

Independent NumPy replay verifies **67 windows, 201 poses, eight solver-retained decisions, eleven margin attempts, fifteen correction proposals and 93 proposal archive files**. It checks original/method/output hashes, complete native solver/saved geometry, correction caps/bounds/parent links, recorded vector/epigraph/cut data and nonlinear/tangent decisions. Later proposal derivatives and LP optimality are not independently certified. Dense/assembled seed values match exactly, with maximum derivative difference `5.329e-15` and measured times 64.812/8.907 seconds.

| Frame | V4 → V6 grip distances, mm | V4 → V6 normal errors, degrees | V4 → V6 box penetration, mm |
| --- | --- | --- | --- |
| 97 | 4.597 / 4.810 → 4.727 / 4.849 | 20.181 / 16.641 → 20.168 / 16.610 | 13.439 → 12.417 |
| 98 | 4.987 / 4.976 → 4.989 / 4.972 | 19.827 / 19.534 → 19.826 / 19.411 | 7.160 → 6.982 |
| 99 | 4.532 / 5.065 → 4.581 / 4.995 | 19.630 / 15.064 → 19.628 / 15.061 | 15.678 → 14.289 |

Maximum normalized solver violation decreases `1.568860 → 1.429993`; squared violation decreases `52.771208 → 44.333584`. **All three poses still fail.** Normals exceed 10 degrees, raw-reference displacement is 221.533 / 221.858 / 221.530 mm against 220 mm, frame 99's right grip exceeds 4.99 mm, and penetration remains failed. Passing grips, floor and speed gates remain passing. Raw neighboring speeds are 0.386/0.610, 0.610/0.582 and 0.582/0.532 m/s against 1.5 m/s.

## Saved-representation failure and next work

Solver rows replay within `6.79e-14`, but float64 solver geometry and saved float32/projected geometry differ by up to `9.71e-6` in normalized rows. **Saved-motion preservation fails at the seventh accepted step:** frame 99's right palm-normal row changes from `-0.5038738572752868` to `-0.5038740690617981`; its physical angle increases `15.061488267 → 15.061490400` degrees. Every solver-retained decision passes float64 retention, but this small saved-row regression violates the intended strict failed-row preservation. The thresholds are not relaxed to hide it.

V6 stays diagnostic and is not promoted as the next motion origin. V4 remains the latest terminal window whose accepted saved representations all preserve every conservative margin row. Next add retention against the actual saved representation before accepting a trial, then repeat the correction experiment and expand useful repair across the contact interval. Complete temporal/surface, rig-transfer, engine, arbitrary-action/object/partner/edit/style/held-out and developer cleanup evidence remain necessary. No source clip or preview was replaced, and no generation, training, import or human review was added. The experiment provides no full-clip, between-key, anatomy/dynamics, self-collision, engine or human certificate. All fourteen capabilities of the full animation-authoring goal remain unapproved.
