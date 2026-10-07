# Worst material depth before aggregate clearance guidance

The [finite-iterate experiment](finite-guide-iterates-v1.md) found a stored-motion-feasible proposal that made overlap deeper while reducing aggregate guide loss. `scripts/native_material_peak_step.py` now separates those objectives. It complements the earlier block-based partner-depth proposals with complete indexed material witnesses, original native bounds and optional event/uniform parameter equations.

```python
from native_material_peak_step import direction

step, report = direction(native_rows, native_jacobian,
    complete_gaps_m, complete_gap_jacobian_m, complete_witnesses,
    controls, lower, upper, trust,
    parameter_rows=original_parameter_rows)
```

The caller authenticates every original witness and derivative. Witness kinds identify every declared contained vertex and every triangle-separation contribution; the function does not infer contacts or select a smaller population. Gaps and their Jacobian use metres. Each contained-vertex gap must be nonpositive at the anchor. Face identity, barycentric weights and world normal remain fixed local proposal choices, so this depth proxy is not a changing nearest-surface signed distance.

The first conic phase minimizes maximum negative contained-vertex gap, with every original native norm hard. The second phase includes every guide slack and minimizes complete squared negative guide deficit under the first **verified candidate's** depth ceiling. Neither ceiling nor phase is called an optimum. Exactly fixed passing native rows can be omitted from conic encoding; the complete strict ray check still evaluates every original row. No approximate derivative threshold, norm-cap change, control/time subset or geometry-limit relaxation is used.

A returned finite iterate retains its original solver status. Infeasibility/numerical-error statuses, incomplete/nonfinite points and out-of-box controls reject. The explicit original ray validator requires a nonzero represented step with zero norm/trust/control excess. Homogeneous parameter rows use the existing 1e-9 proposal tolerance. A candidate must strictly improve peak material depth; a secondary candidate must additionally stay at or below the verified first-phase ceiling with no depth allowance and improve its complete guide loss. If the secondary phase fails, retain the verified first-phase proposal. Actual export/contact/reference/scene checks still decide whether either is usable.

84 initial tests passed; after adding explicit secondary-fallback and coupled-native-row tests, the final 87 focused cases pass with zero skips: 29 new peak cases, 43 existing iterate cases and 15 existing hinge-solver cases. One test places 100 conflicting aggregate rows against two containment witnesses and verifies that aggregate guidance cannot buy a worse depth peak. Other tests cover strict original caps, complete coupled norms/scales, parameter locks, observer isolation, certificate/point rejection, preflight validation and fallback after a secondary priority violation. The new suite is registered once in Linux/Windows CI; hosted success remains unverified.

## Same-point fixture measurement

Reuse the authenticated, separately replayed 53-choice material model: 90 controls, 30,450 original norms, 1,707 native samples, 1,673 geometry times and 964 guides. All 180 complete same-point derivative stencils are reused; zero new stencils are claimed. All 954 triangle contributions and ten contained-vertex witnesses remain present, alongside the 18 event or 72 uniform parameter rows where requested.

All three first phases produce strictly verified affine depth improvements. Each secondary phase returns `AlmostSolved` but exceeds its strict verified depth ceiling, so all three retain the first phase. The overruns are about 2.53e-11 m, 2.07e-7 m and 4.18e-13 m for the original, event and uniform variants respectively. These are recorded numerical priority failures, not a reason to relax original motion or scene acceptance.

| Family | Stored-motion failures at fractions 1, 1/2, 1/4, 1/8 | Seven-frame depth at those fractions, mm |
| --- | --- | --- |
| Original norms | 0 / 4 / 0 / 6 | 4.663817166 / 4.864931067 / 4.983753144 / 5.043137548 |
| Event-preserving | 4 / 4 / 1 / 6 | 4.682129421 / 4.891623583 / 4.996894066 / 5.049653421 |
| Uniform increment | 1 / 2 / 4 / 3 | 4.908408302 / 5.005405150 / 5.053941179 / 5.078213006 |

All twelve exports pass original contact/reference/control/trust checks, and all improve seven-frame maximum depth versus the original 5.102497259 mm seed. Only the original full and quarter fractions pass every stored scalar/vector motion condition. Fractional motion validity is not monotonic because actual stored outputs remain authoritative.

The full original-norm export is selected for the unchanged complete scene audit. Its maximum partner vertex depth across all 1,673 times is 4.697751897 mm, below the original 5 mm limit, with zero over-limit vertex incidences. The scan still rejects: 30,015 proper triangle crossings and 1,591 failed sample checks. The seed had 28,904 proper crossings and 1,527 failed sample checks. Depth improves while crossing coverage worsens; this is not a collision-free or professional-quality animation.

A separate original-context consumer reconstructs the 53 storage choices, event/uniform equations, all six conic models and retained solver statuses, every complete strict ray and priority/fallback decision, and all twelve actual exports with every native condition and seven-frame geometry query. Complete witness/derivative populations are authenticated from the earlier full replay, not newly recomputed. Full-scene archive transport is verified; collision arithmetic is shared rather than independently reimplemented, and no optimizer proof is claimed.

Next, address secondary numerical priority handling and reduce triangle crossings while preserving the demonstrated motion/depth behavior. Assess actual full-scene geometry separately from local material and aggregate proxies. Preserve every rejected output; do not use extra storage repairs solely to promote the ten motion-rejected proposals.

Original assets remain selected, all fourteen release evidence arrays remain empty and the full-project goal stays active. This fixture study establishes no production anatomy, arbitrary-action semantics, engine, continuous-physics, animator-review or cleanup-time approval. Raw outputs and source snapshots remain immutable under ignored `reports/`.
