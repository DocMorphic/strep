# Resumable native pose repair

`guarded_pose_restoration.py --resume <terminal-pose-study>` starts a new diagnostic repair from the previous study's last retained parameters. It preserves the original raw, limb and previous reference motions, authored scene targets, fixed adjacent candidate keys, finger/body/root budgets and numerical working limits. It does not rebase a displacement budget around the corrected pose.

The loader verifies source/frame/row/budget identity, native metadata, original input hashes, every archived method, protocol/result/pose/diagnostic bindings and all saved observation bindings. It replays saved backoff retention decisions, including recorded tangent linearizations when enabled, rejects promotion of an inner query, recomputes complete initial/final inequalities and reconstructs the final pose and independent physical audit. Decision replay uses recorded derivatives; it is not an independent derivative certificate. Sparse/dense preflight is separate.

Chains replay their ancestors, retain the original source and reject cycles. A chain is limited to 32 studies. New output must be separate from the resumed study. Source and predecessor outputs remain immutable. Failed poses can be resumed only as explicitly unapproved diagnostics; resuming does not qualify them for release or scene-generation guides.

`--body-proposal feasible` adds every original native-joint displacement and fixed-neighbor added-speed row to the proposal's feasible-row mask. `--point-proposal feasible` can be used at the same time. Point proposal headroom applies only to point rows. These options strengthen the proposal search; every retained endpoint still uses the original complete nonlinear checks and declared tradeoff policy. A backoff can improve a failed body row without making it feasible. The default remains `preserve` with no resume.

The experiment retains the one-pose scope from [tangent-protected repair](tangent-protected-repair-v1.md): no full-clip, support-slide, between-key, triangle/volume, self-collision, anatomy, dynamics, engine-import or human approval. Native inputs are licensed local acquisitions, excluded from Git; a public source checkout alone cannot reproduce the native experiment.

## Validation

A fresh source-only copy, without vendor assets, passed 183 focused checks across 11 modules. An added chain test and rerun of the 34 runner tests bring the distinct focused count to 184. Tests distinguish retained output from the last inner query, reject modified originals/methods/poses/budgets/frame/final slacks/tangent decisions, preserve existing output on failure, and verify chained provenance and cycle rejection. This is focused local coverage; hosted CI remains separate.

## Native study

V9 resumes V8's retained frame 98 of the unchanged V17 source. It uses merit tradeoffs only for already-failed normal/object rows, preserved hand points, feasible point/body proposals, point headroom `1e-5`, tangent protection, trust `.03`, 50 inner iterations and a 300-second local budget.

The supervisor completed with exit 0 after 315.922 seconds, peak process-tree RSS 677,351,424 bytes. The pose worker reached its local budget after 300.516 seconds: 316 measurements, 315 unretained inner queries, no completed backoff or accepted new step. Final parameters and all physical metrics equal the resumed seed. Successful process completion does not mean a valid pose.

| Check | Resumed seed and retained final | Result |
| --- | --- | --- |
| Left/right surface grip point | 4.455 / 4.916 mm, limit 4.99 mm | Pass |
| Left/right surface orientation | 19.684 / 17.209 degrees, limit 10 degrees | Fail |
| Maximum physical box vertex depth | 13.566 mm | Fail |
| Maximum raw-reference joint displacement | 222.107 mm, limit 220 mm | Fail |
| Raw-reference fixed-neighbor added speeds | 0.228 / 0.454 m/s, limit 1.5 m/s | Pass |
| Floor and original rotation/root budgets | Preserved | Pass |

Complete NumPy replay verified 317 saved poses, original/predecessor/archive bindings, surface point/normal/depth/floor measurements and all three reference populations. It confirmed that every inner query remained unretained and the final output equals the saved predecessor. No original source frame or preview was replaced; the 180-frame source remains failed.

A separate HiGHS diagnostic of the recorded initial Jacobian found a feasible linear proposal at the original `.03` trust radius with body restoration, point headroom and tangent protection. It also found linear feasibility for diagnostic radii `.1` and `.3`; no native rerun used those larger radii. Returned deltas/bounds and linear slacks were checked; minimum residuals were within floating-point rounding (less than `4e-15`). These checks use recorded derivatives and prove neither nonlinear feasibility nor an animation path. The timeout is not an infeasibility result.

Reproduction with the unchanged local native inputs:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-resumed-pose/frame-98 --frame 98 --iterations 30 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 50 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v8/frame-98 --body-proposal feasible
```

The local study supervisor retained the existing 3,600-second / 7 GiB process-tree / 600 MiB available-RAM guards. The command above is the pose-worker command; use an owned supervisor for a native run. Generated outputs stay in ignored `reports/`.

Next: derive a feasibility-first proposal or warm proposal from the recorded linear system, test it against complete nonlinear rows before retention, and preserve both hand points. Then extend to coordinated frame windows and full temporal/geometry replay. No training, model generation, engine import, human review or release gate was approved by this experiment. All fourteen full-project capabilities remain unapproved.
