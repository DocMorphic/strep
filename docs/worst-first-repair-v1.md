# Prioritize the largest pose failure

`--proposal-priority worst-first` is an opt-in objective for the geometry-descent initializer. The default remains `merit`; nonlinear refinement and actual retention rules are unchanged. Many small failures can dominate a squared-error objective, so this experiment gives the largest normalized failure priority while still requiring a negative complete squared-violation slope.

Each supporting-plane round first minimizes an epigraph bounding every scalar first-order violation. A second LP minimizes the complete squared-violation slope within `1e-6` of that epigraph. Original scalar caps, trust/global bounds and complete vector-norm populations remain enforced. Primary and secondary proposals are checked independently of solver success flags; the final direction must strictly reduce the predicted maximum by more than `1e-8`. Failed searches are not nonlinear infeasibility proofs. The existing 20-second/remaining-local-time, 64-round and 32-cuts-per-round limits remain.

LP controls, epigraphs, gradients, cuts and vector populations are archived without promotion to retained poses. Every finite backoff still needs complete original nonlinear and tangent acceptance. Resume rejects contradictory priorities; legacy records use their original merit semantics. No physical acceptance threshold is relaxed.

## Matched native experiment

V23 (worst-first) and V24 (merit) both resume the fully verified V22 frame-98 pose. Every protocol field except timestamp and priority matches: three outer steps, ten inner iterations, trust `.03`, 300 local seconds, original references/fixed neighbors, explicit point/body/normal preservation and streamed complete reports.

| Check | V22 seed | V24 merit | V23 worst-first |
| --- | --- | --- | --- |
| Left/right grip distance, mm | 4.983 / 4.971 | 4.983 / 4.971 | 4.980 / 4.972 |
| Left/right palm normal error, degrees | 19.859 / 19.596 | 19.858 / 19.566 | 19.709 / 19.465 |
| Maximum box penetration, mm | 7.222 | 7.198 | 7.270 |
| Maximum raw-reference displacement, mm | 221.886 | 221.874 | 221.874 |
| Maximum normalized violation | 0.978715 | 0.978552 | 0.963908 |
| Complete squared violation | 5.851296 | 5.742427 | 5.822123 |

Worst-first improves the dominant failure and both palm angles more, but box penetration worsens slightly under the existing failed-object tradeoff. Merit improves total squared error and penetration more. Neither is a usable grasp: normal errors still fail 10 degrees, displacement fails 220 mm and penetration remains failed. Both preserve passing grip distances, floor, root/rotation and fixed-neighbor speed budgets. This single pose does not establish better animation quality or generalization, and it does not justify changing the default.

V23/V24 retain three checked geometry-start steps each, with zero inner queries. Local solve times are 7.453/6.000 seconds; supervisors exit 0 after 79.719/77.704 seconds with peak tree RSS 881,250,304/860,164,096 bytes. The 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged.

Independent NumPy replay verifies all 42 native pose records, six retained decisions and 36 proposal archive files. Replay covers input/method/output bindings, complete skin populations and recorded scalar/vector/cut/epigraph/nonlinear/tangent decisions. Recorded derivatives and primary LP solutions receive primal replay, not an independent full-native derivative or optimality certificate. First-order predictions are not finite-pose certificates.

## Validation and reproduction

A fresh source-only fixture passes 308 focused checks across thirteen modules; 185 also pass without Torch. Tests cover competing small/large failures, false epigraphs, budget expiry without LP promotion, archive parity and contradictory resume policies. CI inventory remains 406 Python modules and 39 Node suites; local focused coverage is separate from hosted CI.

With separately acquired native inputs and an owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-worst-first/frame-98 --frame 98 --iterations 3 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 10 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v22/frame-98 --body-proposal preserve --body-headroom .001 --proposal-start geometry-descent --archive-proposals --normal-policy preserve --normal-headroom .001 --proposal-priority worst-first
```

Preserve both matched outputs. V23 can seed further investigation of dominant normal failures, while V24 records the better penetration/total-error outcome; neither is an approved global winner. Next address finite-step curvature and coordinated contact windows, then full temporal/geometry/engine validation. No source clip or preview is replaced and no model generation, training, import or human evidence is added. All fourteen capabilities in the broad arbitrary-action, scene/partner, editing/style, rig-transfer, transition/export and human-validation goal remain unapproved.
