# Reusable export-feedback correction

`scripts/export_feedback_repair.py` extracts the measured feedback search into a reusable function. It accepts a root-height problem and an export inspection callback, without hardcoded actions, case folders, clip durations or engine events. Studio integration remains pending; this module does not change the current checked-fit defaults.

The caller owns immutable source/reference data and every exported proposal. Before accepting a change, the search preserves each previously passing export group and serialized constraint row, rejects new body flags, and requires a strict improvement in the worst normalized export violation. When all exported groups already pass, serialized feasibility must strictly improve while exports remain passing. It can accept a partial numerical improvement without reporting a complete numerical pass or approving quality.

Incomplete, nonfinite or mismatched observation groups and serialized rows raise an error. An export exception propagates; it cannot be treated as a successful repair. Linear infeasibility reduces only optional search headroom. Measured discrepancy and the original acceptance limits remain unchanged. Every rejected export stays with the caller for inspection.

The inspection callback must perform original-source root/rotation checks, export/reload checks, full-mesh floor and contact measurements, point/global rates, held-pose preservation and body evaluation. This module is a selection/search component, not a substitute for those checks or an independently safe file importer.

## Verification

Twenty-nine focused tests pass across the new core and the prior measured feedback helpers. They cover moving a failure between contact phases, serialized-row regressions, body regressions, missing/nonfinite evidence, unchanged proposals, retained partial failures, actual linear-solver retries, rejected-export retention and export exceptions. Three existing SciPy warnings report that the solver passes its thread option through to HiGHS.

A read-only replay uses the retained wave-11, wave-22 and crawl-22 experiments. All original completion and input hashes were verified first. For every requested proposal, the extracted search reproduces each serialized native motion array byte for byte, matches recomputed serialized constraint measurements, and consumes that proposal's saved full export audit and body evaluation. Final coordinates, selected native files, export slacks, optional-margin choices and acceptance decisions match the measured study exactly. Crawling still rejects its first release-acceleration regression before selecting its second proposal.

The three rate-layout/measurement/headroom helper syntax trees are unchanged from the measured implementation. Evidence is retained in ignored `reports/export-feedback-core-v1/`. This replay creates no new animation exports or engine observations and makes no new perceptual-quality claim. The simultaneously running joint-restart study's existing Python/Godot methods remain unchanged.
