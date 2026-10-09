# Body proposal margins and bounded repair batches

The guarded native pose runner now accepts `--body-headroom`, default `0`, bounded to `[0, 0.001]`. It adds a search-only normalized margin to every `all-reference-position:` proposal row. It does not modify the physical 220 mm displacement limit, reference motions, speed rows, retention caps, tradeoff mask or final acceptance tests. Point margins remain separate. Existing callers retain their defaults.

## Diagnosis and validation

V14 resumes the fully bound V13 terminal pose with ten nonlinear inner iterations instead of fifty. It completes without an accepted step: 36 saved poses independently replay, including sixteen rejected backoffs. Candidates improve the aggregate score but regress protected right-hand/thumb reference-position rows. Even the smallest tested optimized fraction regresses a body row by `1.32e-8` in normalized slack. Exact retention correctly rejects it; this does not prove nonlinear infeasibility.

Recorded complete vector constraints admit checked first-order directions with body margins `1e-5`, `1e-4` and `1e-3`. These are proposal diagnostics, not finite nonlinear certificates. The native experiment uses `1e-3` and still requires complete actual nonlinear and tangent retention.

A fresh source-only fixture passes 230 focused tests across eleven modules; 122 pass without Torch. New checks cover position-only row selection, default-zero compatibility, invalid margins before worker acquisition, and curved nonlinear backoffs that remain rejected until actual protected rows are preserved. The same 405 Python modules and 39 Node suites remain in CI; this is focused local coverage.

## Completed and interrupted native comparisons

All runs use original V17 box-lift frame 98, immutable raw/limb/previous references and fixed adjacent keys. Trust remains `.03`; the local time budget remains 300 seconds. Both hand positions retain the 4.99 mm working limits, normals 10 degrees, displacement 220 mm, added speed 1.5 m/s, floor 2 mm and original rotation/root bounds.

- V14: supervisor exit 0 after 67.250 seconds, peak tree RSS 814,104,576 bytes. The local fit stops with no guarded improvement after 18.203 seconds, 35 measurements and 18 unretained inner queries. Its final pose equals V13.
- V15: thirty outer steps with the body margin record 231 physical observations, including 27 accepted nonlinear decisions. The owned supervisor stops the worker after 149.140 seconds when available RAM reaches 546,824,192 bytes, below the unchanged 600 MiB guard; peak tree RSS is 2,174,091,264 bytes. The interrupted output supplies no complete terminal result or tangent-decision certificate and is not eligible for resume. Partial physical replay verifies all 231 saved records and nonlinear accepted-row retention only; no old outputs are overwritten or promoted.
- V16: a ten-outer-step batch restarts from fully verified V13, without promoting V15's interrupted records. It completes with ten accepted steps after 33.547 local seconds, 74 measurements, 15 unretained queries and 58 backoffs. Supervisor exit 0 after 85.781 seconds, peak tree RSS 1,333,764,096 bytes. Independent replay verifies all 75 records, original/predecessor/method bindings, complete recorded vectors/cuts, nonlinear retention and tangent decisions.

| Physical check | Bound V13 seed | V16 terminal | Result |
| --- | --- | --- | --- |
| Left/right grip distance | 4.813 / 4.977 mm | 4.941 / 4.949 mm | Both pass |
| Left/right palm orientation | 19.721 / 19.358 degrees | 19.884 / 19.635 degrees | Both worsen and fail |
| Maximum box vertex penetration | 11.108 mm | 9.304 mm | Improves; fails |
| Maximum raw-reference displacement | 222.062 mm | 222.011 mm | Improves; fails 220 mm |
| Raw fixed-neighbor added speeds | 0.736 / 0.737 m/s | 0.512 / 0.476 m/s | Pass |
| Minimum skin floor height | 3.919 mm | 5.141 mm | Pass |
| Complete squared violation | 10.685808 | 8.106807 | Improves; not a quality rating |

Normal regressions are permitted by the declared failed-row merit policy. Neither a lower score nor ten accepted steps solves the grasp. Every full-pose, quality and release flag remains false. No source clip, preview, retargeted asset, engine import or human review is replaced or approved.

## Reproduction and next work

With separately acquired native inputs and an owned supervisor, run:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-body-margin/frame-98 --frame 98 --iterations 10 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 10 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v13/frame-98 --body-proposal preserve --proposal-start geometry-descent --body-headroom .001
```

The existing 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged. No unrelated process is stopped. All heavy inputs and outputs remain excluded from the public source snapshot.

V16's inline report is 118,289,938 bytes despite only ten starts. A transport-only probe packs one complete vector/cut payload from 3,037,898 JSON bytes into 445,311 NPZ bytes, verifying every value exactly with the existing observation archive. That probe is not yet integrated into the runner. Next stream complete proposal archives with immutable bindings to bound memory growth, then continue from V16 and address the orientation tradeoff before coordinated windows and full temporal/geometry/engine checks. The full arbitrary-action, scene/partner, editing/style, rig-transfer, transition/export and human-validation goal remains active; all fourteen release capabilities remain unapproved.
