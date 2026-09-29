# Full-skin object sampling experiment

The regional fitter can now check every skin vertex against scene objects with `--full-object-skin`. This is an experimental option; the default remains the frozen subset. The original floor sample, contact targets, edit budgets and acceptance limits stay unchanged.

## Why test this

Reconstructing the retained longer box fit found that its frozen sample included 915 of 18,056 vertices. At its worst native frame, the full mesh penetrated the box by 6.284 mm while the selected subset reported 2.719 mm. The worst vertex belonged entirely to the right forearm and was omitted; 227 omitted vertices penetrated at that frame. This establishes incomplete optimizer coverage, not that coverage is the only cause of failure. The diagnostic samples native keys only.

## Matched development comparison

Both methods used the same five-frame box fixture, balanced regional penalties, three stages with 40 iterations per stage, and a 600-second cap. Independent exported audits sampled integer and quarter frames. These are equal iteration caps, not equal runtime.

| Measure | Frozen subset | Full skin |
| --- | ---: | ---: |
| Object vertices | 915 | 18,056 |
| Floor vertices | 915 | 915 |
| Fit time | 7.641 s | 18.500 s |
| Minimum object clearance | -17.934 mm | -16.456 mm |
| Contact failures | 34 / 34 | 34 / 34 |
| Geometry failures | 17 / 17 | 17 / 17 |
| Maximum anchor error | 5.019 mm | 4.981 mm |
| Maximum normal error | 15.123 degrees | 14.309 degrees |
| Peak joint acceleration | 6.357303 m/s² | 6.352443 m/s² |

Both candidates pass source-relative hard edit bounds. Both still fail the interaction requirements. Source peak acceleration was 6.180514 m/s², so neither candidate establishes temporal preservation. Full-skin sampling reduces the observed penetration in this fixture but does not solve box grasping or approve animation quality.

The default method reproduces every native output array and the candidate GLB from the earlier short balanced box run exactly. Thirty-three focused tests pass, including omitted-vertex detection, unchanged floor sampling, regional objectives, audit checks, finger budgets, support contacts and Studio job validation. Actual Godot imports match four GLBs across 20 actor-frames and 77 bones, with maximum position error below 0.226 micrometres. Engine fidelity does not approve the motion.

## Reproduction and limits

In a provisioned workspace with the retained fixture:

```powershell
.venv\Scripts\python.exe scripts/diagnose_region_box_sampling.py reports/region-fit-box-balanced-long-v1 reports/new-box-diagnostic.json
.venv\Scripts\python.exe scripts/study_region_box_sampling.py reports/new-box-sampling
```

For another authored scene, use the commands in [region fitting](scene-region-fitting-v14.md), adding `--full-object-skin` to the fitting command. The comparison runner depends on a locally generated development fixture; it is not a self-contained public benchmark download. Output directories must be fresh. Raw evidence remains locally under `reports/region-box-sampling-v1` and `reports/region-box-sampling-diagnostic-v1.json`.

The optimizer checks full vertex coverage at native keys only. This does not guarantee collision-free triangle interiors, continuous time, self-collision, anatomical feasibility, forces, or human realism. No model was trained or changed, no held-out trial was consumed, and all 14 release capabilities remain unapproved. Further solver work must address the remaining constraints; repeating iterations on this fixture cannot establish broad action coverage.

Follow-up: [separate per-vertex object constraints](object-vertex-constraints-v1.md) improve sampled clearance further while retaining contact and temporal failures.
