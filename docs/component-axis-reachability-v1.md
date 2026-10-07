# Complete-timeline axis reachability experiment

The [full-scene failure](buffered-native-storage-results-v1.md) cannot be resolved by treating passing local guides as collision clearance. The existing component solver minimizes an overlap objective; it does not require every colliding sample to become clear. This experiment checks its fixed-axis targets against the original allowed boxes, then measures an explicit alternative-axis proposal. It produces no new animation or approval.

## Original-pose box conflicts

Use the previously independently replayed **56-choice** pose, all 180 same-pose stencils, 90 controls, 1,673 original times and 107,072 ordered component-pair rows. This is not the newer 57-choice corrected pose. Every original row has a 10 nm target clearance.

For each scalar affine row, maximize its gap independently by choosing the favorable endpoint of each delta bound. Directed Float64 bounds scan every row; an exact rational witness proves the selected conflict. Ignoring all native motion constraints makes this a larger relaxation, so a conflicting row cannot be rescued by adding those constraints.

| Declared delta box | Conflicting rows | Samples with a conflicting row | Selected unavoidable deficit |
| --- | ---: | ---: | ---: |
| Original local trust box, clipped to cumulative edits | 19,865 | 1,361 | 26.292575390081528 mm |
| Entire remaining cumulative edit box | 944 | 156 | 2.169084265511655 mm |

The local witness is at 0.89375 s, original vertices A:60 and B:63. The cumulative-box witness is at 0.9979166666666667 s, original vertices A:63 and B:63. Complete bounds, masks, original row identities and exact rational certificates are retained. A separate reader reproduces both complete scans, input digests, all sample masks and selected rational certificates without calling the diagnostic API.

These certificates apply to the supplied original-pose, fixed-axis affine model. They do not prove nonlinear or global motion infeasibility, exclude different separating axes, cover the newer corrected pose or justify loosening original limits. They explain why a single hard-clearance solve on these rows cannot succeed in the represented boxes.

## Bounded alternative-axis proposal

`native_reachable_component_axes.py` adds an opt-in proposal builder. It validates the original complete trajectory, clock and same-pose columns, then enumerates all original face normals and edge cross products with both signs. Near-parallel skips stay explicit. Every vertex pair and control contributes to each axis score.

The score is the minimum of the independently maximized affine pair gaps within the delta box. It is a Float64 estimate, and the maximizing deltas can differ between rows. A large score therefore proves neither joint feasibility nor motion or collision success. Stable ties retain the original axis; zero-width boxes retain original guidance. Every already-clear group's axis, margin, pair rows and derivatives remain identical. Only colliding groups may receive an alternative axis, and no old default solver is changed.

The builder retains complete candidate screens and selected models. Budgets reject whole populations: at most 4,096 signed candidate axes and eight million screening elements per frame, in addition to the existing complete-model budgets. Invalid late geometry, nonfinite rankings, incomplete clocks/columns and invalid delta boxes return no partial proposal. Caller-authenticated source membership and derivative provenance remain required.

All **23 new tests** and **121 relevant regressions** pass without skips, 144 total. The translation fixture demonstrates a reachable separating direction when the closest current axis cannot move. Tests also check every candidate sign and pair/control, late rows and last controls, clear-axis preservation, irregular weights, finite budgets, invalid inputs, zero boxes, aliases and the absence of joint-feasibility or collision claims.

## Complete measured result

The original local box experiment evaluates all **1,164,408 signed candidate axes** over 1,673 times and changes axes at 1,453 colliding samples. All 99 originally clear samples remain exact. Selected gaps and all 90 projected columns retain all 107,072 rows. The verified same-pose point stencils are reused; no native-world, derivative, solver, export or full-scene collision query is run.

| Selected local model | Conflicting rows | Samples with a conflicting row |
| --- | ---: | ---: |
| Original closest-gap axes | 19,865 | 1,361 |
| Box-potential proposal axes | 20,153 | 1,360 |

This barely changes sample reachability and increases the number of conflicting rows. It is not a practical correction or evidence for changing the default solver. Keep the failed proposal and its complete screens available rather than presenting a changed axis as a solved interaction. The objective values of different axis models are not interchangeable physical quality measures.

A separate reader reconstructs every candidate inventory, score, stable selection, pair row, projected column, clear-axis condition and selected-axis outward bound without calling the proposal, original model, support, solver or box-diagnostic APIs. Native/point provenance is bound to the completed original model reader; NumPy arithmetic and the earlier manual convex-component helper remain shared. This does not independently certify nonlinear geometry.

## Next work and limits

Move to a staged correction with fresh measurements at each changed pose, retaining original native, contact, reference, cumulative edit and full-scene gates. Do not reuse these derivatives at the newer 57-choice pose, silently convert objective slack into clearance, infer feasibility from estimated box potential, or relabel a local certificate as a global impossibility result. A future hard-target step must check joint feasibility and actual stored exports.

A separate internal seed now authenticates the earlier 57-choice, motion/material/guard-passing correction. Constructor and independent original-context replay preserve all non-anchor job fields, copied GLB bytes, native/reference/contact observations and the known full-scene failure. No production source changes and no derivatives transfer to this seed. A distinct complete 180-stencil measurement and reader are prepared for the new pose; the saved control box has room for the original central difference step in every column. Preparation is not numerical execution or approval.

Complete local producer/reader records and raw arrays remain under ignored `reports/`; the public repository does not bundle their archived inputs. The earlier lower-depth branch, all failed clips and selected source remain unchanged. No production-rig, arbitrary-action, engine, human review or cleanup-time evidence is supplied. All fourteen release evidence arrays remain empty, and the whole-project goal stays active.
