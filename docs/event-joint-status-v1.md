# Preserve joint-edit status through marker changes

A marker-only edit leaves animation geometry unchanged. Studio already inherited contact-correction status, but a rejected joint-target candidate could lose its status after editing gameplay markers.

Event preparation now retains a hash-bound joint audit for the selected candidate. It checks the audit's GLB hash and numerical decision against the selected result, and preserves the original job identity across repeated marker edits. Selecting the original input does not inherit the candidate's rejection. The worker checks the copied audit and motion again before writing the output.

The result, version label and job selector retain the joint status. An inherited-audit download remains available, and the ZIP contains the decision in request.json alongside the unchanged audit and motion. Numerical-screen success remains distinct from action or animator approval.

Validation: 18 Python tests passed, including existing periodic/contact-marker regressions, two successive marker edits of a real rejected joint candidate, mismatched evidence rejection and snapshot mutation detection. Seven JavaScript selection-policy cases passed. The desktop was rebuilt and its reproducibility check passed again after the final job-label change.

The idle local Studio server was restarted to load the backend change; research workers were preserved. A real API job, `20260928-055150-f46299fa`, retained the rejection and exact motion/audit bytes. Its downloaded ZIP and linked audit matched the saved hashes. The inspection marker is explicitly unreviewed. Browser verification showed `Authored markers · Failed checks` and the inherited-audit link. Evidence is in `reports/event-joint-status-v1`.

This inheritance applies only to marker edits of unchanged joint-candidate geometry. Pose, timing and regenerated-motion edits need their own validation; this does not approve their descendants or replace an animator review.
