# Matched larger edit range: improvement without acceptance

The completed surface solve compares the original editable range **48–133** with **23–133**, using the same raw motion, same arm-guide initializer and identical implementation/settings. The saved protocol comparison has exactly two differences: timestamp and edit window. The larger range allows earlier box intersections to be addressed; it does not change the contact targets or tolerances.

| Exported measurement | Initializer | Range 48–133 | Range 23–133 |
| --- | ---: | ---: | ---: |
| Contact failures / 490 | 478 | 381 | 372 |
| Geometry failures / 717 | 379 | 376 | 337 |
| Geometry failures before frame 48 / 192 | 53 | 53 | 32 |
| Box penetration before frame 48 | 28.575 mm | 28.575 mm | 4.477 mm |
| Geometry failures in frames 48–133 / 341 | 326 | 323 | 305 |
| Box penetration in frames 48–133 | 26.768 mm | 22.761 mm | 22.815 mm |
| Peak joint speed | 1.283170 m/s | 1.283171 m/s | 1.358359 m/s |
| Peak joint acceleration | 37.521536 m/s² | 38.183553 m/s² | 37.913644 m/s² |

Phase boundaries in this table remain 48 and 133 for a comparable measurement. The larger-window candidate stays inside the original raw-source edit budgets: maximum rotation edit 35.989314°, root lift 0–7.032335 mm. Its whole-clip speed/acceleration peaks are below the raw source's peaks, but both exceed the initializer's; neither comparison proves smooth or believable motion. All six optimizer stages reached the 100-iteration limit, with 672 function evaluations in 1833.703 seconds. Convergence is not claimed.

Inferred foot-support preservation still fails on **66/1398** assessed samples, maximum error **5.134362 mm** against the existing 5 mm threshold. Thirty-six vertex-identity gaps remain unassessed. These are selected support-point measurements, not force, balance or planted-sole certification.

The outside-window audit exposes a separate defect: 270 fully locked samples preserve skin position within 0.129 µm, but six adjoining interpolation samples change by as much as **2.015327 mm**. Native outside keys remain preserved; editable endpoint root heights alter the adjoining exported LINEAR segments. This prevents an outside-motion preservation claim and motivates explicitly holding the shared endpoint keys.

Both source and candidate pass all **360 Godot actor-frame checks**, with maximum position discrepancy below 0.384 µm. The retained review package `scene-region-jobs/expanded-window-surface-review-v1` has fifteen verified hashes and fourteen allowed data/download routes; Python source is not served. It includes contact, geometry, temporal, support and window failures. Engine fidelity does not approve the motion.

Exact fit, matched protocols, immutable implementation snapshots, audits, finishing method and comparison are retained locally under `reports/region-expanded-window-surface-v1`. No browser review or human quality assessment was performed. All fourteen project release capabilities remain unapproved. This result improves early collision coverage but does not solve the moving lift.
