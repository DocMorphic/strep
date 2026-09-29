# Contact-window preflight

The experimental stationary-pin workflow now checks held-pose travel requirements **before fitting**. A conflicting request produces `needs_authoring_change`, a readable explanation and a JSON report; it creates no candidate animation. It does not silently change the window, contact times, targets, accuracy or rate limits.

`plan_point_rate_window.py` searches expanded integer windows while retaining both endpoints as held interior source poses. It tests every earlier start and later end against every requested point. Each approach/release speed cap stays at its original value, and acceleration caps remain recorded unchanged. It does not recompute larger caps from a wider portion of the source. A proposed window only passes necessary endpoint-distance checks; it is not certified feasible motion.

```powershell
# Inspect a retained trial using its original caps.
.venv\Scripts\python.exe scripts/plan_point_rate_window.py reports/carrier-support-point-rate-v1 reports/contact-window-plan.json

# Preflight is automatic with the experimental per-point guard.
.venv\Scripts\python.exe scripts/study_carrier_support.py reports/scene-carrier-v1/input reports/contact-window-check --rate-guard --point-rate-guard
```

Use fresh report paths. These commands require the local source fixture and licensed assets. `window-preflight.txt` explains individual conflicts in millimetres; `window-preflight.json` retains all tested boundaries. An explicit `--allow-incompatible` option can reproduce a best-effort diagnostic fit despite the warning. Such a fit is still unapproved; this flag does not change any constraints.

## Actual fixture outcome

For the retained 180-frame platform source, frames 20–159 still have three endpoint travel conflicts. Starting at frame **8 or earlier** passes both approach-distance checks. However, **none of the 20 held release endpoints from 159 through 178** passes both release checks with the unchanged caps. The closest joint release outcome is frame 162, where the left foot still has a **0.0626 mm** travel deficit after the explicit 1-micrometre boundary error allowance.

Consequently, the planner returns **no complete window proposal**, rather than recommending the successful approach boundary alone or quietly freeing the clip's final pose. This trial requires an explicit change to another authoring requirement before all endpoint conditions can coexist. The search makes no claim about changing target timing or speed budgets being artistically acceptable.

The final implementation was exercised on the actual fixture with a solver spy that raises if called. Preflight reported three conflicts, retained the requested range and caps, produced the readable report, and **never called the solver or created a candidate**. Evidence is in `reports/carrier-window-preflight-check-v2`; the earlier preflight and checks remain in their original directories. No new fitting or engine run was needed because no animation changed.

Seventeen distinct focused tests cover nearest expansion, all-point agreement, nonmonotone source trajectories, missing/duplicate constraints, no-solution behavior, endpoint budgets and existing between-key audit behavior. Inputs and implementation copies remain recorded for the actual preflight.

This began as an experimental CLI check. [Studio now exposes a separate read-only timing check](studio-contact-timing-v1.md) with source snapshots, bound material points, frame bounds and saved reports. The existing Apply correction method remains separate and does not enforce these rate limits. The general animation system and all fourteen release capabilities remain unapproved.
