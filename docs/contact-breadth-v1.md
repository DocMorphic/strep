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
