# Combined running controls

The authoring preview combines arm swing and torso lean on Kimodo's actual SOMA body. Two sliders select 12 measured combinations, with three takes each. The original neutral run appears beside the edit. Each result includes GLB, BVH, NPZ and measurements; combinations that pass all three takes can export a settings recipe.

Viewer: http://127.0.0.1:8767/reports/combined-controls-v1/viewer.html

## Experiment and results

The matrix and thresholds were saved in `benchmarks/combined-controls-v1.json` before execution. Arm targets are 10, 20, 30 and 45 degrees; lean targets are 0, 10 and 20 degrees. The editor applies lean first, then solves arm range on the result. It starts from the existing corrected neutral loops at seeds 11, 22 and 55. These seeds were already observed; this is not a new held-out evaluation or new model generation.

- 33/36 takes pass the frozen source screens. Nine of twelve target pairs pass all three takes.
- Arm ranges 10/20/30 degrees pass at all three torso levels. All 45-degree pairs fail the pose-seam screen on seed 55. Those pairs remain experimental even when the selected individual take passes.
- Maximum final arm target error: 0.000060 degrees. Maximum lean target error: 0.000009 degrees.
- Root and lower-body joint changes are exactly zero in the evaluated arrays. Contact labels are unchanged. This preserves existing lower-body defects as well as motion.
- Every combination repeats with identical arrays. Every source hash remains intact.
- All 39 GLBs (36 edits and three neutral comparisons) validate without errors or warnings. Maximum GLB joint roundtrip error is 0.000001184 m; maximum BVH joint roundtrip error is 0.000001111 m.
- Forty repository tests pass, including both final control targets, bone lengths, input preservation and rejection of failed baseline/seam checks. Four upstream Torch deprecation warnings remain.

UI checks covered changing both sliders and takes, recipe contents, failed-pair export gating, playback, scrubbing and clicking the preview. The renderer retains all eight SOMA skin influences and the disappearing-mesh fix.

## Scope

This supplies editable motion controls, not a validated agility/strength/stamina mapping. The sliders select measured variants rather than generating arbitrary prompts. Passing source checks does not demonstrate balance, self-collision avoidance, mesh contacts, human naturalness or engine import. Recipes explicitly record `human_approved: false` and `capability_mapping: null`. The preserved single-control study remains linked from the editor.

## Reproduction

From the project root, use a fresh output directory; the experiment rejects an existing one:

```powershell
.venv\Scripts\python.exe scripts/run_combined_controls.py --output reports/combined-controls-repeat
.venv\Scripts\python.exe scripts/build_combined_viewer.py --output reports/combined-controls-repeat
node scripts/validate_combined_exports.mjs reports/combined-controls-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

The recipe records target angles, application order, seed, source hash and take identifier. The summary records the protocol, implementation hashes, all failures and export hashes. No raw motion, old study or original character asset was overwritten.

Next: review the visible combined styles for naturalness, fix wide-arm loop discontinuities, then evaluate speed/acceleration/turning before proposing any action-specific game-stat mapping.
