# Coupled mesh-contact fitting: anticipation and retained failure

`scripts/rig_mesh_trajectory.py` adapts the existing coordinated temporal solver
to explicit mesh patches. It accepts arbitrary patch names and vertices rather
than inferring soles, palms or knees. The authored centroid targets, intervals,
contact/floor/prior weights, root/joint budgets and screens remain unchanged.
Adjacent edit differences are evaluated across the clip, counting each edge
once and retaining the original zero-edit prior before frame zero. Shared
cubic controls let a future target affect earlier poses.

The adapter adds no clearance-height or automatic contact objective. Its
inherited motion constraints also limit each actual joint rotation step to
the source step plus 0.5 degrees. This extra limit is stricter than the draft
alone. Per-frame component boxes remain conservative subsets of the authored
norm budgets; adjacent edit constraints use those authored norm budgets,
where the original sequential fitter used conservative component boxes.
The feasible search spaces and compute budgets therefore differ. This is a
development diagnosis, not an equal-budget solver ranking.

The CLI snapshots the exact original GLB, unchanged draft, implementation,
controls, optimizer trace and rejected candidate. It independently audits
decoded geometry before selecting an output. A candidate must pass the sampled
floor/contact/edit checks and solver completion; otherwise `selected_file`
remains `original.glb`. All outputs remain quality-unapproved. This experimental
CLI is not yet a Studio submission choice.

## First fixed case

The first case in the [published crawl probe](../benchmarks/crawl-body-contact-probes-v1.json)
is reused without changing its four proxy patches or frames 54–56. It remains
an unreviewed contact request on an existing CesiumMan development clip, not
an independently annotated palm/kneecap motion. All 120 frames are editable;
the global floor objective does not preserve motion outside the target interval.

The solve uses 13 cubic controls per each of 45 parameters, spacing ten frames,
and a fixed 60-iteration limit. Both numerical libraries run with one thread.
No model inference, training, new seed or reserved held-out prompt is used.

| Output | Maximum target error | Deepest floor penetration | Floor-failed frames |
| --- | --- | --- | --- |
| Original | 140.697 mm | 7.821 mm | 41 |
| Sequential candidate | 109.487 mm | 15.663 mm | 3 |
| Coupled candidate | 70.098 mm | 28.275 mm | 11 |

The coupled candidate changes all 120 frames, including 117 outside the three
target frames. At frame 53, its right forearm/hand controls already reach
14.437/10.524 degrees, where the sequential controls remain zero. Anticipation
is present, but all four decoded proxy intervals still fail the 20 mm screen.
Maximum errors are 22.318/34.277 mm for the left/right shin and 70.098/48.389 mm
for the left/right hand. The deepest floor penetration also fails the unchanged
5 mm screen.

Root edits remain within the original budgets: 28.711 mm horizontally,
67.040 mm vertically and 12.419 mm per step. Joint edits and steps pass their
original budgets. The returned point has a positive normalized hard-limit
margin of 0.027977. Objective decreases from 12.6880 to 4.07615, but SLSQP
exhausts all 60 iterations; a tested feasible segment from its endpoint is
retained. The candidate is **rejected**, and the exact original remains selected.
No convergence or target-feasibility proof follows.

This resolves the narrow question of whether coordinated controls can start
before the contact interval. It also exposes a separate problem: the current
soft fitting objective can trade worse floor depth for lower target error.
Increasing weights or declaring the lower score successful would not resolve
that failure. Next test explicit floor/contact feasibility constraints while
reviewing the anatomical proxies and contact schedule. Neither reviewed
anatomy nor plausible crawling semantics has been established here.

## Export and engine evidence

The candidate's CPU GLB roundtrip differs by at most 1.2592e-7 in its matrices
and 6.7660e-8 metres in its skinned vertices. Actual headless Godot 4.7.2 imports
the original, sequential and coupled GLBs and seeks all 120 frames of each:
360 poses, 19 bones per clip. Maximum bone position error is 2.7189e-7 metres
and maximum basis element error is 6.9118e-7. Duration and finite loop mode pass.

Driving the **original GLB skin** with those observed engine bones reproduces
the same three contact failures, with maximum geometry difference 4.3113e-7
metres across 1,178,280 vertex observations. This does not verify imported
skin weights, GPU rendering, between-key collision, force balance or naturalness.
The fitting failure survives import; it cannot be attributed to GLB export
or the measured Godot joint playback.

Full model-free checks pass 1,481 Python tests and all 14 JavaScript suites;
a subsequent active-floor gradient regression passes in the 28-test adapter/
spline group, covering 1,482 distinct source checks. Legacy trajectory, pose,
tensor spline and contact tests also pass. The model-free controls reproduce
the historical spline byte-for-byte for seven clocks; existing tensor helper
source remains unchanged, and coupled study archives include the new dependency.

## Reproduction and local evidence

With the exact licensed source clip and its hash-bound 30 fps contact draft:

```powershell
.venv/Scripts/python.exe scripts/rig_mesh_trajectory.py --source character.glb --spec draft.json --output reports/my-coupled-test --spacing 10 --iterations 60
```

Use a fresh output folder; existing results are never overwritten. The CLI
uses the project's Windows worker lock. Original/native source clocks remain
in `original.glb`; fitting/export is a 30 fps sampled approximation over the
draft's declared frames.

Local fit: `reports/crawl-body-contact-coupled-v1`, result SHA-256
`8727dd4b2408972f997e6887439185374d5377336d169144ef2b8ecb3a4e1d22`.
Candidate SHA-256:
`d320e71ada88c9702ce8c30413fba0ac77eb2a6628238a384a91c0de96f6ce13`.
Actual import: `reports/crawl-body-contact-coupled-engine-v1`; reconstruction:
`reports/crawl-body-contact-coupled-engine-study-v1`. All 70 bound fitting,
prior pilot, methods and engine evidence files rehash; receipt
`a58e7416f6674f0d103cc9670c3e12392973ea4dc02d0079359857e4b29f860b`.
No new browser render, human review, timed cleanup or release approval occurs.
All 14 release capabilities remain unapproved; the full-project goal stays active.
