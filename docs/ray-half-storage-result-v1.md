# Actual half-step storage repair

Verified at 2026-10-07T01:41:25.799329+00:00.

The [typed storage repair](ray-axis-storage-repair-v1.md) completed against the exact pinned [ray comparison](ray-depth-comparison-v1.md). All 90 continuous controls remain fixed at the centered-passing half-step; original contacts, rate caps, Float64 static references, edit window and 64 absolute one-ULP component limit remain unchanged.

| Measurement | Raw half-step | Repaired stored clip |
| --- | ---: | ---: |
| Stored native/source failures | 3 | 0 |
| Contact failures | 0 | 0 |
| Original reference bounds | Pass | Pass |
| Absolute component choices | 44 | 45 |
| Maximum measured depth (mm) | 4.802282354420261 | 4.802282354420261 |
| Non-disjoint triangle records | 30431 | 30431 |
| Failed geometry conditions | 1608 | 1608 |

**Measured motion checks pass; geometry fails.** The original anchor depth was 4.887984609217764 mm. The repaired candidate improves the original depth-first ranking while preserving the raw half-step geometry score, but has more triangle records than that anchor. Neither successful export nor depth below 5 mm clears the original non-disjoint-surface gate.

One stage plans 144 original options. The ninth tested neighbor clears the remaining errors; ten exports include the start and all nine probes. A separate consumer checks the entire planned option population, interleaving prefix, every actual merit/transition and stable eligible best selection. This is the best eligible tested prefix, not an exhaustive search of the full family or a matched-compute timing study.

Another independent consumer reconstructs every probe from the legitimate original export context and manual absolute choices. It reproduces every payload, decoded native world, original rate/static/reference bound and final motion/contact result. For both actors, separate variants retain the seven original clips and append animation index 7; original animation metadata, binary prefixes, scene data and native worlds are exact. Original assets stay selected and both variants remain unapproved.

Coverage is 1707 native samples and 1673 geometry times in one generated cube-skin two-character scene. Geometry archive transport is verified; predicates, continuous-time collision freedom, physical plausibility, engine import, production anatomy and human cleanup are not independently certified. The prior 70 source/protocol tests pass; completed studies were not rerun for publication. All fourteen release arrays remain empty. The next experiment should first identify remaining collision witnesses and whether the current editable joints can influence them.

Ignored immutable result SHA256 `c648e3993190dc5f5e5de034dc8ade0d34178f74a800d82a574aa916d64f8868`; every-probe replay `a48a4b834cca027c60a7ab1b1f293a155c7bc96eebc5b7ab24530250f6e42fe4`; full option/selection audit `cb6f9e7b9574a711d8596bb6d33f39a605eabdc1650318d52f050e80f5b0c703`.
