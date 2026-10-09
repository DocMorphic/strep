# Continue verified contact windows

The contact-window runner now accepts `--resume-window DIRECTORY`. It continues only the last accepted correction from a terminal, fully bound window history. Original motion references, frame times, exterior keys and all physical limits stay fixed. Individual-pose and window predecessors are mutually exclusive; output cannot overlap an immutable predecessor.

`window_restoration_resume.py` checks original inputs, archived implementations, native metadata, reports, diagnostics and every saved motion. It recursively verifies an acyclic chain of at most 32 window studies, including legacy individual-pose origins. Every observation gets complete nonlinear native geometry and saved-motion replay. Every backoff gets complete tangent, trust-bound, score and retention replay. Queries and linear initializers remain unretained. Changed rows, clocks, references, masks, proposal margins, policies or terminal controls are rejected. Recorded proposal archives are bound; this does not independently certify LP optimality or every later derivative.

## Verification and native continuation

A fresh isolated source fixture passes **399 focused tests across sixteen modules**. Added tests reject damaged provenance, incorrect ancestor starts, unaccepted-query promotion, changed saved precision, physical audits and trust bounds. The Windows/Linux CPU-native CI command includes the new resume module. The separate model-free inventory remains 406 Python modules and 39 Node suites; hosted CI success is not inferred from local checks.

The V2 continuation requested twelve outer iterations from fully verified V1, with ten inner iterations, trust `.03`, a 300-second local solve budget and row chunks of sixteen. Its owned available-RAM guard stopped the worker after 165.672 seconds: 622,813,184 available bytes fell below 600 MiB. Peak tree RSS was 1,401,999,360 bytes. It has no terminal result and is **ineligible for resume**. Partial replay verifies eight saved windows, 24 poses and one accepted correction; it does not provide terminal or historical metadata approval.

V3 retries from V1 with row chunks of four. All protocol fields except timestamp and chunk size match V2; its first eight observations match V2's controls, solver rows and physical audits. Background memory availability differs, so this is not an isolated RAM-performance experiment. All 18,056 skin vertices and eight influences per frame remain in the nonlinear population.

V3 finishes with five accepted corrections: three geometry-start 1/64 steps, one geometry-start 1/128 step and one optimized 1/16 step. It stops at `linear_start_unavailable`; it does not complete all twelve requested iterations. Local solve time is 286.063 seconds. The supervisor exits 0 after 448.906 seconds, with peak tree RSS 1,108,738,048 bytes. Original 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged.

Independent NumPy replay verifies **67 windows, 201 poses, five retained decisions and 36 proposal archive files**, including input/method/output hashes, native FK/skin, recorded epigraph/cap/vector/cut data and tangent/nonlinear decisions. Maximum solver-row replay error is `7.35e-14`. Solver float64 geometry and saved float32/projected geometry are measured separately: their maximum normalized row difference is `9.12e-6`. All five accepted saved representations preserve every conservative margin row.

| Frame | V1 → V3 grip distances, mm | V1 → V3 normal errors, degrees | V1 → V3 box penetration, mm |
| --- | --- | --- | --- |
| 97 | 4.575 / 4.807 → 4.590 / 4.807 | 20.189 / 16.659 → 20.182 / 16.645 | 13.885 → 13.537 |
| 98 | 4.984 / 4.973 → 4.986 / 4.975 | 19.835 / 19.571 → 19.831 / 19.542 | 7.201 → 7.173 |
| 99 | 4.559 / 5.111 → 4.529 / 5.074 | 19.648 / 15.069 → 19.634 / 15.065 | 16.282 → 15.804 |

Maximum normalized violation decreases `1.629311 → 1.581510`; squared violation decreases `56.265482 → 53.504345`. **All three poses still fail.** Normals exceed 10 degrees; raw-reference displacement is 221.580 / 221.868 / 221.555 mm against 220 mm; frame 99's right grip exceeds 4.99 mm; penetration remains failed. Passing grips, floor and speed limits remain protected. Raw adjacent added speeds are 0.161/0.571, 0.571/0.530 and 0.530/0.301 m/s against 1.5 m/s.

Initial dense/assembled values match exactly, with maximum Jacobian difference `5.329e-15`; measured times are 57.907/7.640 seconds at the resumed seed. These are local derivative measurements, not full-clip performance claims.

## Reproduction and remaining work

With separately acquired native inputs and an owned resource supervisor, use a fresh output directory:

```powershell
.venv/Scripts/python.exe scripts/guarded_window_restoration.py reports/box-lift-authored-height-v1 reports/new-resumed-window --frames 97 98 99 --iterations 12 --trust .03 --seconds 300 --solve-iterations 10 --row-chunk 4 --resume-window reports/box-lift-window-restoration-v1/window-97-99
```

V3's fully replayed terminal window supplies the origin for the subsequent [bounded search-margin fallback experiment](search-margin-fallback-v1.md); V2 stays partial evidence. Next handle finite-step curvature to obtain useful corrections across the contact interval. Then verify complete temporal and surface behavior, rig transfer and engine imports, and broaden arbitrary-action, object, partner, edit/style and held-out evaluation. Developer ratings and timed cleanup evidence remain absent. No source clip or preview was replaced, and no generation, training, engine import or human review was added by this study. All fourteen full-project capabilities remain unapproved; the project-wide goal stays active.
