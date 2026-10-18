# Required repairs in nonlinear retention

Development component, 2026-10-18. The full saved clock found a previously
passing A-to-B condition lost at frame 66. Protecting only the passing rows
of a diagnostic warm seed cannot restore a source condition already lost by
that seed. Likewise, a lower collision peak cannot waive a failed motion cap.

`SceneStepGuard` now accepts an optional complete Boolean `required_rows`
mask. Each explicitly required row must pass its original zero boundary
before a step can be retained, even if that row fails at initialization.
Every other previously passing row remains protected, and the worst search
violation must still strictly decrease inside the original control balls.
Rejected steps cannot change the stored state or rebase any edit permission.

The mask is owned, cannot be shortened and remains required across steps.
The caller must bind it to the original conditions. A default call without
the mask preserves the old report contract, allowing archived diagnostics
to be replayed without adding new report fields.

All **181 focused source cases pass locally**, including the previous 174.
The seven new cases cover required repairs, tiny remaining violations,
interaction with other passing contacts, owned masks, retained requirements,
invalid masks and the unchanged default report. This is a numeric retention
rule, not source binding, geometry coverage, motion approval or a feasibility
certificate. Evidence: `reports/required-scene-rows-tests-v1`.

The same **181 cases pass on hosted Windows and Ubuntu** at
`0e390dfbb099e044848cb5db2d899ba92841c4c9`.

The [full-clock trial](full-clock-scene-step-v1.md) requires original passing
partner conditions, every floor screen and all original motion ceilings.
It retains every per-frame partner/floor row, original-relative joint/root
permissions and actual paired point-contact cones. Saved observations are not
substituted for the raw editor's linearization. All six tested fractions are
rejected at concrete mandatory conditions; no clip, capability or release is
approved.
