# Preserve rejected contact attempts across batch continuations

The V9 conic coverage batch completes frames 66–68 and 84–86, but retains neither update. Both local searches stop at `linear_start_unavailable`. Independent frozen-source replay verifies their saved poses, proposal arithmetic, complete original-source intervals and exact preservation of every earlier edit. **V8 stage 2 remains the retained motion; complete contact passes remain 0/62.** Ten of 21 windows have been attempted and eleven remain.

Each stage reconstructs two local records / six native poses, four margin attempts and six proposal files. Neither accepts a correction. Both complete interval comparisons retain all 22,720 original rows with zero passing loss or protected regression. The independent chain uses seven fresh/reaped processes, 1,336 bound sources and the fixed eight-stage V8 ancestry. Runtime proposal failures are not proofs of infeasibility.

The native guard completes in 1,033.578 seconds, including 375.328 seconds of admission, with 1,119,559,680 bytes sampled peak process-tree RSS. Independent resource replay verifies all 994 observations. Full independent geometric replay completes under its guard in 64.391 seconds, with 210,448,384 bytes sampled peak and 63 verified observations. Both retain the full 2 GiB estimate plus 600 MiB reserve, 7 GiB process-tree cap and existing RAM/time stops. Native stability is fifteen seconds and audit stability three seconds. Sampled memory does not establish an absolute peak or a lower admission estimate.

## Why continuation needed a separate schedule

An interval resume follows retained motion ancestry. When a batch rejects all its new windows, its latest retained interval still points to the preceding batch. Starting another batch from that interval alone loses the rejected attempts and selects them again.

`batch_contact_interval.py` now accepts an optional `--resume-batch` alongside `--resume-interval`. The completed batch supplies scheduling history; the interval supplies native motion. The schedule loader reconstructs the exact initial exclusions, every ordered stage, protocol/result/pipeline bindings, immutable archived methods, native resume references, retention decisions, final exclusions and remaining coverage. Chained continuations bind the preceding batch result and reject cycles, mismatched scope, rewritten files and changed inputs. It requires the explicit motion resume to equal the last actually retained interval. Rejected stages never supply poses. New native stages still perform their full original replay and unchanged retention checks.

Omitting `--resume-batch` preserves the existing protocol and call shape. Legacy completed V9 outputs can supply a schedule without being rewritten. Resume is scoped to this original study and canonical window partition; it is not an approval, cross-rig cache or general transfer certificate.

For example, from the project directory:

```powershell
.venv/Scripts/python.exe scripts/batch_contact_interval.py reports/box-lift-authored-height-v1 reports/new-contact-continuation/batch --start 60 --end 121 --resume-interval reports/box-lift-interval-batch-v8/batch-60-121/stage-2 --resume-batch reports/box-lift-interval-batch-v9/batch-60-121 --proposal-geometry-solver conic --stages 2 --seconds 300 --max-seconds 2400
```

Use an owned resource supervisor with the full native admission policy for the actual study; the example shows the batch arguments only.

## Verification and limits

The focused batch/coverage suite passes **108 checks** in 9.94 seconds. It covers continued all-rejected histories, mixed retention, schedule exhaustion, per-worker session ownership, stale stage/input/archive bindings, incorrect native resumes, altered exclusions, cycles and changes during a new stage. An actual replay of the immutable V9 schedule reconstructs all ten attempted windows while binding V8 as motion. The successful source guard finishes in 15.750 seconds with 594,558,976 bytes sampled peak and seventeen independently replayed observations. These small source fixtures use a 1 GiB estimate plus reserve; they do not lower full native or geometric-audit estimates. The first fixture run has three failures because the fixture incorrectly shares its in-memory session across separate workers; that run and its fourteen resource observations remain archived.

Separate numerical diagnosis of the stalled 117–119 conic subproblem tries the original solver configuration and three predeclared settings variants. All sixteen margin/configuration attempts fail the unchanged complete affine checks. Producer-free replay reconstructs all sixteen saved points, each against 1,068 scalar rows and 2,265 norm vectors. The original near-bound residuals still exceed the 1e-8 acceptance tolerance. No solver setting, tolerance, native motion or retention rule is changed by this diagnosis. The initial diagnostic harness error and every failure remain recorded. No optimality, infeasibility or general backend claim follows.

V9 batch result SHA-256: `8503ea0bfe77311c7018bea710e653b53534119ed8623226238bfa45a3fc5a05`. Independent batch receipt: `d52e677ff90456217fa2f7a528f95bdd33103bea164c431d1483d2aef277c679`. Retained V8 result: `f04bc4286388447dce0f22d3b98e8eb0759b20d7f5b1f0e90d80a92aaaa5260f`. Raw immutable evidence remains under ignored `reports/box-lift-interval-batch-v9/`, `reports/batch-schedule-resume-v1/` and `reports/conic-numerical-diagnosis-v1/`.

All fourteen release capabilities remain unapproved. This study does not validate between-key motion, full-clip realism, rig transfer, object/partner interactions generally, engine import or human cleanup. Continue remaining contact coverage and broad action, scene, partner, rig, editing, style, transition and engine validation plus actual developer review under the same project-wide goal.
