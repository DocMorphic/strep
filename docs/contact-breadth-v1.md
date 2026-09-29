# Cross-family contact fitting study

The [root-height correction](checked-root-feasibility-v1.md) repaired one nearly feasible get-up candidate. This study tests the complete pose-fitting and correction path on eight predeclared development clips: waving, crawling, kicking and jump/landing, at seeds 11 and 22. It is not a held-out release evaluation or a list of supported prompts.

The [frozen protocol](../benchmarks/contact-breadth-v1.json) selects all eight cases before fitting. Each source is an existing 120-frame body-corrected take. Waving and kicking receive a left-foot pin at frames 50–70; crawling receives a left-hand pin over the same interval; jump/landing receives a left-foot pin at frames 85–100. Every edit window is 10–109, with boundary keys held. The material vertex is the lowest point in the specified region at pin start. Its target is its source position at the interval midpoint, shifted 3 mm in X and clamped to at least 2 mm in Y. This deterministic request does not certify that the proposed support is natural or force-bearing.

## Preflight results

All eight requests pass the existing endpoint timing test with zero conflicts. This necessary check does not establish full pose feasibility. A separate horizontal-distance bound shows that seven original clips cannot satisfy the requested pin with root-height changes alone. Rotations or other allowed pose changes are necessary before the final small correction.

| Development case | Maximum horizontal pin error on original source | Root-only source pin impossible at 5 mm |
| --- | ---: | --- |
| Wave, seed 11 | 5.920 mm | Yes |
| Crawl, seed 11 | 518.099 mm | Yes |
| Kick, seed 11 | 290.574 mm | Yes |
| Jump/land, seed 11 | 6.138 mm | Yes |
| Wave, seed 22 | 3.394 mm | Not established by this bound |
| Crawl, seed 22 | 20.078 mm | Yes |
| Kick, seed 22 | 11.408 mm | Yes |
| Jump/land, seed 22 | 6.759 mm | Yes |

The large crawl/kick requests are retained. No difficult case, target or seed is replaced after seeing its measurements. If the timing check had rejected a case, it would have been reported without starting fitting or silently widening its window. A passing horizontal-distance bound is not proof that root-only fitting is feasible.

## Frozen execution

Each feasible timing request uses the same four-stage, 120-iteration-per-stage pose fitter as the retained get-up study: tolerance-scaled sampled pins, per-material-point and global rate guards, full-mesh per-time floor bounds and original source-relative edit budgets. Each resulting candidate is then passed to the bounded root-height correction. Failed proposals remain saved. The original source always defines the rate, floor and edit limits; a candidate never becomes a new budget reference.

All checks and bindings are completed before any pose fit. The suite freezes the protocol, source/current/raw/limb artifacts, asset hash, source metadata, Python implementation and release-reservation catalog. The reservation catalog is read only to prevent seed overlap; its cases are not tuned on. The current protocol is development evidence, regardless of future numerical success.

```powershell
.venv\Scripts\python.exe scripts/study_contact_breadth.py prepare `
  reports/contact-breadth-v1 --protocol benchmarks/contact-breadth-v1.json
.venv\Scripts\python.exe scripts/study_contact_breadth.py checks reports/contact-breadth-v1
.venv\Scripts\python.exe scripts/study_contact_breadth.py case `
  reports/contact-breadth-v1 --case-id wave-11
```

Run the other declared case IDs in protocol order. Existing outputs are preserved; these commands refuse to overwrite a previous preparation or case result. The local batch launcher under the ignored report directory performs the same ordered calls. Do not change imported source files while a batch worker is running.

Thirty-four focused workflow tests pass: nine new catalog/binding/rejection checks, eleven timing checks, seven immutable checked-job checks and seven root-feasibility checks. The new tests cover catalog coverage, reservation separation, deterministic binding without source mutation, changed-method rejection, invalid IDs/windows, and refusing to fit or overwrite a timing-rejected case. All eight actual source previews pass mesh/pose verification during timing checks.

At the time this protocol was published, the numerical batch was running. No final success fraction, new engine result or human rating is claimed. Numerical outputs, preserved failures, full exported contact/rate/floor audits, body/support flags, then engine checks will determine the next action. Studio defaults remain unchanged and all release capabilities remain unapproved.


First completed case: [wave seed 11](contact-breadth-wave-v1.md) passes all 81 pin samples, full-floor preservation and 284 engine pose observations, but retains a 7.5980e-7 m/s approach-speed excess. The fixed root repair rejects an infeasible extra-margin subproblem. A retained-data diagnosis separates that stronger search target from the original limits. Seven cases remain pending; the original batch continues unchanged.


Second completed case: [crawl seed 11](contact-breadth-crawl-v1.md) misses four pin samples despite passing point-rate ceilings. Its 5.007995 mm horizontal residual proves that root height alone cannot repair the retained pose to 5 mm. Support/pose regressions and a tiny raw floor difference remain; 284 engine observations pass. Six cases remain pending; the unchanged batch is now fitting kick seed 11.


Third completed case: [kick seed 11](contact-breadth-kick-v1.md) fails 55 of 81 pin samples, three point-rate ceilings and per-time floor preservation. Its 44.484085 mm horizontal pin error cannot be repaired by root height alone. All 284 engine observations pass; motion quality remains unapproved. Three cases are complete and five remain pending; the original batch continues with jump/landing.


Fourth completed case: [jump/landing seed 11](contact-breadth-jump-v1.md) passes all 61 pin samples, point/global rate limits, full-floor preservation and 284 engine observations after one accepted root correction. This is the first contact-screen pass among four completed cases, with four still pending. The original batch continues with wave seed 22. A separate [crawl preservation diagnostic](contact-breadth-crawl-v1.md#isolated-held-pose-restoration-diagnostic) removes locked-frame reconstruction drift and raw floor difference without changing its four pin failures; the frozen crawl outcome remains intact.


Fifth completed case: [wave seed 22](contact-breadth-wave-v1.md#seed-22-a-feasible-proxy-still-fails-the-exported-speed-limit) passes pins, floor, body regression checks and 284 engine observations, but retains a 6.6607e-8 m/s approach-speed excess over the original native-derived ceiling. The root proxy is feasible, so no repair step was attempted. The decoded source also exceeds that ceiling; both native-budget and decoded-source comparisons remain visible. Five cases are complete, only jump/landing seed 11 passes the full contact screen, and the original batch continues with crawl seed 22.


Sixth completed case: [crawl seed 22](contact-breadth-crawl-v1.md#seed-22-pins-pass-acceleration-checks-remain-open) passes pins, floor, body regression checks and 284 engine observations, while approach/global acceleration still exceed native-derived ceilings. The decoded source exceeds those ceilings too; its separate comparison does not alter fixed-study acceptance. The root repair rejects a locally constant violated constraint. Six original cases are complete, with one contact-screen pass; two remain pending.


Seventh completed case: [kick seed 22](contact-breadth-kick-v1.md#seed-22-pin-passes-hold-acceleration-and-foot-sliding-remain) passes pins, floor, original global-rate limits and 284 engine observations. Hold acceleration still exceeds its point-phase limit, and body evaluation adds a foot-sliding flag. The rejected root step preserves the fitted seed. Seven of eight original cases are complete, with one full contact-screen pass; the final jump/landing case remains pending.


## Completed frozen batch

All eight original cases and their engine checks are complete. The final [jump/landing seed 22](contact-breadth-jump-v1.md#seed-22-final-case-retains-pin-and-rate-failures) retains two foot-pin misses and four point-phase rate excesses. Both original workers exited successfully; original snapshots and failures remain immutable.

| Original case | Contact screen | Engine pose observations |
| --- | --- | ---: |
| Wave 11 | Fail | 284, pass |
| Crawl 11 | Fail | 284, pass |
| Kick 11 | Fail | 284, pass |
| Jump/landing 11 | Pass | 284, pass |
| Wave 22 | Fail | 284, pass |
| Crawl 22 | Fail | 284, pass |
| Kick 22 | Fail | 284, pass |
| Jump/landing 22 | Fail | 284, pass |

The aggregate is **one of eight contact-screen passes and 2,272 passing engine observations**. Alternative repair experiments are separate results, not replacements for these outcomes. The completed follow-up record binds every case, engine capture and independent recheck by hash. Future method changes must preserve historical verification against frozen snapshots, rather than rewriting old studies to match current code.
