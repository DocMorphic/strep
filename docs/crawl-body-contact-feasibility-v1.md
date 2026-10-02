# Floor restoration and guarded mesh-contact feasibility

The experimental mesh-contact CLI now accepts `--feasibility`. It first
restores sampled floor clearance under the original root/joint limits. Once
that succeeds, it pursues the authored contact targets with floor clearance
held as a hard constraint. This separates feasibility from the original soft
fitting score, which previously traded floor penetration for lower target error.
The default soft fitting path remains available.

Each frame constrains the lowest vertex of the **entire evaluated mesh**.
Contact constraints use the authored patch centroid and target radius. These
are exact sampled quantities; the lowest-vertex branch is nonsmooth when the
responsible vertex changes. SLSQP does not provide a global feasibility or
infeasibility certificate. Initial infeasibility is handled with a nonnegative
slack in the floor-restoration phase; contact slack never relaxes the restored
floor. Only tested motion-feasible improvements are returned, and the contact
phase also requires floor feasibility. Failed directions remain in the trace.

An internal one-percent margin tightens the 5 mm floor cap to 4.95 mm and the
20 mm contact radius to 19.8 mm, leaving export roundoff room. It does not widen
either screen. Original source-step-plus-0.5-degree rotation constraints remain
in force, as described in the [first coupled study](crawl-body-contact-coupled-v1.md).
If floor restoration fails, contact pursuit is skipped. Independent decoded
geometry, edit limits and solver completion still govern output selection;
failed candidates remain archived and the exact original stays selected.

The CLI now records exceptions after creating its own output directory. A
failed export preserves raw input, draft, methods and any completed outputs.
An existing directory, including one concurrently created by another worker,
is never relabeled or overwritten by this error handler. Input hashes are bound
before copying; fitting loads verified private copies and rechecks both source
files and snapshots before completion. Concurrent edits cannot rebind the request.

## Fixed crawl result

The first existing CesiumMan crawl case retains the exact original source,
four unreviewed hand/shin proxy patches, frame 54–56 targets, authored limits
and screens. It uses the same 13-by-45 cubic control shape and ten-frame
spacing. Declared budgets are 30 floor iterations and 60 contact iterations;
this is not an equal-compute comparison with the previous soft solve.

Floor restoration succeeds in two iterations. Contact pursuit exhausts all
60 iterations and returns a tested feasible endpoint segment. The combined
candidate passes floor and edit limits but misses three contact intervals.

| Output | Maximum target error at fitted frames | Deepest floor penetration at fitted frames | Floor-failed frames |
| --- | --- | --- | --- |
| Original | 140.697 mm | 7.821 mm | 41 |
| Soft coupled | 70.098 mm | 28.275 mm | 11 |
| Floor guarded | 130.100 mm | 4.491 mm | 0 |

The guarded candidate's left/right shin maximum errors are 14.175/34.518 mm;
left/right hand errors are 130.100/96.591 mm. The left shin passes, while the
other three intervals fail. Root edits reach 5.000 mm horizontally, 13.023 mm
vertically and 2.451 mm per step; joint edits and steps pass. All 120 frames
change, including 117 outside the target interval. The clip-wide edit/floor
objective still makes no immutable-context promise for this request.

Original soft energy decreases from 12.6880 to 10.8804 but is **not** the
feasibility selection metric. Final normalized motion-limit margin is 0.0986005.
Floor restoration is retained through contact pursuit; reaching the hand targets
is not demonstrated. The candidate is **rejected**, exact original selected,
and all quality/release approvals remain false.

## Independent timing and engine checks

Independent exact-key decoding samples all four source/sequential/soft/guarded
clips at 120 Hz, native keys, midpoints and declared float32 boundaries: 701
poses each, 2,804 total and 9,177,492 vertex observations. Guarded floor depth
remains 4.491 mm with zero failed samples. Original and soft coupled depth
reach 7.957/28.322 mm, showing that a fitted-frame check alone misses some
interpolation extrema. These finite samples are not a continuous collision proof.

Contact timing is reported two ways rather than silently choosing a hold
convention: the inclusive first-to-last active-key span, and the half-open full
frame span through the next key. Guarded left-hand maximum error is
130.100/137.970 mm respectively; both fail. Three contact intervals still fail
on both clocks. The draft's intended continuous hold needs explicit annotation.

Fresh actual headless Godot 4.7.2 imports all four clips and seeks 480 fitted
poses, 19 bones each. Maximum position error is 2.7996e-7 metres and maximum
basis element error is 6.9118e-7. Finite loop modes/durations match. The original
GLB skin driven by observed engine bones reproduces the guarded floor pass and
contact failure, across 1,571,040 vertex observations. Imported skin weights,
GPU rendering, forces, self/object collision and semantic quality remain open.

## Geometry review remains necessary

Posthoc inspection of all vertices with at least 65 percent relevant skin
weight finds the lowest Cesium left/right hand-region points at 57.821–70.680 /
41.350–51.563 mm above ground during these frames. Those surfaces are much
lower than the wrist-near centroids used by the existing proxy draft, but they
also do not touch the floor. On the Quaternius female/male clips, shin regions
penetrate as deeply as 31.519/71.057 mm. This strengthens the need to distinguish
anatomical target selection, timing, retargeting and generated action correctness.
A lowest weighted point is not independently labeled as a palm or kneecap.
These observations do not authorize replacing the frozen request or prove it
infeasible. No new model training is justified from this diagnostic alone.

Next investigate contact-feasible search directions and review/replace proxy
patches and contact timing. Broader scene/partner, action/edit/style, rig transfer,
transitions/loops, imports and human cleanup remain part of the same full goal.

## Reproduction and evidence

```powershell
.venv/Scripts/python.exe scripts/rig_mesh_trajectory.py --source character.glb --spec draft.json --output reports/my-feasibility-test --spacing 10 --iterations 60 --feasibility --floor-iterations 30
```

Use the exact licensed source and hash-bound 30 fps draft in a fresh output
folder. This experimental CLI uses the Windows worker lock and is not yet a
Studio submission option. Default model inference and authoring controls are
unchanged; the original input preserves its native clocks.

Fifteen initial tests cover independent full-mesh derivatives, staged floor
protection, frozen context/bounds, unreachable targets, skipped phases, actual
decoded exports, failure preservation and exact mode/budget validation. The
initial source checks pass 1,497 Python tests and 14 JavaScript suites.
Subsequent concurrent-output and input-mutation regressions pass in the 46-test
focused group; the final full source suite passes all 1,500 Python tests and
14 JavaScript suites. Fitting classes and the
feasibility stage match the measured archives; final snapshot/ownership guards
are separately bound and tested. Measured archived methods remain intact.

Local fit: `reports/crawl-body-contact-feasibility-v1`, result SHA-256
`53759bb2949e58fc2a9a9461fecb476b2e91ed998c1d35fb7d6f10f621e9da9a`.
Candidate:
`a92c8b36cb120bfe47f12794593b5da338625ce59e105a5b8b885f085840e3b2`.
Subframe results: `reports/crawl-contact-subframe-inspection-v2`; region checks:
`reports/crawl-contact-region-inspection-v1`. The first subframe writer failed
to serialize NumPy arrays; its helper/failure remain saved separately at v1,
and v2 fixes only observer JSON conversion. No fitting result was rerun or altered.
Actual import/reconstruction lives at
`reports/crawl-body-contact-feasibility-engine-v1` and its sibling engine study.
All 124 bound old/new fits, method archives, diagnostics/failure and engine files
rehash; receipt
`cee61da9824f2647ddd6e8f2464c31decb7e8e000bcbb244d0dc3ff0085d9625`.
No new inference/training, formal held-out prompts/seeds, browser/GPU rendering,
submitted developer/human review, timed cleanup or release approval occurred.
All 14 capabilities remain unapproved and the project-wide goal stays active.
