# Complete indexed clearance observations

`native_indexed_clearance_observation.observe` builds exact clock and original-vertex lookups once. It retains the original scalar subtraction and dot-product arithmetic for every declared clearance row. Axes, positive margins, duplicate protections and row order stay unchanged. Every declared actor/time frame and point is validated, including unused points. Missing frames, invalid indices, nonfinite values and insufficient complete-population budgets reject the observation.

All 38 isolated public-source tests pass without skips. After the separate complete stored-export replay, the saved start and final candidates each reproduce all 33,490 gaps, margins and failed-row identities exactly. These fixture comparisons use shared original skinning primitives and check declared guide/component frames; they do not independently establish source provenance, full scene coverage or collision freedom.

| Saved export | Old projection lookup only (s) | New complete validation and projection (s) |
| --- | ---: | ---: |
| `start` | 1.477323 | 1.013725 |
| `storage-3-0` | 1.464613 | 0.987013 |

These are single local serial CPU measurements. Frame construction and skinning occur before either timed section; the old section measures projection alone, while the new section also validates the complete declared population. They are not end-to-end generation benchmarks. The API has no derivative or collision predicate, and neither export is approved for quality or release.

The separate reader reproduces all 257 export pairs and the original finite search decisions. An earlier interrupted reader is preserved as incomplete; its progress prints are not treated as a completed certificate. The final candidate still fails one original motion-rate row at the unchanged 64-choice limit. See [the complete study](staged-native-storage-results-v3.md).
