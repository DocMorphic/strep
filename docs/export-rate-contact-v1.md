# Preserving sampled joint-rate peaks during contact repair

The experimental regional fitter accepts `--export-rate-guard`. It adds separate augmented inequalities for every joint speed and acceleration sample on a quarter-frame clock. Both ceilings come from the original clip's global peaks, even when fitting starts from a previously corrected candidate. The feature is off by default.

The differentiable trajectory reconstructs local translations and rotations from global native arrays, interpolates translations linearly and rotations with shortest-path quaternion SLERP, and evaluates forward kinematics. Float32 export key times are retained. Channel quantization, native reconstruction rounding and the exporter's rotation projection are not exact parts of this proxy; actual decoded GLB checks remain necessary.

The original source and geometry-passing five-frame box candidate provide a calibration check: maximum coordinate discrepancies are 0.094 and 0.108 micrometres, and maximum acceleration discrepancies are 0.000563 and 0.000709 m/sÂ². The experiment uses `--export-acceleration-margin-fraction 0.0005`, lowering the proxy's acceleration ceiling by approximately 0.00309 m/sÂ². This is a measured development margin, not a general numerical error bound. The speed ceiling is unchanged.

Rate residuals are divided by their original peak, with a 1e-6 floor for static clips. The inequality merit sums over samples and joints, starts at penalty 10 and follows the existing stage growth factor of four. Multiplier updates use the accepted pose, with diagnostics recorded at each stage. This is a finite optimization objective, not an enforceable feasibility guarantee.

The comparison starts both variants from `reports/region-box-refreshed-interior-v1/motion.npz`, uses the original authored scene and edit budgets, and gives each six stages of 100 iterations. Both retain full object skin coverage, per-vertex object multipliers, balanced regional penalties, refreshed contact witnesses, a 0.05 mm object-clearance solver margin and a 0.01 mm contact-gap solver margin. One variant enables the rate guard and one does not. Prior passing outputs remain unchanged.

The current fixture is five frames of a previously repaired development motion. It is neither a complete box lift nor a held-out action. Preserving global peaks can hide increases on individual joints and does not establish continuous-time dynamics, anatomical plausibility, force balance, self-collision freedom or animator approval. Broader actions, longer clips and release review remain required.

To reproduce on a provisioned machine, use `scripts/fit_scene_regions.py` with the settings above and fresh output directories, followed by `scripts/audit_scene_region_fit.py`. The latter independently decodes exported motion and retains original contact, clearance and source-relative edit thresholds. No model or training data changes are involved.

The guarded export still increases individual joint peaks: 28 of 77 joints increase speed and 37 increase acceleration by more than 1e-5 in their respective units. The largest increases are 0.054286 m/s at the left forearm and 0.706781 m/s² at the left index base. These are changes from the original source, not from the already corrected initializer. The lower global peak must not be described as preserving every joint's smoothness. Detailed rows are retained in `reports/region-box-export-rates-v1-audit/per-joint-rates.json`.

## Completed comparison

| Variant | Native tracks passing | Exported contact failures | Geometry failures | Peak acceleration | Time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Prior geometry-passing initializer | 2 / 2 | 0 / 34 | 0 / 17 | 6.389502 m/s² | prior work |
| Equal-budget continuation, guard off | 1 / 2 | 1 / 34 | 0 / 17 | 6.382778 m/s² | 79.078 s |
| Export-rate guard, 0.05% acceleration margin | 2 / 2 | 0 / 34 | 0 / 17 | 6.174595 m/s² | 125.860 s |

The original source peak is 6.180514 m/s². Both new variants retain its 0.363166 m/s peak joint speed and pass original hard edit bounds. The guarded candidate's minimum full-skin box clearance is 2.049937 mm. The control's failed left-hand frame is frame 2, with a 10.000587-degree normal error against the unchanged 10-degree limit. This failure is retained.

The implementation snapshots have identical source text after newline normalization; original mixed line endings were restored between runs. Original input hashes, initialization, all other solver settings and acceptance limits match. Actual Godot checks pass 20 actor-frames across four GLBs and 77 joints, with maximum position error below 0.235 micrometres. The focused suite passes 69 tests, including interpolation derivatives, static references, multiplier updates, margin rejection and existing scene/contact/edit behavior. Live browser and human review were not performed.

Evidence is retained in `reports/region-temporal-proxy-v1.json`, both `reports/region-box-export-rates[-control]-v1` studies and adjacent audit folders, and `reports/region-export-rate-comparison-v1/comparison.json`. The equal iteration caps do not imply equal execution time or line-search evaluation counts. All 14 release capabilities remain unapproved. The next validation should use longer contact intervals and inspect per-joint changes and approach/release boundaries rather than infer full-motion quality from this short result.
