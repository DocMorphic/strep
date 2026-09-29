# Crawl result: root height alone cannot repair the remaining pin error

The second case in the [frozen breadth study](contact-breadth-v1.md), crawl seed 11, has completed. Its authored left-hand pin misses the original 5 mm limit at **4 of 81** exported samples; maximum error is **5.012671 mm**. All six point speed/acceleration ceilings pass. The root-only repair rejects its linear subproblem and retains the fitted candidate unchanged.

This is a different failure from [wave seed 11](contact-breadth-wave-v1.md). With the fitted rotations and root XZ fixed, the pinned material point's horizontal distance from the target reaches **5.007995 mm at frame 53**. Vertical root movement cannot change that horizontal distance. Therefore no root-height-only correction can satisfy every 5 mm pin sample for this retained pose, even with a larger vertical step or no extra interior margin. This does not establish infeasibility when joint rotations are allowed to change.

Read-only linear diagnostics also reject the original 10-micrometre trust box without extra margin and a 100-micrometre box without extra margin. No alternate motion was produced. Increasing the root trust radius alone is not a solution to the demonstrated horizontal error.

## Other measurements

The fit used 632 evaluations: four 120-iteration stages with 133, 152, 161 and 182 evaluations, plus accepted-point recomputations. All stages reached their iteration cap; final projected-gradient infinity norm is 129.40. The recorded full case took 593.88 seconds before its separate engine check.

Maximum exported floor penetration is **0.451884 mm**. Raw per-time added depth is **4.8368e-9 m**, at frame zero; no sample exceeds the audit's existing 1-micrometre export-precision classification budget. The raw difference is retained. The stricter study screen requiring exactly zero added depth does not pass.

All 80 outside-window observations pass numerical preservation, with maximum skin-position error 7.76e-8 m. Held root coordinates are exactly equal to the source; reconstructed held local/global matrices differ by at most 5.96e-8 and joint positions by 2.98e-8 m. A locked floor row in the root proxy has a tiny negative slack that root-only editing cannot change. Exact preservation of held source arrays/export channels warrants separate investigation after the frozen batch; these differences are not silently waived or rewritten.

The source already had a left-hand support-gap flag. The result retains that flag and adds nine pose/speed/support flags: excessive pose displacement and added joint speed, hand surface sliding, foot/hand support gaps and knee support gaps. Passing the pin alone would not establish acceptable motion quality for this request.

Actual Godot playback passes **284 pose observations**, two requested-boundary events, four callback-mutation rejections, forward/reverse playback and unload. Maximum actor matrix component error is 1.16e-6. Exported global speed/acceleration peaks, 2.908122 m/s and 91.657017 m/s², remain below their original ceilings of 2.928820 and 91.925525. Engine compatibility does not approve the motion.

Local evidence is in `reports/contact-breadth-v1/cases/crawl-11.json`, `engine/crawl-11/verification.json` and `crawl-11-root-diagnosis.json`, with immutable source/fit/repair jobs under `reports/contact-jobs/contact-breadth-v1-crawl-11-*`. Imported source and the eight-case protocol remain unchanged. No new test run, browser check, human rating or cleanup time is claimed. Two cases are complete; six remain pending, and the original batch has advanced to kicking.

After the fixed batch is accounted for, test corrections that can adjust bounded joint rotations as well as root height, retain the original constraints and measure support regressions. Root-only polishing remains useful for some near-feasible clips, but the crawl result demonstrates why it cannot serve as the general correction method. All release capabilities remain unapproved.


## Isolated held-pose restoration diagnostic

A separate export diagnostic copied the original source root, joint positions and local/global rotation arrays at the 22 locked keys, including both edit-window boundaries. All free candidate keys remained exactly unchanged. This removed the measured reconstruction drift: all 80 outside-window decoded observations now have exactly zero pose, basis and skin difference, and maximum raw added floor depth becomes zero. The four pin failures, pin maximum, six phase-rate excesses and whole-clip global rate peaks remain unchanged. All ten body/support flags remain.

The diagnostic passes native BVH/GLB checks and 284 additional actual Godot pose observations, including requested events, callback protections, forward/reverse playback and unload. Maximum actor matrix error is 1.17e-6. Evidence and the isolated method are retained under `reports/contact-breadth-v1/crawl-held-restoration-v1/` and `diagnose-held-restoration.py`. Original inputs and implementation hashes were reverified before and after. This is an additional diagnostic, not a replacement for the frozen crawl result.

The source of the drift is the unconditional reconstruction path, which projects local rotations onto SO(3), runs forward kinematics and casts to float32 at held keys too. The next implementation should restore held pose arrays from the correct seed after reconstruction and audit actual export segments and boundary dynamics. Warm-start handling and other windows still need regression coverage before integration. No live batch code changed, no default was promoted and no human quality was inferred.
