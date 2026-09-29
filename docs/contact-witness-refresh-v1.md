# Refreshing contact witnesses inside an unchanged hand patch

The fitter now offers `--witness-mode stage_refresh`. It may replace the three vertices used to guide distributed contact, while preserving the authored patch, target, anchor, normal and acceptance limits. The default remains `frozen` pending broader validation.

Selection runs at the actual initial pose, including a bounded restart, and at accepted solver-stage boundaries. It never changes witnesses during an L-BFGS line search. A proposed triple is accepted only when its squared violation score strictly improves. For balanced reduction, the comparison covers the changed gap, radius, spacing, area and centroid families. The worst reduction compares the complete maximum squared violation. Every accepted change records old/new vertex IDs and scores; final witnesses are also recorded.

When regional inequality multipliers are enabled, changing vertices resets only the gap/radius/spacing/area/centroid multiplier rows. Whole-patch clearance, normal and anchor identities retain their multipliers. The search is heuristic and does not prove global feasibility. Independent exported evaluation still searches the whole authored patch.

Two optional solver margins address finite optimization and export precision without relaxing acceptance. `--object-clearance-margin-m` increases the solver's object-clearance target. `--contact-gap-margin-m` decreases its selected contact vertices' maximum gap. The latter copies the limits rather than mutating the authored package, and rejects a positive margin that exhausts the available clearance window. Both default to zero.

## Development comparison

The box variants use the same five-frame fixture and initialization from the earlier per-vertex candidate, balanced fixed regional penalties, full skin coverage and six stages of 100 iterations. The original clip remains the edit-budget reference. The frozen restart is the retained control from [bounded restart experiments](regional-constraints-warm-start-v1.md).

Reselection without margins passes all 34 independently decoded hand-contact samples but misses four of 17 whole-body geometry samples. The smallest box gap is 1.994196 mm against the original 2 mm requirement. Twenty-six accepted correspondence changes occur across initialization and five stage boundaries: 10, 3, 4, 4, 3 and 2.

A 0.05 mm object target margin makes the exported contact and geometry samples pass. However, the native final frame's left-hand witness has a 3.000019443 mm gap against a 3 mm upper limit. Export rounding puts that witness inside the limit. That native/export discrepancy is preserved as a failed native result, rather than silently accepting the export alone. A separate candidate adds a 0.01 mm upper-gap margin to test a result with room inside both limits.

The existing sphere repair is also rerun with stage refresh under its original three-stage, 40-iteration settings. It accepts no witness changes, reproduces every native output array and the candidate GLB exactly, and retains all 34 contact and 17 geometry passes. This is a regression check on an existing development fixture, not an additional action or held-out trial.

The final box candidate, with both solver margins, passes both native hand tracks, all 34 decoded contact samples and all 17 geometry samples. The original authored limits, source inputs, seed and iteration budgets are identical across the box comparison; only the recorded optimization options differ.

| Box variant | Native hand tracks passing | Exported contact failures | Geometry failures | Minimum box clearance | Peak joint acceleration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen control | 0 / 2 | 34 / 34 | 17 / 17 | 1.721591 mm | 6.443118 m/s² |
| Refreshed, no margins | 2 / 2 | 0 / 34 | 4 / 17 | 1.994196 mm | 6.422764 m/s² |
| Refreshed, clearance margin only | 1 / 2 | 0 / 34 | 0 / 17 | 2.053416 mm | 6.423187 m/s² |
| Refreshed, both margins | 2 / 2 | 0 / 34 | 0 / 17 | 2.050287 mm | 6.389502 m/s² |

The final maximum anchor error is 4.994811 mm and maximum hand-normal error is 9.998710 degrees. It passes original source-relative hard edit budgets and takes 97.672 seconds, compared with 84.250 seconds for the frozen restart. All compared candidates retain the source's peak joint speed of 0.363166 m/s. Final acceleration still exceeds the source's 6.180514 m/s², so geometry success does not establish temporal preservation or animation quality.

Sixty-four focused tests pass. They cover fixed witnesses during line searches, latest accepted-pose selection, strict score improvement, selective multiplier resets, frozen behavior, unchanged authored tolerances and margin rejection, plus existing initialization/contact/job checks. A zero margin retains previously valid zero-width contact windows; a positive margin cannot exhaust them. Actual Godot imports verify 40 new actor-frames, eight GLBs and 77 bones, with maximum position discrepancy below 0.281 micrometres. Ten frozen-control actor-frames reuse prior engine evidence. Browser and human review remain unperformed.

Preserved evidence includes `reports/region-box-refreshed-witness-v1`, `reports/region-box-refreshed-margin-v1`, `reports/region-box-refreshed-interior-v1`, `reports/region-sphere-refreshed-witness-v1`, their independent audits, and `reports/region-witness-comparison-v1/comparison.json`. The intermediate native/export mismatch remains in `reports/region-box-refreshed-margin-boundary-v1.json`. No prior result was overwritten.

## Reproduction and scope

In a provisioned workspace with an authored scene and compatible prior candidate, use a fresh output directory:

```powershell
.venv\Scripts\python.exe scripts/fit_scene_regions.py path/to/original-scene.json --actor A --contact left-grip --contact right-grip --output reports/new-witness-fit --region-loss balanced --stages 6 --iterations 100 --seconds 600 --full-object-skin --object-constraint-mode per_vertex --initialization path/to/prior-candidate.npz --witness-mode stage_refresh --object-clearance-margin-m 0.00005 --contact-gap-margin-m 0.00001
.venv\Scripts\python.exe scripts/audit_scene_region_fit.py reports/new-witness-fit reports/new-witness-fit-audit
```

The box initialization itself took 83.547 seconds; restart times exclude that prior cost. The margin values are experimental solver targets, not calibrated universal defaults. Full vertex coverage at discrete times does not establish continuous collision avoidance, triangle-interior clearance, anatomy, self-collision or forces. Temporal regression, full-action transitions, broader objects/rigs/partners and human review remain separate requirements. No model was trained or changed, and all 14 release capabilities remain unapproved.
