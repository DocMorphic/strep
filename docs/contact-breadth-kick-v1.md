# Kick result: contact fitting remains incomplete

The third case in the [frozen breadth study](contact-breadth-v1.md), kick seed 11, fails the requested left-foot pin at **55 of 81** exported samples. Maximum error is **63.214993 mm**, against the unchanged 5 mm limit. Root-height repair rejects its linear subproblem and preserves the fitted motion byte-for-byte. This is a retained failed development case, not a supported-action certification.

The decoded GLB material point has **44.484085 mm horizontal error at frame 50**. Vertical root movement cannot remove this error while joint rotations and root XZ remain fixed. As with [crawling](contact-breadth-crawl-v1.md), this establishes a limitation of root-height-only repair for the retained pose; it does not prove that the full joint-pose problem is infeasible. The deterministic pin request also does not establish that holding this foot through the specified interval is semantically appropriate for the kick.

## Measurements

The complete fit/repair case took 504.13 seconds before separate engine verification. The pose fit used 529 evaluations: four stages of 120 iterations, with 126, 131, 134 and 134 function evaluations plus accepted-point recomputations. Every stage reached its iteration limit. No optimizer convergence or training result is claimed.

| Exported check | Result |
| --- | --- |
| Pin error | 63.214993 mm maximum; 55/81 samples fail |
| Approach point speed/acceleration | Both original ceilings pass |
| Hold point acceleration | Exceeds original ceiling by 12.214948 m/s² |
| Release point speed | Exceeds original ceiling by 0.022773 m/s |
| Release point acceleration | Exceeds original ceiling by 0.850108 m/s² |
| Full-mesh floor penetration | 0.565326 mm maximum |
| Per-time added floor depth | 0.507360 mm maximum at frame 67; two samples exceed the existing 1 µm precision classification budget |
| Outside-window preservation | All 80 observations pass numerical tolerance; maximum skin error 6.06e-8 m |

Hold speed also passes. The floor result illustrates why a lower whole-clip maximum is insufficient: the source peak is 0.717649 mm, but the candidate introduces penetration at other times. The per-time comparison correctly retains that regression.

Body evaluation flags excessive pose displacement, added joint speed and left-foot surface sliding. Exported whole-clip global joint peaks of 7.871628 m/s and 566.653365 m/s² remain below the original ceilings of 8.193098 and 578.207243. Those global maxima do not replace the failed point-specific phase limits or body/support checks.

Actual Godot playback passes **284 pose observations**, two requested-boundary events, four callback-mutation rejections, forward/reverse playback and unload. Maximum actor matrix component error is 7.12e-7. These events denote the requested pin boundaries, not verified physical contact. No motion-quality approval follows from successful playback.

## Evidence and next action

Local evidence is retained in `reports/contact-breadth-v1/cases/kick-11.json`, `engine/kick-11/verification.json`, `kick-11-horizontal-bound.json` and the immutable `reports/contact-jobs/contact-breadth-v1-kick-11-*` jobs. Suite, implementation, completion, engine and unchanged-candidate hashes were rechecked. No browser check, new test run, human rating or cleanup time is claimed.

Three of eight cases have completed; the original batch continues with jump/landing. Keep its methods and inputs frozen. Once all cases are accounted for, test bounded joint-pose correction under the same source-relative pin, floor and rate constraints, alongside the separate near-feasible root-repair improvements motivated by waving. Preserve this fixed-method result as the comparison. All release capabilities remain unapproved.


## Seed 22: pin passes, hold acceleration and foot sliding remain

The seventh frozen case, kick seed 22, passes all 81 left-foot pin samples, with maximum error 4.609579 mm. It has zero full-floor penetration/added depth and passes all 80 outside-window preservation observations (maximum skin error 6.11e-8 m). Hold acceleration is 4.010516523668894 m/s² against the original 4.010260922545707 ceiling: excess 0.000255601 m/s². The decoded source peak is 4.0102467664127595 m/s², also below the candidate. All other point-phase rate ceilings pass.

Global speed/acceleration peaks, 9.319279 m/s and 379.198352 m/s², remain below their original 9.320127 and 379.539784 ceilings. Body evaluation adds a left-foot surface-sliding flag to a source with no body flags. Passing one material-point pin does not establish that the whole foot is planted or that motion is natural. The fixed root repair rejects its linear subproblem and retains the seed unchanged; it does not prove the full pose problem infeasible.

The fit used 2,027 evaluations: stage iterations 120, 117, 120 and 120, with 302, 608, 680 and 433 evaluations plus four accepted-point recomputations. Only stage two stopped on relative objective reduction; the others hit their iteration cap. Full case time was 1,337.95 seconds before engine checking. Actual Godot playback and the independent record recheck pass 284 observations, requested events, callback protections, forward/reverse playback and unload (maximum actor matrix error 7.48e-7). Native BVH/GLB and eight-weight skin checks pass.

Evidence is retained in `reports/contact-breadth-v1/cases/kick-22.json`, `engine/kick-22/verification.json` and the immutable fit/repair jobs. Seven original cases are complete; one passes the full contact screen. The final jump/landing case is still running. No human or release approval is inferred.
