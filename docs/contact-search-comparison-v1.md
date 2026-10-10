# Matched contact search-step comparison

The current development box-lift still passes zero of 62 complete physical contact keys. Saved-pose recovery preserves useful improvements from an interrupted fit, but does not establish contact quality or completion of that fit's coverage window.

The next experiment compares normalized proposal search steps of 0.03 and 0.10, starting from the same independently verified recovered motion and the same completed V11 schedule. Each branch attempts one identical failing three-frame window. Both use the conic proposal backend, eight fit iterations, a 300-second local fit budget and ten proposal solve iterations. Original contact, object, floor, reference, joint and root limits, saved-pose checks and whole-interval retention gates remain unchanged. Search trust is an optimization parameter, not a relaxed physical tolerance.

The two branches share only an owned in-memory replay of their verified starting ancestry. The second cannot inherit the first branch's edited motion. Stored protocols, starting arrays including precision, complete original row labels/slacks, selected frames and fit budgets must match. Overall branch times are not comparable because the first includes full ancestry replay; per-fit budgets are matched. Coverage schedules remain branch-specific and neither branch is automatically promoted.

The comparison records metrics for the actually retained motion. A rejected proposal's improved diagnostics are not credited. Counts of passing contact keys are computed from per-frame checks; the existing all-keys boolean is reported separately.

Before execution, the unchanged independent local and complete-interval numerical auditors were copied and frozen for each branch. Their only adaptations are branch paths and eligibility of a completed branch after a later sibling stops. Completed outputs require separate numerical replay and resource/lifecycle verification before any adoption. Partial outputs remain diagnostic evidence.

The comparison helper, owned-session batch integration and recovery checks pass 102 focused tests. The new comparison suite is included in the Linux and Windows native CPU CI job. This is a development-fixture search experiment, not held-out evaluation, animator review, engine validation or release approval. All fourteen release capabilities remain unapproved and the single project-wide goal remains active.

Local artifacts are preserved under `reports/contact-trust-comparison-v1/`; generated poses and private fixture payloads are not published with the source.
