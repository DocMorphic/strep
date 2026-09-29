# Inner-solve budget and support review

The normalized-support grasp trial preserves sampled foot points but still fails hand-region contact and forearm clearance. All six stages stop at their 100-iteration limit, with large recorded projected gradients in mixed optimizer coordinates. This is evidence that the allotted inner solve did not establish stationarity, not proof that a longer solve will succeed or that the constraints are feasible.

## Controlled larger-budget trial

The regional fitter now accepts explicit inner budgets from 1 to 1,000 iterations. The default solver configuration remains 100 and the CLI default remains 40. Invalid values, including booleans and noninteger numbers, are rejected. No contact tolerance, rotation/root budget, geometry, loss, initialization or default algorithm changes.

`reports/region-support-inner300-v1/method.py` runs six stages of 300 iterations on the same five-key shared-pose fixture, with the same original source, grip initializer, normalized foot preservation, full sparse skin, region constraints, witness refresh, rate guard, margins and declared 600-second fitting budget. SciPy's function-evaluation allowance also scales with the iteration budget under the existing adapter rule. The implementation difference is the iteration validator; it does not change the accepted 100-iteration computation. Fitting and all source/candidate audits are retained. No full-duration rerun is started by this diagnostic.

## Review panel

Studio's existing diagnostics panel now includes source support-point sample failures, maximum drift in millimetres and coverage gaps, alongside motion timing. It distinguishes missing/invalid evidence and unverified preservation from a sampled pass. Placement edits still invalidate and hide these saved measurements. The explanation makes clear that point preservation does not establish a planted sole, balance, forces or naturalness.

Twenty-two focused iteration/optimizer/support tests and four desktop-build tests pass. The Node support formatter checks passing, failed, missing, malformed and incomplete-coverage summaries; the existing region-editor interaction checks pass. File-backed checks exercise the actual 75.634 mm failed and 4.973 mm passing support reports. The generated Studio matches its source, has 417 unique element IDs, and its module script parses. These are offline code/data checks; no browser rendering or human review was performed. Evidence is retained in `reports/support-review-panel-v1`.

## Completed result

| Exported measurement | 100 iterations per stage | 300 iterations per stage |
| --- | ---: | ---: |
| Runtime / objective evaluations | 131.703 s / 1,045 | 493.985 s / 3,934 |
| Failed hand-contact samples / 34 | 34 | 34 |
| Failed geometry samples / 17 | 17 | 17 |
| Minimum box clearance | -14.080265 mm | +1.043809 mm |
| Failed source-support samples / 34 | 0 | 0 |
| Maximum support drift | 4.973310 mm | 3.998919 mm |

The larger budget removes sampled skin-box intersection but misses the unchanged 2 mm clearance requirement. Both hands still fail overall distributed contact. At the first exported key, the left patch has 1.986934 mm minimum clearance and 10.016211° normal error, slightly outside its 2 mm/10° requirements. Its anchor is within 5 mm. The right anchor, patch clearance and normal meet their limits, but no qualifying distributed contact triangle is found. Passing some components does not pass a hand contact.

All six larger-budget stages still hit the iteration limit. The output repeats exactly, preserves original edit bounds and root XZ, and has root lift 9.858666 mm, minimum skin-floor gap 9.625186 mm and maximum original rotation edit 33.362431°. Source-support preservation is relative to inferred source targets, not proof of a fully planted sole or force support. The Godot audit reproduces all ten new source/candidate actor-frames and 77 joints with position discrepancy below 0.190 micrometres. This is one static development pose, not a usable action or release evidence.

`comparison.json` and `compare.py` under `reports/region-support-inner300-v1` bind the protocol/output/audit comparison. Only the requested iteration count, timestamp and the recorded iteration-validator implementation differ. Input data and all acceptance limits match. A separate native first-key diagnosis retains the eight vertices still below 2 mm clearance; the closest two are weighted entirely to `RightForeArm`, followed by left-palm and right-pinky points. The exported audit remains authoritative.

Studio collection `support-inner300-review-v1` preserves the failed source/candidate result with support and timing reports. Thirteen package hashes and twelve permitted routes pass offline verification; the Python snapshot is intentionally unserved. The new review panel exposes the passing support measurements without hiding hand/geometry failures. No live browser or human review was added.

The larger inner budget materially changes the candidate, so the earlier result cannot be treated as a pose-feasibility limit. However, more iterations have still not established convergence or complete contact. Next target the remaining forearm/palm/finger clearance and missing right-hand contact witnesses while preserving support and all original edit limits. Full-motion transitions and broader release validation remain open; all fourteen release capabilities are unapproved.

## Optional solver buffers

The regional fitter now exposes `--region-limit-margin-fraction` (default zero). A positive fraction tightens solver clearance, spacing and area requirements, and reduces solver contact-gap, local-radius, centroid, normal and anchor tolerances. The existing absolute contact-gap margin is applied first. Authored scene limits and independent audit acceptance remain unchanged, as do original edit bounds and inferred support tolerances. The protocol and objective record retain the requested fraction.

Forty focused region-objective, witness-refresh, initialization, support and job tests pass, including limit immutability and rejection of invalid or exhausted buffers. This verifies the implementation, not improved fitting quality. A paired continuation from the same best pose, with zero versus a small positive fraction, remains to be run and audited before making an effectiveness claim.
