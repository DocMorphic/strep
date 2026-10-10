# Two more verified contact windows; complete lift still fails

V10 continues verified V8 motion and the separately verified V9 attempt schedule. It correctly skips V9's two rejected windows, then completes frames 105–107 and 108–110. Both new updates survive complete original-source checks and independent frozen replay. **V10 stage 2 is now the verified retained motion.** Twelve of 21 windows have been attempted and nine remain. Full physical/keyed contact passes are still **0/62**.

| Frame | Prior penetration | Verified penetration | Verified maximum palm-normal error |
| --- | --- | --- | --- |
|105|23.141 mm|20.862 mm|22.015°|
|106|23.634 mm|20.855 mm|22.273°|
|107|23.644 mm|21.160 mm|22.058°|
|108|23.438 mm|22.602 mm|21.632°|
|109|23.231 mm|22.525 mm|21.196°|
|110|23.080 mm|22.399 mm|21.042°|

The first window retains four steps in 246.282 seconds, with 57 measurements and 23 unretained nonlinear queries. The second retains two steps in 67.172 seconds, with thirteen measurements and no nonlinear queries. Both stop at `linear_start_unavailable`, which records a search failure rather than infeasibility. No poor take or failed proposal is removed.

Across the full interval, object and normal checks still fail at all 62 keys, point checks fail at 25 keys and reference-position checks at nine. Worst penetration remains 24.831 mm at frame 71, outside the new windows. The point-failure count falls from the preceding 27, but this does not turn any complete contact key into a pass. Original rig, object track, grip targets, references, edit limits, precision and retention rules remain unchanged.

## Independent reconstruction

Seven fresh/reaped NoTorch processes use 1,336 frozen source bindings. Local replay reconstructs 58 records / 174 native poses for stage 1 and fourteen records / 42 poses for stage 2. It checks eighteen total margin attempts, eleven correction proposals and 81 proposal archive files. Both complete 62-key intervals and exterior boundaries reconstruct all 22,720 original rows, with zero originally passing loss or protected regression. Earlier edited poses are preserved exactly, including the V8 edits that the separate V7 conic diagnostic did not contain.

The batch verifier reconstructs the fixed eight-state V8 native ancestry and the two rejected V9 attempts separately. It binds the independent V9 receipt and saved stage files, checks that neither rejected stage supplies motion, then verifies the new stages' selection, exact source flow, original-row comparisons and retained poses. Schedule continuation is exercised on real saved output, not only synthetic fixtures.

The native guard completes in 1,051.156 seconds, including 37.391 seconds of admission, with 1,282,523,136 bytes sampled peak process-tree RSS. All 996 resource observations independently replay. The complete independent audit guard finishes in 82.500 seconds, with 382,373,888 bytes sampled peak and eighty independently replayed observations. Full native/audit admission remains 2 GiB plus 600 MiB reserve; native stability is fifteen seconds and audit stability three. Existing RAM-floor, process-tree and runtime stops remain. These observations do not establish an absolute memory peak or justify lower estimates.

## Numerical failure diagnosis

The separately preserved 117–119 diagnostic stops on a complete affine subproblem. A predeclared follow-up contracts four captured zero-margin solver points by 1/16, 1/32, 1/64 and 1/128. Independent arithmetic reconstructs all sixteen candidates against 1,068 scalar rows, 2,265 norm vectors and 525 hard bounds. Fourteen pass the existing 1e-8 affine checks, but **all sixteen fail the fitter's unchanged strict tangent preservation**. Smaller steps alone cannot be presented as valid fitter inputs.

Each fails one row: `object:box:LeftHand:frame-117`. A subsequent predeclared, bounded scalar-plane projection adds a search-only 1e-10 margin to violated rows, with at most fifty projections. Each captured candidate needs one tiny correction. Separate arithmetic reconstructs all four corrected points; all original affine bounds, scalar/vector checks, strict tangent preservation and descent/worst-improvement conditions pass. This is a feasibility candidate, not the original solver's minimax or secondary solution, an optimality certificate or a native pose approval. No public solver default or tolerance changes.

The guarded native experiment measures all four corrected candidates at eight fixed backoff fractions. All 32 pass strict tangent preservation but fail both nonlinear and saved-representation retention; zero are eligible or retained. Independent NumPy FK/skin reconstruction checks 33 complete window records, including the baseline, and all 99 poses. It reproduces the original scalar/physical/saved rows, projected controls, scores and all rejection decisions. This separate V7-based terminal diagnostic cannot replace V10. No affine fallback is promoted.

The native guard completes in 57.547 seconds with 752,832,512 bytes sampled peak and 57 independently replayed resource observations. Independent reconstruction completes in 18.953 seconds with 165,138,432 bytes sampled peak and twenty replayed observations under unchanged full audit admission. A preparation error and a later verifier directory-variable shadowing error are preserved with their failed executions. The repaired verifier separates the directory variable from its FK temporary dictionary; numerical expressions and retention gates do not change.

Archived row differences identify `object:box:LeftHand:frame-117` as the default candidate's only nonlinear protected regression at all eight fractions. At full fraction its normalized slack decreases by 1.06522e-5; even the smallest fraction decreases by 6.49672e-10. Saved motion additionally exposes palm-normal regressions at some fractions. These are measured row differences, not derivative or curvature certificates. A search-only 1e-10 tangent margin does not suffice for nonlinear or serialized-motion preservation.

V10 batch result SHA-256: `c8eb2129dde6046048ecd6b7ebf281399ece65b5d99c58d719f2f534c0ead366`. Independent batch receipt: `f673baa0b5e7245b8df7c98f2d065a2009545ac6eead1f6f4810119949d016d8`. Latest retained stage result: `b838c0538b0ee98e4ff1a3caaa8c9ade6c438448d84bf96d7676d8d59085ca54`. Native correction result: `d5f910091847caeb11cf0346b80ca5b5e813cf68d1eae3b62b80b83f3430840c`; independent reconstruction: `038d512eb29b41a948d8f22604e07e62bbf6e758ec5da31389135fa3a1d24da7`. Raw motion, proposals, failed predecessors, frozen methods and traces remain ignored under `reports/box-lift-interval-batch-v10/`, `reports/conic-contraction-followup-v1/`, `reports/conic-plane-projection-v1/` and `reports/conic-plane-native-v1/`.

All fourteen release capabilities remain unapproved. No inference or training occurs in these studies. Between-key motion, full-clip realism, anatomy, dynamics, arbitrary rigs, scene/partner interactions generally, engine import and actual reviewer cleanup remain separate requirements. Continue remaining contact coverage and broad action, scene, partner, rig, editing, style, transition, engine and load-aware performance work under the same full-project goal.

The [following V11 two-key continuation](contact-interval-batch-v6.md) independently verifies a rejected attempt at 120–121. Thirteen windows are attempted and eight remain; V10 stage 2 is still the verified motion.
