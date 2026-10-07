# Actual exports after bounded ray recovery

Verified at 2026-10-07T01:20:36.869107+00:00.

The [ray method](ray-depth-restoration-v1.md) returns a separately verified first-phase candidate while preserving the rejected solver point. The same 44-choice motion-feasible anchor, complete cached model, source/contact/rate/static-reference/geometry limits and four requested fractions remain. No new derivative columns are generated.

| Fraction | Stored motion failures | Centered motion failures | Depth (mm) | Triangle records | Failed geometry conditions |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 17 | 15 | 4.72396543735 | 30372 | 1606 |
| 0.5 | 3 | 0 | 4.80228235442 | 30431 | 1608 |
| 0.25 | 4 | 0 | 4.84553903216 | 30429 | 1608 |
| 0.125 | 3 | 0 | 4.86686588228 | 30404 | 1608 |

The original anchor has depth 4.887984609217764 mm, 30398 triangle records and 1609 failed geometry conditions. **Every new geometry score improves**, using the original depth-first ranking. Contacts have zero failures and original references pass at every fraction. **Every motion/geometry gate still fails.** No candidate is retained, approved or substituted for the original assets.

The full step fails 15 centered rows and 17 stored rows, so storage correction alone is insufficient there. The half-step, quarter-step and eighth-step pass centered checks but have stored-motion failures. The half-step has the best original geometry score among those eligible fractions; its three stored failures motivate a [finite storage repair](ray-axis-storage-repair-v1.md). Centered pass does not guarantee a storage solution or collision pass.

The independent consumer reproduces complete cached source/model lineage and original array identities, every exported payload/world/native/centered count, and original rate/static/reference bounds. A separate consumer evaluates every saved initial solver point, all 21 finite ray probes and the selected complete native/surface populations, reproducing the strict affine-cap pass and original rejection without solver/producer/norm/reduction/guard imports. Geometry archive transport is verified; nonlinear predicates, continuous-time geometry, physics, whole-box dominance and phase optimality are not independently certified. This remains one generated cube-skin scene, not production-character, held-out action/rig or human-quality evidence. All fourteen release arrays remain empty.

Ignored immutable receipts: producer `edf815539a3c0fbf94769c2a87b17192f2a98ec6e8461cfb17dd77924a970471`; complete cache/export replay `23e4097301ad6e875eb39e13b3b935a797ca9896cf9dacce4ccc8d11e7b0ca05`; all-phase/ray audit `9c27bf18d518920d12af74cb7dd23481e5a5b147a9bd78e676a6f0f99d7e821b`.
