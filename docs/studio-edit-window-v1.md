# Selecting contact-edit ranges in Studio

The **Fit hand contacts** panel now offers an optional first/last editable frame selection. Leaving it off retains the existing whole-clip request. Turning it on saves the selection with the contact draft and sends it through the immutable job request to the regional fitter's existing `edit_window` option. Resetting, loading a different scene and running a job disable the appropriate controls; source revisions continue to isolate saved drafts.

The client checks integer bounds and coverage of every selected contact interval. The backend independently checks bounds, available localized spline controls and contact coverage before creating a job folder. It repeats the selection check before solver dispatch. A range too narrow for any free rotation controls is rejected; the system does not widen it silently. Preserving existing motion can preserve existing collisions as well.

After a windowed fit, the job runs the independent decoded joint/full-skin preservation audit, records outside and boundary regressions, computes remaining geometry by range, and attaches both reports to the review. Audit failure leaves the job failed. A mismatched protocol selection or result identity is rejected. Successful job completion still does not approve animation quality.

## Validation

- Twenty-five Python tests pass across request validation, immutable snapshots, solver dispatch and desktop build preservation. Legacy requests omit the solver option; limited requests forward the exact endpoints. Dispatch tests intercept the solver explicitly and do not claim new numerical output.
- Two Node checks pass, including the existing contact editor with range selection, local rejection, submission, saved draft recovery and disabled controls, plus the range-diagnostics renderer.
- The actual post-fit helper was exercised with the completed windowed arm-guide clip and a real 120 Hz full-skin audit. Its older guide protocol requires an explicit seed adapter at the auditor boundary; the exact hash-bound starting seed was supplied. Outside preservation passes, while 478 contact and 379 geometry failures remain. A different requested window is rejected before output. This validates post-fit integration, not a new Studio solve.
- The local Studio server was restarted to load the backend changes after confirming it had no child jobs. Its replacement bound port 8768, and the separate long-running contact solver remained live. No HTTP or live browser validation was performed.

Exact post-fit verification code and output are retained under `reports/studio-edit-window-v1`. The full `region-windowed-surface-v1` numerical study subsequently completed; its [measured failures and boundary changes](windowed-surface-fit-v1.md) are retained. The subsequent [real Studio workflow](studio-window-flow-v1.md) now verifies complete backend execution and engine import while retaining contact/geometry failures. Browser interaction remains unverified. All fourteen release capabilities remain unapproved.
