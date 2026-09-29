# Pose compatibility in saved contact checks

Studio now checks stationary contact requests against both endpoint travel bounds and the existing native body-change screen before enabling **Fit saved checked pins**. A proven conflict produces `needs_authoring_change`, a concrete explanation and a downloadable pose report. The source motion, contact draft, targets, intervals and acceptance limits remain unchanged.

The [pose bound](contact-feasibility-diagnosis-v1.md) uses the original raw and limb reference motions. It concerns displacement from each reference at the same frame, not character travel distance or action amplitude. Its rigid-skin assumptions and arithmetic reserve are recorded in the report. No detected conflict means only that this necessary test did not rule out the request; it does not establish feasible or realistic motion.

Schema 2 checks snapshot and hash-bind those references alongside the current native motion and GLB. Checked fitting validates the pose report, source references and implementation versions. Older checks remain preserved but require a fresh check before fitting. The existing Apply contact edit action retains its separate behavior.

## Verification

The real check supervisor processed three original requests without invoking the fitter:

| Source | Endpoint timing conflicts | Pose frame/reference conflicts | Result |
| --- | ---: | ---: | --- |
| Crawl, seed 11 | 0 | 13 | Needs authoring change |
| Wave, seed 11 | 0 | 0 | Checked; feasibility unproven |
| Kick, seed 11 | 0 | 0 | Checked; feasibility unproven |

The crawl explanation reports a minimum 53.65 cm joint displacement from the raw reference at frame 50 against the current 22 cm screen. This request cannot pass both current native checks under the stated assumptions. Its original failed fits remain available. Kick's unresolved fitting and support failures are not cleared by its check result.

All source, snapshot, artifact and implementation hashes were verified. No new animation was generated. The old saved wave check is rejected with an explicit refresh message. Thirty-eight focused Python tests and the offline contact timing/export-review Node tests pass. Direct handler calls verify three actual listings and six report routes; offline DOM checks verify the actual results' text, report links and fit eligibility. No HTTP, browser rendering, engine run or human review was performed for this integration.

Local evidence is retained under ignored `reports/studio-pose-check-v1` and `reports/contact-jobs/studio-pose-check-v1-*`. The Studio process was restarted after verifying its identity and acquiring the worker lock; its replacement process and listening socket were checked.

The full project goal remains active, with all fourteen release capabilities unapproved. Next work remains the coupled joint/support failure in kick and the broader scene, partner, rig and review requirements; this check prevents a known incompatible request from entering another expensive checked fit.
