# Preserve failed palm orientations during pose repair

In merit-mode pose experiments, `--normal-policy preserve` removes every normal row from the failed-row tradeoff mask. Failed orientation rows cannot worsen; passing orientations remain within their original limits. Object rows may still trade under the existing requirement that maximum violation does not increase and complete squared violation decreases. Default normal tradeoff behavior and rowwise behavior remain compatible with prior experiments.

`--normal-headroom` adds a search-only normalized margin to normal proposal rows, bounded to `[0, .001]` and requiring explicit normal preservation when positive. Point/body margins remain separate. No physical point, normal, displacement, speed, floor, root or rotation threshold changes. Resume validates the declared normal policy against the actual mask, while legacy protocols retain their original tradeoff semantics. Stage logs distinguish reading reports, binding archives and independently verifying each ancestor.

## Validation

A fresh source-only fixture passes 295 focused tests across thirteen modules; 177 pass without Torch. New tests reject a lower collision score that hides a failed-normal regression, exercise a nonlinear improvement through another control, verify separate margin populations, reject invalid options before worker acquisition and reject contradictory resume policies. CI inventory remains 406 Python modules and 39 Node suites. This is focused local coverage, not hosted-CI or release approval.

V20 resumes the complete streamed V17 frame-98 study and verifies its legacy ancestors under unchanged original references and physical budgets. Ten outer and ten inner iterations use trust `.03`, a 300-second local budget, point margin `1e-5`, body/normal margins `.001` and streamed reports. Ten accepted steps are saved, but the owned supervisor interrupts publication at 151.656 seconds when available RAM reaches 599,109,632 bytes, below 600 MiB. Peak tree RSS is 818,544,640 bytes. No terminal result is available and no interrupted pose is promoted for resume.

Partial NumPy replay verifies all 99 saved physical records, all 61 recorded nonlinear/tangent backoff decisions, ten accepted steps and 60 current proposal archive files. It establishes bindings at partial-replay time; these do not replace the unavailable terminal result references or prove historical metadata binding. The final saved observation improves normal errors to 19.847/19.394 degrees, penetration to 7.066 mm and raw displacement to 221.809 mm, but remains failed and ineligible for resume.

V21 is a completed three-outer/three-inner-iteration comparison from V17. It verifies actual native resume and all 22 records, but accepts no step. The worker-construction edit also shortened its inner budget; that configuration remains preserved. Supervisor exit 0 after 63.375 seconds, peak tree RSS 828,833,792 bytes. It supplies no infeasibility proof.

V22 explicitly restores ten inner iterations while retaining three outer iterations and restarts from verified V17, never V20. It completes with three accepted steps after 21.657 local seconds: 36 measurements, 17 unretained inner queries and 18 backoffs. Supervisor exit 0 after 77.625 seconds, peak tree RSS 817,324,032 bytes. Independent replay verifies all 37 pose records, full archived vector/cut populations, original/predecessor/method bindings and every nonlinear/tangent decision. Its 36 nonfinal observations match V20's corresponding records exactly.

| Check | V17 bound seed | V22 retained terminal | Result |
| --- | --- | --- | --- |
| Left/right grip distance | 4.968 / 4.954 mm | 4.983 / 4.971 mm | Both pass 4.99 mm |
| Left/right normal error | 19.876 / 19.712 degrees | 19.859 / 19.596 degrees | Both improve; still fail 10 degrees |
| Maximum box penetration | 7.613 mm | 7.222 mm | Improves; failed |
| Maximum raw-reference displacement | 221.929 mm | 221.886 mm | Improves; fails 220 mm |
| Raw fixed-neighbor added speeds | 0.532 / 0.512 m/s | 0.565 / 0.544 m/s | Pass 1.5 m/s |
| Minimum skin floor height | 6.857 mm | 4.878 mm | Pass 2 mm |
| Complete squared violation | 6.549961 | 5.851296 | Decreases; not a quality rating |

Actual native continuation from a streamed terminal source is now verified. The pose, quality and release flags remain false. These small improvements do not solve a grasp, establish realistic anatomy/dynamics or qualify a clip.

## Reproduction and next work

Use separately acquired native inputs and an owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-normal-preservation/frame-98 --frame 98 --iterations 3 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 10 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v17/frame-98 --body-proposal preserve --body-headroom .001 --proposal-start geometry-descent --archive-proposals --normal-policy preserve --normal-headroom .001
```

The 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged; no unrelated process is stopped. Preserve V20's interrupted output and use V22 as the next fully bound pose. Next measure whether proposal priorities can reduce the dominant normal failures more effectively, then extend useful correction to coordinated windows and full temporal/geometry/engine checks. No source clip or preview is replaced and no generation, training, retargeted import or human evidence is added. All fourteen broad arbitrary-action, scene/partner, editing/style, rig-transfer, transition/export and human-validation release capabilities remain unapproved.
