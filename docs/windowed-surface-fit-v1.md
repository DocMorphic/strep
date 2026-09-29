# Window-preserving surface-contact fitting

The regional surface fitter now accepts `--edit-window START END`. It preserves the initialization's rotations and root track on unselected native keys while optimizing hand regions, body-object clearance and optional source-support constraints inside the window. This carries the previously tested edit-locality mechanism into the contact solver; it does not make its augmented constraints guaranteed feasible.

## Implementation

`localized_spline.py` supplies the shared null-space control restriction used by both the joint-frame initializer and regional fitter. Existing imports from `object_grip_seed` remain compatible. The restricted fit adds free controls to recovered initialization controls within the original spline space. Root lift is masked to its initial value outside the window. Rotation and root edit limits remain relative to the original source, and the completed native motion is checked against the starting pose outside the selected keys. Shared-pose mode rejects a local window because that combination has no meaningful independently editable temporal segment.

The option defaults to `None`, preserving prior behavior. Protocols record the requested window; recipes record the control-space restriction and measured outside-key rotation/root discrepancies. Immutable fitting and Studio job method snapshots include the new helper. The window is currently an explicit fitting option; this change does not add a Studio window-selection interaction.

## Validation

Fifty-eight focused tests pass across localization, guide references, bounded initialization, support preservation, solver stage limits and scene jobs. Four saved five-frame integration runs compare the frozen and current default solver under both legacy and physical-root coordinates; every output array is bit-identical within its matched pair. Their artifact hashes are bound in `reports/region-window-integration-v5/compatibility-binding.json`.

A separate real-character integration probe repeats the first source/seed pose for 60 keys, freezes objects and shifts grip targets by 1 cm along their box faces only on frames 12–47. One stage of five iterations changes the interior while preserving the outside seed root exactly. Outside local-rotation discrepancy is 5.29e-8 radians; original edit bounds pass and native forward-kinematics discrepancy is below 0.358 micrometres. The root lift ranges from zero to 6.701 mm within original limits. This is a synthetic code integration probe, not an action-quality result.

Earlier fixture attempts are retained: the five-frame window had no free spline controls; an off-face target was rejected before fitting; and a repeated static source with a near-zero rate ceiling suppressed the intended interior edit. The final integration probe disables that incompatible static rate guard. The actual moving study below retains its existing rate guard. No failed fixture or output was overwritten or promoted to success.

## Full-motion study in progress

`reports/region-windowed-surface-v1/method.py` runs the existing 180-frame box-transfer scene with the original source as edit reference and the completed windowed arm-guide motion as initialization. It selects `[48,133]`, six stages of 100 inner iterations and a 2,400-second fitting budget. It retains full sparse skin, per-vertex object inequalities, augmented hand-region constraints, witness refresh, both inferred foot supports, physical root coordinates, the 0.001 regional solver buffer, 0.05 mm object solver margin, 0.01 mm contact-gap solver margin and existing source-relative export-rate guard.

The driver records its exact process identity, captures implementation/input hashes, and runs decoded full geometry, joint-rate, support and actual Godot import audits after successful fitting. Raw failures are retained. At this commit the process is active; no final candidate, improvement or completed audit is claimed. The loss printed during fitting is not a quality decision.

The window intentionally preserves existing motion outside the selected keys, including any pre-existing defects there. Boundary interpolation, locked intervals and the complete exported clip must still be assessed. Results must distinguish failures inherited from locked motion from failures introduced or retained in the edited span. All fourteen release capabilities remain unapproved.
