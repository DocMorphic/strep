# Window-preserving surface-contact fitting

The regional surface fitter now accepts `--edit-window START END`. It preserves the initialization's rotations and root track on unselected native keys while optimizing hand regions, body-object clearance and optional source-support constraints inside the window. This carries the previously tested edit-locality mechanism into the contact solver; it does not make its augmented constraints guaranteed feasible.

## Implementation

`localized_spline.py` supplies the shared null-space control restriction used by both the joint-frame initializer and regional fitter. Existing imports from `object_grip_seed` remain compatible. The restricted fit adds free controls to recovered initialization controls within the original spline space. Root lift is masked to its initial value outside the window. Rotation and root edit limits remain relative to the original source, and the completed native motion is checked against the starting pose outside the selected keys. Shared-pose mode rejects a local window because that combination has no meaningful independently editable temporal segment.

The option defaults to `None`, preserving prior behavior. Protocols record the requested window; recipes record the control-space restriction and measured outside-key rotation/root discrepancies. Immutable fitting and Studio job method snapshots include the new helper. The original change exposed an explicit fitting option; [Studio range authoring](studio-edit-window-v1.md) now carries it through contact jobs.

## Validation

Fifty-eight focused tests pass across localization, guide references, bounded initialization, support preservation, solver stage limits and scene jobs. Four saved five-frame integration runs compare the frozen and current default solver under both legacy and physical-root coordinates; every output array is bit-identical within its matched pair. Their artifact hashes are bound in `reports/region-window-integration-v5/compatibility-binding.json`.

A separate real-character integration probe repeats the first source/seed pose for 60 keys, freezes objects and shifts grip targets by 1 cm along their box faces only on frames 12–47. One stage of five iterations changes the interior while preserving the outside seed root exactly. Outside local-rotation discrepancy is 5.29e-8 radians; original edit bounds pass and native forward-kinematics discrepancy is below 0.358 micrometres. The root lift ranges from zero to 6.701 mm within original limits. This is a synthetic code integration probe, not an action-quality result.

Earlier fixture attempts are retained: the five-frame window had no free spline controls; an off-face target was rejected before fitting; and a repeated static source with a near-zero rate ceiling suppressed the intended interior edit. The final integration probe disables that incompatible static rate guard. The actual moving study below retains its existing rate guard. No failed fixture or output was overwritten or promoted to success.

## Completed full-motion study

`reports/region-windowed-surface-v1/method.py` runs the existing 180-frame box-transfer scene with the original source as edit reference and the completed windowed arm-guide motion as initialization. It selects `[48,133]`, six stages of 100 inner iterations and a 2,400-second fitting budget. It retains full sparse skin, per-vertex object inequalities, augmented hand-region constraints, witness refresh, both inferred foot supports, physical root coordinates, the 0.001 regional solver buffer, 0.05 mm object solver margin, 0.01 mm contact-gap solver margin and existing source-relative export-rate guard.

The driver completed in 1,978.235 seconds with 686 optimizer evaluations. All six stages reached their 100-iteration limit; convergence is not established. Exact process/input/implementation records and decoded geometry, joint-rate, support and actual Godot import audits are retained. The loss printed during fitting is not a quality decision.

The window intentionally preserves existing motion outside the selected keys, including any pre-existing defects there. Boundary interpolation, locked intervals and the complete exported clip must still be assessed. Results must distinguish failures inherited from locked motion from failures introduced or retained in the edited span. All fourteen release capabilities remain unapproved.


| Measurement | Starting arm-guide clip | Surface continuation |
| --- | ---: | ---: |
| Failed contact samples / 490 | 478 | 381 |
| Failed full-clip geometry samples / 717 | 379 | 376 |
| Failed selected-window geometry samples / 341 | 326 | 323 |
| Peak selected-window box penetration | 26.768 mm | 22.762 mm |
| Peak whole-clip box penetration | 28.575 mm | 28.575 mm |
| Peak joint acceleration | 37.522 m/s2 | 38.184 m/s2 |

Original raw-source edit bounds pass: maximum rotation edit 35.9871 degrees and root lift 0-7.553 mm. The original raw-source acceleration peak is 37.9821 m/s2, so the candidate still exceeds that comparison despite the export-rate guard. Inferred source-support preservation fails at 86 of 1,398 measured samples, with 5.190 mm maximum drift against a 5 mm allowance; 36 additional material-point identity gaps remain. No planted-sole or force-balance conclusion follows.

The independent 120 Hz seed/candidate audit confirms fully locked segments match within 0.129 micrometres of skin position. Boundary-straddling samples change by up to **3.413 mm**, driven by editable root keys. Native outside-key preservation therefore does not establish preservation at every outside time. The review records this boundary regression alongside contact, support and temporal failures. Fifty geometry failures remain in fully locked segments, confirming the preflight conflict; another three remain across the boundary.

All 360 source/candidate actor-frames import into Godot with joint-position discrepancy below 0.345 micrometres. The `windowed-surface-review-v1` collection passes fifteen package hashes and fourteen permitted offline routes; the Python snapshot remains unserved. This is fidelity and packaging evidence, not approval. Exact comparisons, audit identities, stage outcomes and package verification are in `reports/region-windowed-surface-v1/completion.json` and its retained `finish.py` method.

Next compare a wider [23, 133] window with the same original source, arm-guide initializer, physical-root formulation and solver settings. This addresses the demonstrated locked-geometry conflict without changing acceptance thresholds. The result may still fail contacts, feet or timing; it must be measured rather than assumed feasible. All fourteen release capabilities remain unapproved.


The subsequent [matched expanded-window study](expanded-window-surface-fit-v1.md) reduces early penetration but still fails contacts, geometry, support and outside-boundary preservation.
