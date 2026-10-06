# Compact surface guidance for native motion edits

The optional compact guide represents each observed triangle pair with one separation condition instead of nine vertex-pair conditions. This reduces the size of proposal guidance while retaining all six triangle vertices. Existing jobs, verifiers and acceptance limits remain unchanged.

For a fixed normal `n`, the condition `min(A @ n) - max(B @ n) >= clearance` is equivalent in real arithmetic to requiring that clearance for all nine vertex pairs. Both extrema are reevaluated when vertices move. Floating-point evaluation can differ slightly because the arithmetic order differs.

## Query and model behavior

`scripts/native_compact_surface_rows.py` queries every declared time, actor pair and triangle population using the existing crossing and containment procedures. Object, plane and penetrating-vertex witnesses retain their original forms. An insufficient row budget rejects the complete build; it never returns a truncated subset. The report records compact and expanded populations separately.

`scripts/native_compact_surface_model.py` appends the compact guides after every original native norm, retaining its caps and scales. Optional decoded anchoring checks that these arrays remain identical. The model supports central differences and bounded one-sided differences at control limits.

The minimum/maximum gap is nonsmooth. Its local finite differences are not equivalent to linearizing nine separate inequalities. Every proposal still needs independent export, decoding, original native checks and complete geometry evaluation. This optional model is not connected to existing Studio jobs and does not approve motion or release readiness.

## Software validation

The 24 new focused tests compare compact and expanded gaps on generated fixtures, including moved vertices that become new extrema. They also check complete populations, preserved object and plane witnesses, insufficient budgets, changed inputs, invalid settings, original native norms and decoded anchoring.

The two new suites and four related surface/native suites pass 81 tests with zero skips. CI includes both new suites. These checks establish software behavior on generated fixtures.

## Complete retained scene study

The complete guide builds on all 1,673 original geometry times. It retains all 30,502 triangle records in their original order and uses 33,324 rows: 30,502 triangle support blocks and 2,822 other witnesses. The equivalent expanded population contains 277,340 rows, including 274,518 triangle-pair rows. All 3,346 actor/object queries remain. Both actors retain all 152 skin vertices and 228 original faces.

Every triangle block matches its original face identity and fixed axis. Direct evaluation of all nine vertex-pair gaps differs from the compact minimum by at most `4.440892098500626e-16 m`. The build takes approximately 70.4 seconds on the development machine. This resolves the complete-guide resource obstacle; it does not change the source scene's geometry failure.

One local proposal uses 30 full-clip controls with explicit editable boundaries, the original nine source-rate arrays, original contact limits and cumulative bounds against the original assembly. The model retains all 1,707 native times and the complete 665,730 pose/vertex-query population. Every one of 29,290 original native norms is protected in the affine solve; the 33,324 surface guides follow that prefix.

Clarabel returns `AlmostSolved` for the minimax phase and `InsufficientProgress` for the secondary minimum-norm phase. These statuses describe the affine proposal only. Independent serialization and decoding reject every tested fraction:

| Step fraction | Failed stored source rows | Failed unrounded source rows | Failed contact rows | Stored acceptance |
| --- | ---: | ---: | ---: | --- |
| 1 | 36 | 12 | 0 | Rejected |
| 0.5 | 15 | 0 | 0 | Rejected |
| 0.25 | 24 | 0 | 0 | Rejected |
| 0.125 | 6 | 0 | 0 | Rejected |

All four probes pass cumulative original-reference track and joint-displacement bounds. Full geometry is measured for the full-size probe at all original 1,673 times. It remains negative, with 30,478 triangle records and 1,594 failed samples. Fewer triangle records do not establish improvement: its maximum vertex depth rises to approximately 5.196622 mm from 5.191161 mm, against the unchanged 5 mm limit. Smaller native-rejected fractions have no new geometry assessment.

No candidate is selected. Original clips, contacts, external limits, source files and archived methods remain unchanged. These are generated-scene numerical observations; production motion quality, engine readback of a corrected candidate and human cleanup evaluation remain open.

## Independent replay and precision diagnosis

A separate consumer binds every original input, saved artifact and archived method to its receipt. It replays every placed vertex at all 1,673 geometry times, retains original topology and record order, and reduces every triangle gap through all nine scalar pairs using `math.fsum`. The maximum difference remains `4.440892098500626e-16 m`. Other witness gaps are also reconstructed. Every original native vector, cap and scale in the model prefix matches byte-for-byte; every probe is independently decoded and reclassified at all 1,707 native times. Geometry report populations and observation transport are verified; the geometry query itself and solver construction are not independently rerun.

Direct evaluation against the original uniform-time rate arrays classifies every stored failure as an original rate row. The three smaller unrounded proposals pass every native condition, including contacts. Stored-key precision therefore blocks those proposals, while the full-size unrounded proposal also has twelve source failures. Zero-control exports pass the original native conditions. All raw results remain separate and rejected; no external cap is increased.

The next restoration must preserve those original caps and contacts in the stored asset, then independently assess complete geometry and cumulative bounds. A passing unrounded curve or affine solver status cannot approve the exported motion.

| Local receipt | SHA256 |
| --- | --- |
| `reports/compact-surface-full-clock-v1/result.json` | `34edaf82ebf51c9f6b600c96d17d193e734410b663cdbade31476bd858c7fd0b` |
| `reports/compact-surface-model-probe-v1/result.json` | `a2d86ae334e2a49ab93d78a647fd523e75c74e3758ea8aaa7a14575a7114515b` |
| `reports/compact-surface-independent-v1/result.json` | `8b699a39c4e5bb62dbbb953006344bf40542cb2b2465c1fafe1976a32bf969cb` |
| `reports/compact-surface-precision-v1/result.json` | `8b886c5a59371c70c6a14a206c68b22d05a5411a162c8ecfc25ec5469d694abc` |

All four CPU drivers exit zero and release the worker lock. Generated outputs stay outside the public repository. No new engine run, rendering/GPU, model sampling/training or human review is claimed. All fourteen release evidence arrays remain empty, and the full-project goal remains active.
