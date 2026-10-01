# Continuing geometry repair with serialization headroom

The preceding headroom study found an internal state with all hard motion, palm,
arm and finger edit limits intact, but 251 old signed witnesses and 21 new
projection rows still failing. This continuation starts from that exact saved
state rather than restarting at an earlier, easier candidate.

## Procedure

The completed source, original controls/scales, clocks, reference assets, frozen
donor mesh-cut rows and archived methods are hash-bound and verified. Its saved
final metrics must reproduce within 1e-12 before solving. Original caps, scales
and row populations remain frozen across the entire continuation.

Up to three new local models are built at the exact last admissible internal
state. Each model retains the seven observed motion-error headroom targets as
proposal-only cap reductions. The signed-witness proposal reserve is recomputed
from twice the current serialized/unrounded discrepancy plus the existing 5e-7
normalized floor. These targets are empirical, not certified error bounds.

Each proposed direction is replayed at all 256 fractions i/256 with the original
actual limits. The outer loop independently rechecks hard groups, control bounds,
the original objective ceiling and strict improvement of the worst margin before
advancing. It stops if no admissible improvement exists; it does not keep
repeating a stalled proposal. Every model, direction, trial and internal state
is saved separately from selected output clips.

Numerical feasibility grants access to the unchanged 53-time full-mesh guard.
Independent decoded motion/contact/geometry checks remain mandatory before any
changed output can be selected. A numerical pass or relative geometric
improvement is not animation-quality approval.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --continue-headroom-study reports/coupled-motion-headroom-v1 --iterations 3
```

This requires the bound local studies and assets, excluded from Git. Seven new
model-free tests verify exact continuation, stopping on stagnation, rejection
of hard-motion regressions, unchanged caps across iterations and bounded budgets.



## Completed bounded result

All three new linearizations take internal steps. Their 256-point replays retain
249, 249 and 38 hard-feasible samples respectively. The final worst normalized
violation is -2.935045e-6, a 98.74% reduction from this continuation's seed.
All original motion/palm/arm constraints, all 3,610 finger edit rows and all
2,448 new projection rows pass. However, **206 old signed witnesses still fail**,
with maximum excess about 5.870091e-8 m. The internal candidate remains rejected.

The fixed-axis objective is 3.579549 mm, only 0.001393 mm below the donor's
3.580943 mm. This narrow proxy improvement does not show useful physical contact
improvement. Selected GLBs remain byte-identical to donors; the full mesh guard
is not run, and Studio is not changed. All 987 minimal source tests pass.

All 3,024 bound inputs, 70 archived/current methods and 13 output files were
rehashed. Study `reports/coupled-headroom-continued-v1` binds:

- Result: `b82c9b8d4d688b4531ec398f6ba8c6b71eea5ad005931861513661a52329b9d0`.
- Request: `be7ee965ef367d4a86e22f9de1abfe772ccb653a8ebe7e413f2bcd2cb8a3b9b8`.
- Iteration summary: `8bcacf9db5ec394d3b521d5185d223d520e71f3204f2d94217b681bcc76644af`.
- Final constraints: `e50fcadb9ef9f87867dcf22afc45a60ef27dc0513a676acdcae491301d7a3e2b`.

## Contact-contract diagnosis changes the next experiment

Feasibility restoration alone cannot establish a convincing interaction here.
The donor's complete 53-time audit still has 14 samples above 5 mm vertex depth,
with directional maxima 20.975834 and 20.792016 mm. A small improvement in the
fixed-axis objective does not imply that those physical intersections clear.

At contact time 2.091722595 seconds, the preserved skinned palm anchors are
22.623660 mm apart. The current repair allows each anchor to move by 0.01 mm
and separately restricts the relative-vector change to 0.01 mm. For original
relative vector d and new vector d', the reverse triangle inequality gives:

`norm(d') >= norm(d) - norm(d' - d) >= 22.613660 mm`.

Consequently a hypothetical stricter **2 mm anchor-gap goal** is impossible
under this preservation lock; it requires at least 20.623660 mm relative change.
This is a statement about the selected surface anchors, not proof that all
other hand surfaces do or do not touch. The 2 mm condition is an explicit
candidate for a new authoring experiment, not a retroactive acceptance change.

The read-only diagnosis binds the existing completed mesh audit, its baseline
snapshot and the finger-repair contact request. Local artifact
`reports/contact-anchor-contract-v1/diagnosis.json` has SHA-256
`d406c6a6d511417aaabbd9335343d71566d4ebec001069b5cb7fca978cf7a0ee`.
The arithmetic can be reproduced from `initial_palm_centers_m` and
`point_drift_limit_m` in the bound finger request; the solver's `palm_vectors`
includes both individual displacement and the relative-vector displacement.

After this bounded run, prioritize a separately declared contact-target and
approach-planning experiment over more micro-residual replay. Author a shared
palm meeting target, permit contact-key changes within an explicit edit window,
and assess approach, meeting and departure geometry together. Preserve the
original inputs and benchmark results; retain motion, root/support and edit
limits where applicable, and explicitly report incompatibilities. A new target
condition cannot be reported as passing the old frozen-contact study. Full
geometry, action correctness and developer review are still required.
