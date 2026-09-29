# Separate object-clearance constraints for each skin vertex

The scene fitter now offers `--object-constraint-mode per_vertex`. Each sampled skin vertex has its own augmented-Lagrangian multiplier instead of sharing one maximum-violation constraint per object and frame. The default remains `maximum`; this experiment does not enable a new Studio default or approve box interaction quality.

## Evidence and method

The preceding [full-skin sampling comparison](object-skin-sampling-v1.md) found that including all vertices alone did not repair the box interaction. At that candidate, 541–590 vertices violated the box clearance in each native frame, but the squared maximum penalty supplied a skin-position gradient through only one vertex per frame. The new mode supplies gradients through all currently violating vertices when multipliers start at zero.

The feasible set is unchanged: every selected vertex must satisfy the same primitive clearance. Per-vertex merits are summed over vertices and averaged over frames and objects. One violating vertex keeps its original weight; multiple violations now contribute multiple penalties. This changes both gradient coverage and total penalty weight, so this is not evidence isolating gradient sparsity from weighting. At the diagnostic pose, the zero-multiplier box merit rises from 3.060 to 162.258. The diagnostic does not reconstruct final optimizer multipliers or prove convergence.

Both comparison modes use full coverage of 18,056 skin vertices, the original 915 floor samples, the same authored source, frozen hand witnesses, balanced regional loss, rotation/root budgets and acceptance limits. The initial object penalty is 20,000 and grows by four per stage. No training or checkpoint change occurred.

## Independent exported results

This is the same five-frame development repair fixture, sampled independently at integer and quarter frames. The contact requirement includes a 2 mm minimum clearance, a 5 mm anchor tolerance, a 10-degree normal tolerance, and distributed patch conditions.

| Variant | Fit time | Minimum object clearance | Contact failures | Max anchor error | Max normal error | Peak joint acceleration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Maximum, 3 × 40 | 18.500 s | -16.456 mm | 34 / 34 | 4.981 mm | 14.309° | 6.352443 m/s² |
| Per vertex, 3 × 40 | 19.922 s | -9.507 mm | 34 / 34 | 5.543 mm | 13.394° | 6.193069 m/s² |
| Maximum, 6 × 100 | 74.313 s | -6.424 mm | 29 / 34 | 5.957 mm | 11.451° | 6.401104 m/s² |
| Per vertex, 6 × 100 | 83.547 s | +1.601 mm | 34 / 34 | 4.531 mm | 10.958° | 6.473133 m/s² |

All four candidates pass source-relative hard edit budgets and fail all 17 geometry samples because minimum clearance remains below 2 mm. The longer per-vertex fit removes sampled penetration but does not meet clearance or all contact requirements. It also has worse peak acceleration than the maximum comparison and the source's 6.180514 m/s². Peak joint speed remains 0.363166 m/s in these four variants. Fewer contact failures in the longer maximum variant do not outweigh its penetrating body geometry; neither method is accepted.

The longer per-vertex native maximum clearance violation decreases across stages from 17.360 to 7.134, 1.725, 1.205, 0.651 and 0.399 mm. This demonstrates progress within the search, not convergence or continuous-time feasibility. More iterations on this one fixture are not broad validation.

The initial longer maximum attempt failed its 600-second budget: progress jumped from 72.67 seconds at evaluation 580 to 3,711.64 seconds at evaluation 600. The cause of this elapsed-time jump is unverified. That failed output remains untouched; only that arm was retried, with unchanged settings and a fresh directory. Timing values above are from completed attempts, not the failed run.

## Validation and reproduction

Forty-four focused tests pass. They check gradient coverage, finite-difference derivatives, preservation of single-vertex weight, feasible-set equivalence, multiplier layout rejection, unchanged floor sampling, regional objectives, hard finger budgets and existing fitting/job behavior. The maximum-mode residual and merit expressions remain numerically equivalent to the legacy expressions.

Actual Godot imports verify all 77 bones for 30 new actor-frames; another ten baseline actor-frames reuse the preceding verified full-skin run. The largest new position discrepancy is below 0.266 micrometres. Hash checks bind fitting results, independent audits, source inputs and engine GLBs. These checks establish export fidelity, not contact success or visual realism. No live browser or human review was performed.

For an authored scene in a provisioned workspace, using a fresh output directory:

```powershell
.venv\Scripts\python.exe scripts/study_region_object_constraints.py path/to/scene.json --actor A --contact left-grip --contact right-grip --output reports/new-object-constraint-comparison --stages 6 --iterations 100 --seconds 600
.venv\Scripts\python.exe scripts/diagnose_object_constraint_gradients.py reports/completed-fit reports/new-gradient-diagnostic.json
```

The comparison runner retains each method's failed execution, audits completed candidates and imports their GLBs. It returns failure if either method failed; failed execution and failed motion-quality measurements are separate outcomes. The ordinary fitting CLI also accepts `--full-object-skin --object-constraint-mode per_vertex` for explicit experiments.

Local evidence: `reports/region-box-gradient-comparison-v1.json`, `reports/region-box-vertex-constraints-v1`, `reports/region-box-object-constraints-long-v1`, `reports/region-box-maximum-long-retry-v1`, their audits, and `reports/region-object-constraints-final-v1/comparison.json`. Generated fixtures and assets require a provisioned workspace and are excluded from the public source repository.

## Remaining work

Retain this option as experimental. The remaining regional violations, clearance margin and temporal regression need a coordinated correction, followed by longer clips and varied objects/actions/rigs. Full vertex coverage still does not test triangle interiors, continuous time, self-collision, anatomical limits or forces. This single development fixture cannot establish general manipulation or partner interaction. All 14 project release capabilities remain unapproved.

Follow-up: [regional constraints and bounded restarts](regional-constraints-warm-start-v1.md) compare fixed versus staged regional penalties from original and recovered candidate controls; every interaction remains rejected.
