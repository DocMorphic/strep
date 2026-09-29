# Full-distance pose checks in Studio

Studio now includes the [full-distance skin certificate](contact-pose-sphere-v1.md) in saved contact checks. It retains the earlier per-axis certificates, adds the exact spherical certificate to each report row, and explains the strongest lower bound. A conflict blocks **Fit saved checked pins** without changing the source, contact draft, timing, target or acceptance limits.

Check schema 3 freezes and verifies the spherical method alongside the original methods and raw/limb references. Older saved checks remain available for inspection but require a fresh check before fitting; both the editor and backend reject them politely. Historical schema 2 pose-report links remain accessible. This migration does not claim that a no-conflict result is feasible or realistic.

## Actual retained requests

Three new jobs exercised the real check supervisor with the original requests:

| Source | Pose conflicts | Result |
| --- | ---: | --- |
| Crawl, seed 11 | 13 | Needs authoring change; at least 55.63 cm versus 22 cm |
| Kick, seed 11 | 2 | Needs authoring change; at least 26.52 cm versus 22 cm |
| Wave, seed 11 | 0 | Checked; feasibility and quality still unproven |

All three retain zero endpoint timing conflicts. No correction was invoked and no new animation was created by these jobs. A previously successful schema 2 wave check is rejected with a refresh message; the new wave check passes request binding.

Source/snapshot, artifact and method hashes were verified after the workers exited. Direct handler calls verify three actual study entries and six report routes, and an offline DOM check verifies actual explanations, report links and fit eligibility. Fifty-four distinct focused Python tests pass, including a diagonal conflict the old per-axis preflight misses, preserved per-axis evidence, unchanged requests, old-schema rejection and missing-method refresh. Both Node contact timing/export-review tests pass. Four existing Torch deprecation warnings remain.

The local evidence is in ignored `reports/studio-pose-check-v2` and `reports/contact-jobs/studio-pose-check-v2-*`. The server was restarted after exact process/console-child identity checks under the worker lock; its new process and listening socket were verified. No HTTP or browser-rendering claim is made.

The preceding [body-constraint experiment](native-body-constraints-v1.md) completed and remains rejected despite passing engine playback. Neither that result nor these diagnostic checks approve animation quality. No further iteration-only retries are planned for the two proved incompatible requests; they remain explicit failures of the request/current edit-policy combination. The broader authoring and release requirements remain open.
