# Experimental region-aware clip fitting

The region-authoring package now has a fitting path, `fit_scene_regions.py`. It consumes authored scene contacts directly instead of reproducing a hard-coded sphere-study sequence. It returns candidates and retains failed measurements; it is not a release-approved interaction solver.

## Method

The fitter reuses the native clip solver's cubic correction controls, source-relative rotation bounds, vertical root-lift bound, finger budgets, inferred support terms and sampled object-clearance inequalities. Both the base and previous motion are the supplied clip. This differs from the older sphere experiment's original V13-relative budgets; these experiments do not establish preservation of that older cumulative reference.

The new objective uses the authored patch's area-weighted normal and a frozen triangle of three separated skin vertices. It penalizes patch clearance, selected-point upper contact gaps, target radius, spacing, triangle area, centroid distance, normal error and the explicit anchor tolerance. Scene targets and object tracks remain fixed. The vertex-distance calculation uses analytic sphere or Euclidean box signed distance; the independent evaluator recomputes distances separately.

If a valid distributed witness already exists in the supplied frame, it is used. Otherwise the initializer scores all triples in a pool of up to 24 nearby vertices. This heuristic can miss useful correspondences and freezes its choice during the fit. Failure is not proof that the request is infeasible. The independent exported audit searches the full declared patch.

Two penalty reductions are recorded explicitly. `worst` uses the largest squared normalized violation per contact-frame. `balanced` gives each constraint family a contribution, normalizing the multi-vertex families by their sample count. This changes the optimization objective, not the authored acceptance limits. Legacy point-only compilers still reject region contacts; the new fitter explicitly installs the regional objective and removes the different anchor-adjacent normal objective.

The output includes raw input, authored scene, compiled constraints, implementation snapshots, fitting recipe, progress, native motion, source/candidate GLBs and source/candidate scene measurements. Inputs are hashed before and after fitting. A declared time budget can interrupt the run, and failed runs remain recorded.

## Reproduction

Use a provisioned workspace, explicit region contacts and fresh output directories:

```powershell
.venv\Scripts\python.exe scripts/fit_scene_regions.py path/to/scene.json --actor A --contact left-grip --contact right-grip --output reports/new-region-fit --region-loss balanced --stages 3 --iterations 40 --seconds 180
.venv\Scripts\python.exe scripts/audit_scene_region_fit.py reports/new-region-fit reports/new-region-fit-audit
```

The independent audit decodes GLB animation at integer and quarter frames, recomputes full skin/object and floor clearance, and checks anchor and distributed contact requirements. It also checks native source-relative body/finger edit budgets, noneditable joint rotation preservation, root X/Z preservation and unchanged predicted foot-contact labels. Native forward kinematics is independently reconstructed with the source bone offsets, and every exported key is compared with the native record. Bone-length changes cannot bypass the rotation-budget check. Peak joint speed and acceleration are reported separately. Discrete sampling is not continuous collision proof, and contact labels are not force measurements.

## Development results

The first fixture takes five frames (60–64) of the earlier corrected sphere clip and applies a declared +2-degree local X wrist rotation to both hands. It retains the authored object trajectory, region patches and contact limits. This is a local repair test, not a new generated action. The original source and reference crop are preserved.

| Variant | Contact failures / samples | Geometry failures / samples | Minimum full-skin object clearance |
| --- | ---: | ---: | ---: |
| Perturbed sphere source | 34 / 34 | 0 / 17 | +2.584 mm |
| Sphere fit, worst penalty, 3 × 40 iterations | 0 / 34 | 0 / 17 | +2.220 mm |
| Box source, same motion | 34 / 34 | 17 / 17 | −25.281 mm |
| Box fit, worst penalty, 3 × 40 | 34 / 34 | 17 / 17 | −20.545 mm |
| Box fit, balanced penalty, 3 × 40 | 34 / 34 | 17 / 17 | −17.934 mm |
| Box fit, balanced penalty, 6 × 100 | 34 / 34 | 17 / 17 | −6.284 mm |

The box changes the target primitive to side faces containing the same grip points. It is an explicitly different scene condition, not independent action coverage. Every candidate passes the original per-run source-relative hard edit budgets. The largest rotation edits are 0.008382, 0.394206, 10.614669 and 12.917862 degrees, respectively; root lift stays near 0.022 mm. The very small sphere repair is enough to restore the declared contact condition; it does not restore the original wrist pose or demonstrate large-error recovery.

The longer box fit reduces maximum patch-normal error to 11.127457 degrees, still beyond the 10-degree limit. Its maximum anchor error is 5.106134 mm, beyond the 5 mm limit. Neither additional iterations nor a lower penalty value constitutes acceptance. All box failures are retained, and failure of these local searches does not prove infeasibility.

Motion regression measurements also remain visible. Sphere peak joint speed stays 0.363166 m/s; peak acceleration changes from 6.180514 to 6.180777 m/s². The short balanced box candidate reaches 0.366984 m/s and 6.357303 m/s²; the longer candidate reaches 0.363166 m/s and 6.257815 m/s². No temporal or human-quality approval is inferred from contact repair.

Sixty-five focused tests pass, including numerical derivative checks for the regional terms, sphere/box distance derivatives, existing body/finger bounds and authoring rejection tests. Godot matches all five frames and 77 bones of the sphere candidate and the short balanced box candidate within 0.226 micrometres in position. That engine test establishes fidelity even for a failing motion; it does not approve contact quality. The longer box variant has not been through that engine check.

Evidence is retained under `reports/region-fit-pilot-v1`, `reports/region-fit-box-pilot-v1`, `reports/region-fit-box-balanced-v1`, `reports/region-fit-box-balanced-long-v1`, their audit folders, and `reports/region-fit-engine-v1`. All runs are terminal, all raw failures and implementation snapshots remain preserved, and no reserved held-out case was used.

## Scope and next work

Primitive targets, native SOMA humanoids and grounded yaw-only actor placement are supported by this experimental path. Whole-body collision sampling in the optimizer remains incomplete; the exported audit checks the full mesh vertices. Partner fitting, arbitrary target rigs, Studio region editing, long-sequence stability, transitions, self-collision, forces and anatomical/human review remain open. The initial studies above are development perturbation tests, not additional action coverage or reserved held-out trials. No model was trained or changed.

Next connect authored regions, fitting jobs and independent failed/passing measurements to Studio. Further solver work should examine frozen correspondence choices, root-parameter conditioning and unsatisfied full-body clearance. More iterations on this same fixture are not broad validation. All 14 release capabilities remain unapproved.
