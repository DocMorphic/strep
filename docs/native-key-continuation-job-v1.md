# Recipe-driven verified continuation

`scripts/native_key_continuation_job.py` makes the [verified continuation API](native-key-continuation-v1.md) available as a bounded, offline command. It starts from the parent's saved edited controls. The original initializer supplies the rig, clocks, active keys, root/endpoints, edit limits, scene/contact intent and all four source motion-cap arrays. The edited clip never becomes a new reference.

This version accepts a completed standard `strep-native-key-interval-restoration-v1` parent and its complete `strep-native-key-restoration-replay-v1` receipt. It deliberately rejects private trial schemas and continuation-job parents: recursive chains and migration of the earlier private 35-rate/12-floor result are not implemented. That earlier result remains retained evidence, not input accepted by this command. There is no new Studio selector.

Save this recipe outside the fresh output directory. Paths resolve relative to the recipe. Replace the three placeholders with independently recorded SHA256 bindings of the parent's original result, request and numerical replay; the command does not automatically trust replacement files.

```json
{
  "schema": "strep-native-key-continuation-job-v1",
  "parent": {
    "path": "standard-restoration",
    "result_sha256": "<trusted result SHA256>",
    "request_sha256": "<trusted request SHA256>",
    "replay": "standard-replay/result.json",
    "replay_sha256": "<trusted replay SHA256>"
  },
  "iterations": 3,
  "trust": 0.02,
  "difference_step": 0.001,
  "backoffs": 8,
  "maximum_seconds": 650
}
```

Using the project's prepared offline Python environment, run through the unchanged resource supervisor:

```powershell
uv run --offline --isolated --no-project --python 3.10 --with-requirements requirements-ci.txt python scripts/run_guarded_job.py --worker scripts/native_key_continuation_job.py --output reports/my-continuation-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 900 -- reports/my-continuation-recipe.json reports/my-continuation
```

The worker lock allows one numerical job. Admission requires approximately 2.78 GB available RAM for 15 seconds; the independent supervisor retains its runtime RAM/RSS/time limits. `maximum_seconds` bounds search at phase boundaries after fresh starting-state verification, rather than interrupting a matrix build or export. The supervisor's 900-second execution deadline covers the entire worker. Deferred, failed and interrupted outputs remain visible and cannot be replayed as completed jobs. Dependency/model/asset acquisition remains separate; this is not a bundled offline installer.

Each proposed step is exported and fully sampled. A retained candidate must preserve previously passing individual rate/geometry conditions, cannot increase existing individual violations or introduce new degenerate face IDs, and must retain all original edit/contact/root checks. Larger rejected steps remain alongside retained backoffs. The final output keeps the original selected and quality/training/release flags false, including when sampled numerical conditions pass.

The new auditor checks the parent bindings and freshly reconstructs its starting state. It then recreates every returned clip and complete observation array, checks protected scene intent and contact/geometry decisions, and replays each backoff from the saved edited start rather than from `problem.initial`. It checks all selected controls and history coverage without executing the optimizer. Its receipt uses the separate `strep-native-key-continuation-job-replay-v1` schema.

Record the new job's result and request digests, then replay with fresh output:

```powershell
uv run --offline --isolated --no-project --python 3.10 --with-requirements requirements-ci.txt python scripts/run_guarded_job.py --worker scripts/audit_native_key_continuation_job.py --output reports/my-continuation-replay-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 900 -- reports/my-continuation reports/my-continuation-replay --expected-result-sha256 <trusted-new-result> --expected-request-sha256 <trusted-new-request>
```

After each job, `scripts/audit_guarded_job.py` independently replays its resource trace. Resource completion and numerical replay do not establish animation realism, continuous collision, balance, semantic correctness, engine fidelity or animator approval. The existing 35 rate failures and twelve floor failures remain unresolved, and all project release requirements remain unchanged.

## Checked software validation

All fourteen selected tests pass in 165.82 seconds. The unchanged guard completes in 183.000 seconds with 181 resource observations; its resource trace replays with matching bindings. Tests cover exact complete clip/cap reconstruction and public numerical replay, altered result/request/start-receipt bindings, forged approval, invalid budgets/schema/digests, and a saved nonzero-control start whose full step creates a new failure while the half step is retained. The numerical fixture and controlled search test have different scopes; neither substitutes for humanoid quality or human review. Evidence remains locally under ignored `reports/native-key-continuation-job-validation-v1`.

## Development-character command run

The new public command runs one iteration from the earlier verified 47-rate/18-floor state, with 372 active controls and a 0.01 trust radius. The original 30-degree/22-cm edit limits, fixed root/endpoints, raised-foot point target, 5-mm floor and original 120-Hz motion-cap arrays remain unchanged. This is an authored preservation target, not evidence of planted support or correct action semantics.

| Returned export | Rate failures | Floor failures | Decision |
| --- | ---: | ---: | --- |
| Verified saved start | 47 | 18 | Starting state |
| Full step | 30 | 90 | Rejected |
| Half step | 38 | 35 | Rejected |
| Quarter step | 41 | 17 | Retained for further research |
| Final repeat | 41 | 17 | Still fails acceptance |

The final peak floor depth is 5.649871 mm. Six rate rows and one floor sample are repaired relative to the verified start, with all individual no-worsening guards retained. The command completes in 211.484 seconds with 209 resource observations; the guard's resource trace replays with matching bindings. All five exports and earlier evidence remain intact under ignored `reports/kenney-continuation-command-v1`. This is separate from the earlier private three-iteration trial, whose better 35/12 result remains unchanged. No completed trial is overwritten or promoted.

A separate public replay passes in 192.265 seconds/190 resource observations. It freshly verifies the saved nonzero-control starting state, all five returned clip bytes and complete contact/geometry/motion arrays, the two rejected steps, the retained quarter step and the final 41/17 rejection. Its recorded resource trace replays with matching bindings. Evidence remains under ignored `reports/kenney-continuation-command-replay-v1`. Shared curve/reader/skin methods are explicit; no optimizer, engine, training, new generation, held-out fixture or human review runs in this replay. The entire-project goal stays active.
