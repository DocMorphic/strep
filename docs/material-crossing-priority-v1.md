# Worst triangle support with a hard material-depth ceiling

The [fresh moved-pose model](rebased-material-peak-v1.md) reduces contained-vertex depth while leaving many triangle crossings. At its starting pose, the worst declared triangle-support gap is -10.336808919 mm, versus a worst contained-vertex depth of 4.697751897 mm. These are different measurements: a fixed-axis support gap is neither signed distance nor a collision verdict.

`scripts/native_material_crossing_step.py` supplies a separate local proposal. For every declared triangle corner-pair row, it minimizes a single worst affine deficit relative to the explicit clearance. Every original native vector norm, control/trust box and optional homogeneous parameter row remains hard. Every contained-vertex witness is also hard, bounded by the starting worst material depth with zero acceptance allowance.

For gaps `g`, gap Jacobian `J`, control step `d`, clearance `c` and starting worst containment depth `D`, the added constraints are `g_triangle + J_triangle d >= c - t`, `t >= 0`, and `g_inside + J_inside d >= -D`; the objective minimizes `t`. All nine ordered corner pairs of each declared triangle record remain present. Repeating a row does not increase its objective weight as it would in a sum of squared deficits. The caller must authenticate the complete witness population and derivatives at the same pose; this method cannot discover omitted triangles or times.

Solver statuses are retained. Certificates, numerical errors, nonfinite points and out-of-box iterates cannot become motion. An explicit finite ray checks every original affine native norm with zero acceptance allowance. The candidate must additionally preserve the starting material-depth ceiling, preserve parameter rows within the existing 1e-9 proposal check, and strictly reduce the worst triangle deficit. None of these local checks approves actual contact, decoded motion or scene geometry.

The 34 new tests cover competing triangle rows, repeated contributions, coupled native bounds, control limits, containment as a hard constraint, observer isolation, invalid inputs/statuses, strict depth rejection and misleading aggregate improvements. Together with the 29 existing peak-priority tests, 63 tests pass with zero skips. The new suite is registered once in the shared Linux/Windows source workflow; hosted success is unverified.

The generated two-character comparison reuses the fully replayed eight-frame model at exactly the same starting pose: 90 controls, 30,450 original norms, 1,707 native times, 1,673 geometry times, 1,110 material rows and all 180 previously computed complete stencils. There are zero fresh stencils or changed acceptance conditions. All three variants produce `Solved` proposals; the independent strict checks still decide whether each finite point can be tested. This is not an independently proved optimum.

| Variant | Worst affine triangle deficit before / after, mm | Stored-motion failures at fractions 1, 1/2, 1/4, 1/8 | Eight-frame triangle records at those fractions |
| --- | --- | --- | --- |
| Original norms | 10.436808919 / 10.209544894 | 0 / 0 / 0 / 2 | 150 / 128 / 124 / 122 |
| Event-preserving | 10.436808919 / 10.209544894 | 3 / 0 / 1 / 0 | 142 / 120 / 120 / 122 |
| Uniform increment | 10.436808919 / 10.253591521 | 2 / 0 / 0 / 1 | 120 / 120 / 130 / 130 |

The anchor has 122 records over those eight frames. Seven exports pass all stored scalar/vector motion conditions. Every export passes reference/control/trust bounds. Only the uniform full step fails one contact condition. All twelve actor pairs differ from the corresponding previous peak-priority exports. Smaller fractions are not presumed passing.

The existing depth-first rule selects the full original-norm export for the unchanged complete scene audit. Maximum partner vertex depth is 4.683168168 mm, with zero vertices over the original 5 mm limit. However, proper crossings increase from the model anchor's 30,015 to 30,385, and failed samples increase from 1,591 to 1,609. The previous published peak export is also better at 4.483570315 mm and 29,937 crossings. The new candidate remains rejected and is not promoted to another internal seed.

The separate original-context reader reconstructs all three complete conic matrices/objectives, the 18 event/72 uniform equations, strict native-ray prefixes, starting containment ceilings and all twelve actual exports, including original source rates, contacts, static references and all eight frame queries. Same-pose witness/derivative reuse is bound to the completed prior full replay. The full-scene archive is transport-verified with shared collision predicates; collision arithmetic and solver optimality are not independently certified.

This comparison exposes a failure of the proposed local objective: reducing the worst frozen-axis deficit does not ensure fewer actual intersections, even with locally nonregressing containment depth. The next correction needs measured full-scene crossing behavior and changing separation geometry, rather than promotion based on the affine score alone. Raw outputs and rejected fractions remain immutable under ignored `reports/`; no model or dependency changes are involved.

Original assets stay selected, all fourteen release evidence arrays remain empty and the full-project goal stays active. This generated fixture supplies no production-anatomy, arbitrary-action semantics, engine import, animator-review, cleanup-time or exhaustive motion-coverage approval.
