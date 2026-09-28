# Support correction: three versus twelve solver steps

The matched study is complete on the same24-case population: eight actions, three rigs and one seed.13 cases were eligible for foot-speed correction;11 were preserved without targeting. Source motion, editable windows, physical budgets and solver settings were fixed apart from the maximum iterations. This is development evidence, not held-out or human realism validation.

Eight targeted outputs improve the selected speed-excess objective and at least one foot-speed peak; five are unchanged. The number of clips exceeding the raw-reference foot peak drops from10 to8. All4,800 sampled Godot actor-frames pass import/transform checks for26 input/selected clips.

| Case | Left peak change (m/s) | Right peak change (m/s) | Maximum local floor increase (mm) | Root peak change (m/s²) |
|---|---:|---:|---:|---:|
| motion-036-rig-02 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| motion-036-rig-03 | 0.000000 | -0.008923 | 0.007167 | -0.000212 |
| motion-011-rig-01 | -0.012422 | 0.000000 | 0.002069 | 0.000000 |
| motion-011-rig-02 | -0.010620 | 0.000000 | 0.019357 | 0.000000 |
| motion-011-rig-03 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| motion-046-rig-01 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| motion-046-rig-03 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| motion-031-rig-01 | 0.000000 | -0.005993 | 0.004076 | -0.000051 |
| motion-031-rig-02 | 0.000000 | -0.093095 | 0.002138 | 0.000000 |
| motion-031-rig-03 | 0.000000 | -0.036948 | 0.000515 | 0.000000 |
| motion-061-rig-01 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| motion-061-rig-02 | -0.029083 | -0.029803 | 0.001191 | 0.003681 |
| motion-061-rig-03 | -0.002121 | -0.020723 | 0.000661 | 0.000000 |

Direct comparison covers9,561 times/19,122 posed meshes. Six cases have local floor-depth increases greater than the unchanged1micrometre reporting tolerance relative to the earlier correction; maximum0.019357mm. Root acceleration also increases locally in several clips, including a0.003681m/s² clip-peak increase in exhausted-walk rig02. Micrometre differences are numerical preservation diagnostics, not proof of perceptible loss.

The separate common-input quarter-frame audit covers4,774 times in13clips. Ten contain floor increases above1micrometre relative to the common input; maximum0.033197mm. This is a different reference from the preceding direct comparison. Continuous-time clearance remains unproven.

All18 correction blocks stop before the12-step budget;10 retain a nonzero objective. Recorded rejected final proposals often violate hover constraints, alongside anchor, speed, dynamics and rotation rows. Failure of these proposals does not prove global infeasibility. Thirteen remaining regressing edges lie inside editable windows and seven outside them; no boundary edges occur. Simply raising the iteration count again is not justified. Next inspect feasible-step construction/serialized precision while preserving tolerances, and address omitted support edges separately.

The immutable review package is reports/rig-jobs/support-iterations-review-v1:24 cases/96 versions, raw transfer → common input → earlier correction → further correction. All465 packaged file hashes were independently rechecked. Measured frame shortcuts expose floor/root changes and support-speed peaks. The package preserves licenses, raw inputs, notes and diagnostics; no ratings or cleanup times are fabricated. Browser verification is recorded separately.

Evidence: reports/support-iterations-comparison-v1/comparison.json; stopping-diagnostics.json; reports/support-iterations-summary-v1/summary.json; reports/support-iteration-pair-audit-v1/complete-summary.json; reports/support-iterations-quarter-audit-v1/completion.json; reports/support-iteration-coverage-v1/summary.json; reports/rig-jobs/support-iterations-review-v1/package-verification.json.

The broad project goal remains active. Partner/object penetration, semantic correctness, calibrated capability/style controls, held-out transfer and human cleanup review remain open release requirements.
