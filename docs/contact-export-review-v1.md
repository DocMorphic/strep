# Readable contact-export results in Studio

Checked contact candidates now show an expandable review in the contact editor. Failed or unavailable checks open automatically. Each row identifies the contact/phase, measured value, applicable limit and any excess. The full audit remains linked.

The panel covers the exported stationary-pin samples, contact-point speed/acceleration, added floor penetration and motion outside the edit window. It does not approve whole-body joint rates, action correctness, force support or naturalness. Existing body-quality flags remain part of the full clip review.

Positive excesses retain enough precision to remain visible, including very small rate errors and added floor depth. Missing, negative, nonfinite or incomplete measurements are unavailable rather than passing. Pin sample misses cannot be hidden by a passing maximum. Outside-window measurements exceeding the existing 1e-6 position/basis limits cannot be hidden by a contradictory stored pass flag.

Floor results distinguish added penetration from total penetration. An edit can preserve the source's floor depth while still retaining an existing intersection; the display exposes both. Clip changes clear the previous result, and contact names are inserted as text rather than interpreted as HTML.

## Validation

The new offline DOM checks pass for numeric limits, tiny failures, missing evidence, inherited penetration, contradictory evidence, safe metadata text, stale-result clearing and the full-audit link. Existing timing/check/fit workflow tests also pass, including saved-check revision binding and draft preservation. Four desktop-build tests confirm that the generated page matches its editable sources and retains the existing authoring controls and unique IDs.

The renderer was additionally checked against eleven retained reports. Its contact-screen interpretation matches the original eight-case results and the three successful export-feedback alternatives:

| Report | Failed displayed checks |
| --- | ---: |
| Wave 11 / 22 | 1 / 1 |
| Crawl 11 / 22 | 2 / 1 |
| Kick 11 / 22 | 5 / 1 |
| Jump/landing 11 / 22 | 0 / 5 |
| Three export-feedback alternatives | 0 each |

Every report had all displayed measurements available. Failure counts refer to the listed point-contact/floor/preservation checks, not the complete release matrix. Renderer and fixture hashes are retained in `reports/contact-export-review-v1/verification.json`.

This change affects JavaScript, HTML and CSS only. The running joint-restart study's Python/Godot methods were rechecked and remain unchanged. No browser, HTTP, visual-layout, human-quality or new engine-playback verification is claimed for this interface change.
