# Preserve collision rows during grasp repair

`--object-policy preserve` removes every object row from merit-mode tradeoffs. Failed clearance rows cannot worsen and passing rows must remain feasible at every retained pose. The default remains `tradeoff` for compatibility with archived studies. Rowwise retention already protects these rows.

`--object-headroom` adds a separate search-only normalized collision margin, bounded to `[0, .001]`; positive values require object preservation. These rows use a 10 mm normalization, so `.001` tightens proposals by 10 micrometres. Point, normal, body, floor, speed and rotation margins remain separate. Original nonlinear acceptance thresholds are unchanged. Resume checks the archived object policy against the actual mask; legacy protocols retain their historical tradeoffs.

## Why this was tested

Complete V23 backoff replay identifies a nearly tangent left-forearm clearance row as the dominant passing-row rejection. Its initial normalized slack is `0.0000515177`; a full proposed step produces `-0.0116709`. The first iteration accepts only a 1/16 step and later iterations only 1/128. These are measured nonlinear failures, not an infeasibility proof. Recorded first-order/vector probes can preserve every object row and improve the largest failure, but those proposals need finite native verification.

V25 repeats V23 from the same fully bound V22 frame-98 pose with object preservation and `.001` collision margin. Source, original references, neighbors, physical limits, trust `.03`, three outer steps, ten inner iterations, 300-second local budget, other margins, normal preservation, geometry priority and archive transport remain identical. Implementations and the new object-policy/proposal fields necessarily differ.

| Check | V22 seed | V23 object tradeoff | V25 object preservation |
| --- | --- | --- | --- |
| Left/right normal error, degrees | 19.859 / 19.596 | 19.709 / 19.465 | 19.836 / 19.585 |
| Left/right grip distance, mm | 4.983 / 4.971 | 4.980 / 4.972 | 4.983 / 4.972 |
| Physical box penetration, mm | 7.222 | 7.270 | 7.215 |
| Raw-reference displacement, mm | 221.886 | 221.874 | 221.880 |
| Maximum normalized violation | 0.978715 | 0.963908 | 0.976420 |
| Complete squared violation | 5.851296 | 5.822123 | 5.825482 |

V25 improves both normals, collision depth and displacement while protecting every original row; three 1/64 steps are retained. However, normal errors still fail 10 degrees, displacement fails 220 mm and penetration remains failed. Grip distances, floor and neighbor speeds remain passing. Larger steps now regress failed thumb, ring and pinky clearance rows as well as the right point at larger fractions. The margin does not solve finite-step curvature or establish a usable grasp.

The supervisor completes with exit 0 after 87.922 seconds, peak tree RSS 888,270,848 bytes. The local solve takes 8.563 seconds with 22 measurements, 21 backoffs, three initializers and zero inner queries. All original global guards remain unchanged. Independent NumPy replay verifies 23 complete native pose records, three accepted decisions, 18 proposal archive files and all input/method/output bindings. It replays complete recorded epigraph/vector/cut/scalar/nonlinear/tangent data and physical skin/contact/body populations. It is not an independent full-native derivative or LP optimality certificate.

## Validation and reproduction

A fresh source-only fixture passes 320 focused tests across thirteen modules; 189 also pass without Torch. Coverage includes an improving normal score hiding a collision regression, a joint correction using another clearance control, separate margin routing, invalid requests before worker acquisition and contradictory archived policies. CI inventory remains 406 Python modules and 39 Node suites; hosted verification is separate.

With separately acquired native assets and an owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-collision-preserving/frame-98 --frame 98 --iterations 3 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 10 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v22/frame-98 --body-proposal preserve --body-headroom .001 --proposal-start geometry-descent --archive-proposals --normal-policy preserve --normal-headroom .001 --proposal-priority worst-first --object-policy preserve --object-headroom .001
```

Use V25 for further all-row-preserving diagnostics while preserving both earlier tradeoff comparisons. Next investigate finite-step curvature and coordinated contact-window controls; small one-pose gains do not replace full temporal, geometry, engine, held-out action/rig/partner or human review. No source clip or preview is replaced, and no generation, training, import or human approval is added. All fourteen full-project release capabilities remain unapproved.
