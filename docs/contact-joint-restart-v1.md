# Full-joint restart of retained contact failures

The root-only repair cannot solve every contact miss. In the retained crawl-11 candidate, the maximum horizontal hand-pin error is 5.007995 mm against a 5 mm tolerance. Kick-11 reaches 44.484085 mm horizontally and 63.214993 mm in total. Vertical root translation cannot remove those horizontal errors while rotations and root XZ remain fixed.

The preceding full-joint fits stopped at iteration limits. Their poses remain representable by the original correction spline: recovering controls after restoring held source keys gives maximum rotation-vector errors of 4.31e-8 radians for crawling and 3.20e-8 for kicking. Maximum original-relative rotation changes are approximately 32.34 and 25.27 degrees, below the existing 40-degree budget. These facts justify testing a bounded restart; they do not establish feasibility or motion quality.

## Declared experiment

`scripts/study_contact_joint_restart.py` runs crawl-11 followed by kick-11. Each uses its retained fitted poses as a warm start, six outer fitting stages and up to 120 optimizer iterations per stage. The original run used four stages. Optimizer history and inequality multipliers restart from their normal initial state; only poses carry over.

All twenty existing body-joint controls remain available. Root lift is still bounded by 0–0.22 m relative to the immutable original source, rotation changes by 40 degrees, and root XZ remains fixed. The source also defines point/global rate and floor references. The edit window remains frames 10–109, with 22 held native keys including adjoining endpoints. Those keys are restored exactly before initialization and preserved after fitting.

The method retains tolerance-scaled authored-point constraints, quarter-frame point/rate/floor guards, sparse skin evaluation and the existing physical root-coordinate bounds. It does not apply the new root-only export-feedback repair afterward; that separation identifies what the full-joint restart itself accomplishes.

The comparison changes both initialization and the number of outer stages. It tests this combined configuration, not an isolated causal benefit of warm starts. These remain development examples with authored targets, not held-out actions or naturalness evidence.

## Verification and retained evidence

The runner verifies the historical benchmark, snapshots its current Python/Godot implementation and hashes source, seed, contact-policy and mesh inputs. It recomputes the original point-rate reference before fitting, checks original global-rate ceilings afterward, and verifies root/rotation budgets against the original source rather than the warm seed. Every final candidate is exported and independently audited for pins, per-time floor regression, outside preservation, point/global rates and body flags, then receives an actual engine check. Failed results remain stored and unapproved.

Twenty-nine focused tests pass: eight restart-budget checks, seventeen exact held-pose checks and four initialization checks. The new tests include counterexamples where a candidate fits within a fresh allowance relative to the warm seed but exceeds the original root or rotation budget. The CLI help check also passes.

```powershell
.venv\Scripts\python.exe scripts/study_contact_joint_restart.py --suite reports/contact-breadth-v1 --output reports/contact-joint-restart-v1
```

The output folder must be new. The completed original archive, licensed local assets and pinned Godot acquisition are required. This is a development runner, not an automatically approved Studio correction.

At launch, execution started under a recorded live process identity. Crawling's re-exported warm seed still misses four of 81 pin samples, with a 5.012671 mm maximum. Its point-phase rate limits pass, raw added floor depth is now zero, and all 80 outside samples have exactly zero pose/basis/skin difference. This establishes the restart input; no restarted-fit result was available at launch. The original benchmark and all release approvals remain unchanged.


## Crawling result: improved pin error, still rejected

The six-stage crawl-11 restart completed in 751.60 seconds of fitting, with 1,268 objective evaluations. Pin misses decrease from four to one of 81 samples; maximum error drops from 5.012671 to **5.000419 mm**, still above the original 5 mm limit. Added floor depth rises from zero in the restored warm seed to **5.966434e-7 m** at frame 58.5. Although below the audit's 1-micrometre diagnostic category, this positive raw regression still fails the study's zero-added-depth acceptance rule. Total floor penetration is 0.451898 mm.

All six contact-point rate ceilings and both global joint-rate ceilings pass. Global speed/acceleration are 2.805085 m/s and 80.726064 m/s², below 2.928820 and 91.925525 respectively. All 80 outside-window observations remain exactly unchanged. Original-relative maximum root lift is 0.107177 m and maximum joint rotation change is 32.378312 degrees, within the original bounds.

The same ten body-regression flags present in the warm seed remain, covering pose/joint-speed change and hand/foot/knee support or sliding. No body-quality approval follows from the smaller pin error. Only the first optimization stage stops on relative objective reduction; the other five hit their iteration limits. Neither stopping condition proves feasibility.

Native BVH/GLB and all eight skin influences pass structural checks. Actual Godot playback passes **284 observations**, two requested boundary events, four callback-mutation rejections, forward/reverse playback and unload (maximum actor matrix error 1.17e-6). Completion and input hashes were independently verified. This result is retained as rejected in `reports/contact-joint-restart-v1/crawl-11/`; kicking is now running under the same frozen method.


## Kicking result: smaller pin error, new body/rate failures

The kick-11 restart completed in 576.16 seconds with 951 objective evaluations. The foot-pin maximum decreases from 63.214993 to **48.788524 mm**, and misses decrease from 55 to **48 of 81** samples. It remains far outside the original 5 mm requirement.

Added floor penetration decreases from 0.507360 mm to zero, while inherited total penetration remains 0.518426 mm. All 80 outside-window observations remain exactly unchanged. Original-relative root lift is at most 0.036772 m and rotation change 29.233754 degrees, inside the original bounds.

Several dynamic requirements fail: approach acceleration exceeds its ceiling by 12.273962 m/s², hold acceleration by 24.421953 m/s², release speed by 0.011616 m/s and release acceleration by 0.665051 m/s². Global acceleration is 589.439336 m/s² against a 578.207243 m/s² ceiling. Global speed passes. A new `RightFoot_support_gap_regression` joins the three prior pose/speed/left-foot-slide flags. The smaller target error therefore does not establish an acceptable correction, even relative to the warm seed.

Native export checks and 284 new Godot observations pass, including requested events, callback protections, forward/reverse playback and unload. Maximum actor matrix error is 8.28e-7. Both cases' completion/input hashes and frozen method copies were verified after the worker exited successfully. The complete restart study contributes 568 actual engine observations and **zero approved contact results**. Its outputs remain immutable; the study is terminal and no longer freezes production source changes.

The combined warm-initialization/more-stages experiment improved target errors but did not solve either retained failure. It does not justify further iteration increases as a default, and the kicking outcome must not replace the prior result automatically. Continue export-aware integration separately and investigate the remaining pose/support constraints without weakening the original acceptance limits.
