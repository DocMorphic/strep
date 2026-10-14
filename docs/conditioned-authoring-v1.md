# Explicit conditioned authoring

`scripts/native_conditioned_authoring.py` adds a separate CLI path around the existing authoring job. Given a validated ordinary recipe, it preserves the original recipe and inputs, creates weight-only actor derivatives, rebinds contact/geometry and optional object-edit/rotation-speed policies, and runs the ordinary engine authoring and replay stages. It then gates the combined sampled result on original-reference skin fidelity. Numerical failures remain completed failures; nothing is automatically adopted in Studio.

```powershell
python scripts/native_conditioned_authoring.py path/to/ordinary-recipe.json path/to/fresh-output
```

Use the project environment and existing resource supervisor when running locally. Actor names and prompts have no action whitelist. Source recipes retain their strict v1/v2 contracts. Both actor-only and object/partner schemas use the same ordinary authoring implementation. Input/output separation, immutable input snapshots, source and method hashes, saved stage results and every completed stage file are checked. Exceptions retain partial outputs and a terminal failed pipeline.

All 71 related Python checks pass, including nine new wrapper checks. They exercise the conjunction of both acceptance gates, source/evidence tampering, failed fidelity, busy workers and fresh-output requirements. A small two-actor/object fixture executes real weight export, numerical authoring and full replay with only synthetic engine execution mocked; it is not actual-engine evidence.

The real Godot 4.7.2 actor-only wrapper run on the previously corrected crawl passes both authoring and original-reference fidelity at all 2,017 times and 1,029 vertices. Original/imported maximum skin error is 0.002642 mm against the unchanged 0.1-mm tolerance. It takes 83.094 seconds of guarded execution; all 100 resource observations replay. The 71-test job takes 418.937 seconds with 431 observations, all replayed. No limits or realism thresholds were changed.

Fresh replay checks every original input, method and saved output binding, replays the complete engine observations, and reproduces every fidelity array exactly. It performs zero additional engine executions and takes 43.704 seconds; all 61 resource observations replay.

Private records remain under ignored `reports/conditioned-authoring-validation-v1`, `reports/crawl-conditioned-authoring-v1` and `reports/crawl-conditioned-authoring-replay-v1`. The prior seven-action conditioning study retains four raw floor failures. The focused hosted workflow for the preceding export/fidelity commit passes all eight Windows/Ubuntu jobs; this wrapper still needs its own hosted outcome.

This path is CLI authoring integration. Studio selection, downloadable game-package receipts, actual object/partner engine validation of this wrapper, real-time playback, physics, human review and release acceptance remain unfinished. It does not authorize training or consume reserved held-out cases. All fourteen release capabilities and gates remain unchanged.
