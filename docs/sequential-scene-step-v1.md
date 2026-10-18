# Retaining nonlinear scene steps without losing passing conditions

Development component, 2026-10-18. The preceding articulated trial reduced
worst overlap but lost contacts that already passed; a feasible linear model
was not a feasible motion. These changes keep that failed trial intact.

The conic minimax proposal now accepts a complete Boolean `protected_rows`
mask. Those rows remain in the complete minimax population and also receive
hard linear constraints without peak slack. A declared model-only search
reserve keeps them inside the predicted zero boundary. The original default
without protection remains supported. Every source-relative control-vector
ball remains mandatory; neither controls nor physical values are clipped.

`scripts/sequential_scene_step.py` adds `SceneStepGuard` for complete named
signed observations. Each supplied row's original physical pass boundary is
zero. A nonlinear proposal can be retained only if its control vectors stay
inside the original unit balls, every previously passing row remains
nonnegative, and the largest violation toward the declared search targets
strictly decreases. Newly passing conditions become protected after retention.
Average improvement, unchanged worst error, a lost contact of even 1e-15 or
partial/reordered row populations cannot replace those rules.

Search reserves tighten the target without changing the original boundary.
A step may pass an original physical row while still missing its interior
search target; both decisions remain visible. State owns its complete controls,
rows and reserves. Rejected steps cannot update it or rebase the edit budgets.
This guard compares caller-supplied observations; it does not prove source
binding, geometry coverage, exported motion, anatomy or release quality.

All **157 source cases** pass locally: the prior 142 plus protected conic and
nonlinear retention cases. Tests cover hard predicted contacts, preservation
of every supplied row, complete masks, tiny nonlinear regressions, newly
protected conditions, original control budgets, separate original/search
decisions, strict worst-error progress and owned state.

Local evidence: `reports/sequential-scene-step-tests-v1`. The next real study
keeps the original high-five inputs, five-degree joint/two-centimetre root
permissions and physical screens. It will relinearize only at retained states,
record rejected steps and preserve complete original-relative limits across
continuations. Numeric success on supplied rows is not whole-scene clearance
or animation approval; the full project goal stays active.
