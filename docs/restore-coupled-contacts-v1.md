# Saved-motion native repair with fixed contact guards

`scripts/restore_coupled_contacts.py` connects the recentered proposal model to
an offline, source-bound correction workflow. Its input is a rejected control
vector plus an optional preceding feasible control vector for the same original
clip and edit permissions. Controls always stay relative to the original source.
The original source must already satisfy its native conditions; this stage
repairs edits that depart from it. Earlier native scene-fitting stages handle
requests whose original contact positions are infeasible.

```powershell
python scripts/restore_coupled_contacts.py contacts.json permissions.json surface-policy.json geometry-policy.json reports/repair-v1 --rejected-controls rejected-controls.npy --baseline-controls previous-controls.npy --iterations 3 --phase-seconds 120 --maximum-iterations 200
```

Omit `--baseline-controls` to use the original zero controls. The workflow first
re-exports and decodes the baseline. It must pass every native condition, every
original individual contact guard and every static edit check. The rejected
vector is separately exported and decoded; it must pass static edits and actually
fail native conditions. An already feasible input is rejected instead of being
reported as a successful repair experiment.

The rejected motion supplies the derivative origin. The preceding feasible
motion supplies the contact reference throughout all iterations. Original rate
caps, tolerances, clocks, component boxes and permissions never reset around an
intermediate candidate. All complete native rows remain hard, including contact
position and frame speed. Every authored surface orientation and side gap keeps
its own guard against the baseline; the original source guards are also checked.

The solver has the existing explicit phase time/iteration budgets. Raw directions
are saved before validation, and usable directions are projected into the exact
trust and original component boxes without slack. Each backoff is independently
exported, decoded and recorded. An intermediate repair requires every contact
guard and static edit check to pass, a nonincreasing worst native excess and a
strict reduction in squared positive native excess. Eliminating all positive
native excess also counts as progress when the old squared excess is tiny. A
positive native residual of any size still fails feasibility.

Intermediate candidates can remain native-infeasible. They are derivative
origins only, with no geometry approval or retained animation. The loop stops on
native feasibility, a stalled proposal, a timeout without direction, or its
explicit iteration budget. A native-feasible candidate must additionally improve
contact against the fixed preceding baseline: worst positive contact excess must
not increase and the squared positive excess sum must decrease. Native repair
without contact improvement does not trigger retention.

Only an eligible final candidate receives the complete declared sampled geometry
audit, at most once per run. Exact geometry donors are optional through
`--geometry-donor`; old archives lacking complete query inputs cannot be reused.
Geometry archive size limits reject instead of dropping samples. Retention
requires complete native feasibility, individual original/baseline contact guards,
contact improvement and a passing complete geometry result. If anything fails,
`retained-controls.npy` contains the preceding baseline controls, which may be
nonzero. Every rejected trial stays available. The product's original source
selection remains unchanged, and quality/release approval stays false.

The workflow binds its source assets, methods, copied specifications, full
condition/model arrays and closed decisions with hashes, checks mutation before
solving and before completion, uses one numerical thread and the shared
production-worker lock, and requires a fresh output directory. Failed runs retain
their pipeline error and existing outputs. It does not alter existing cumulative
studies or integrate with Studio yet.

## Validation scope

Validation uses small serialized synthetic fixtures, including independent
uncached contact and whole-geometry replay. Controlled directions exercise
multi-step native repair, one fixed reference across infeasible origins, original
guards, nonzero fallback, remaining authored failures, failed geometry, timeouts,
strict tiny native excess, source/observation mutation, cap resets and busy locks.
A command fixture invokes the real bounded CPU solver and records its actual
outcome without assuming convergence. The first command test correctly rejected
the busy production checkout's lock; that failed test and exact source/log
snapshots are preserved locally. Its revised fixture runs in its own copied
source checkout with its own lock. No production lock was bypassed.

Partner touch and hold fixtures preserve both complete world populations and
the unedited partner asset. Their native/contact repair passes, but complete
geometry rejects unavailable containment because their triangle meshes are open.
Both failed retention expectations and full fixture outputs are preserved. The
revised tests require that specific geometry rejection and unchanged baseline
fallback, with no alteration to the workflow or its limits.

No real-character repair result, universal convergence, engine equivalence,
self/continuous collision or human motion-quality approval is claimed. Existing
authored failures stay visible. Production correction and full independent replay
remain separate work under the unchanged project-wide release criteria.


All 37 focused workflow cases and 351 isolated native/contact/geometry/solver cases pass. Local evidence: `reports/restore-coupled-contacts-tests-v4.log`, `reports/restore-coupled-contacts-clean-source-v2` and `reports/restore-coupled-contacts-repair-v1`.


One preserved small command fixture uses the actual CPU solver: both phases report AlmostSolved, its 483 native failures fall to zero and complete declared sampled geometry passes. The retained partial improvement still fails one authored surface condition. The focused test independently replays native conditions, uncached contact and whole geometry. This is a synthetic fixture, not a production character, partner geometry or human-quality result. Local evidence: `reports/restore-coupled-contacts-command-v1`. Both mistaken open-partner retention expectations are preserved in `reports/restore-coupled-contacts-repair-v2`.


The [saved repair replay command](verify-coupled-restoration-v1.md) now checks complete closed trial populations, fixed original caps and contact references, raw keys, directions and retention decisions, then reruns all declared geometry/containment queries using the unchanged shared kernel. Its 27 focused and 378 isolated source cases pass; the actual production restoration and fresh replay remain pending.
