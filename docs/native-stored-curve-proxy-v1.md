# Stored-clip-centered proposal curves and recentered depth restoration

The retained eighth-step clip passes the original sampled native/contact and cumulative reference bounds, but fails complete geometry. Its smooth proposal curve now matches the exported anchor; no correction has yet been solved with this new proxy.

## Recentered fixture results

This CPU study uses the existing generated cube-skin pair fixture, original source/reference, thirty controls, twelve fixed absolute one-neighbor rotation-storage corrections, all nine rate arrays and unchanged limits. It rebuilds all witnesses and derivatives at the previous repaired half-step anchor. It retains 277193 scalar surface conditions through 118273 equivalent rows and 158920 independently verified exact dominance implications, alongside 29290 native norms and 2846 depth witnesses. All thirty scalar derivative columns replay with maximum difference 4.440892098500626e-13; the original native Jacobian replays exactly.

The primary depth phase solves in 38 iterations, the surface phase solves, and the minimum-norm phase is AlmostSolved. The final step is projected to the original 0.02 trust box (maximum correction about 1.38e-11). Numerical priority excess is measured, not an exact lexicographic certificate.

| Step fraction | Stored native failures | Legacy smooth failures | Contact failures | Complete geometry depth |
| --- | ---: | ---: | ---: | ---: |
| 1 | 9 | 15 | 0 | 5.120550 mm, failed |
| 0.5 | 9 | 12 | 0 | Not assessed |
| 0.25 | 6 | 6 | 0 | Not assessed |
| 0.125 | 0 | 6 | 0 | 5.164935 mm, failed |

Every fraction passes cumulative original-reference bounds. The eighth step has 30471 triangle records, 93 contained vertices and 1596 failed geometry samples, versus previous-anchor depth 5.171110 mm and 1595 failed samples. Fewer records or lower depth do not waive the unchanged 5 mm limit or crossing checks. All raw fractions, including failures, remain immutable locally. The eighth clip is selected only as an unapproved next-model anchor.

## Proposal implementation

`scripts/native_stored_curve_proxy.py` requires a verified storage-adjusted editor, explicit anchor controls and every edited actor's actual exported clip. It binds original source bytes, anchor bytes, edit request, tracks, controls, weights, boxes, storage policy and corrections. Changes require a fresh proxy.

For each permitted track it freezes the complete offset between actual stored keys and the original continuous keys at the anchor, including rounding and explicit corrections. Protected-key offsets must be zero. At the anchor the smooth keys equal the stored keys; nearby proposals retain the fixed offsets. Quantized values, exports, audits and library appends delegate to the existing editor, preserving its acceptance path and byte-identical exports.

The first full-anchor probe, after small fixtures passed, failed on 33 of 573552 pose entries with maximum difference 4.51594947e-8 at the original 2e-12 pose tolerance. That terminal failure and its implementation are retained. After its worker exited, only the new proxy's smooth world sampling was changed to use the existing native scalar sampler at every time. Scalar endpoint comparisons near Float32 clocks differed from the older vector helper's comparisons; existing helpers and previous studies were not rewritten.

A separate corrected probe matches all 1707 native sample worlds within 1.3322676295501878e-15. Decoded and centered native failure counts are both zero; the legacy smooth curve has six failures. The normalized residual difference is about 3.21417870097207e-9 from floating-point propagation, not byte equality. Original native vectors, caps and scales evaluated on the same decoded worlds remain byte-identical. Both exported clips remain byte-identical. A consumer that does not import the new proxy independently reconstructs all 2320 offset components, complete worlds and residuals using the original scalar sampler and verifies the recorded bytes.

## Validation and limits

Sixteen new cases and forty-one existing storage-repair/search cases pass: 57 tests, zero skips. They cover actual exported anchors, Float32 endpoint neighborhoods, fixed offsets, protected keys, identical exports/library append and rejection of malformed or stale contracts. CI adds only `tests/test_native_stored_curve_proxy.py`.

The full recentered model was rebuilt before this proxy existed. Anchor alignment alone does not validate stored-centered derivatives away from the anchor or another solve. Next rebuild the complete model with the new proxy and retain every measured failure under unchanged decoded acceptance. Geometry archives/limits/clocks were replayed, but geometry predicates were not independently recomputed. These are generated-fixture software and numerical results, without new engine, rendered/GPU, production anatomy, physics, model sampling/training, developer/animator review or broad action coverage. All fourteen release evidence arrays remain empty.

## Immutable local receipt hashes

Generated studies stay under ignored `reports/`; only code, tests and concise evidence are public. SHA256:

- partner-depth-recenter-probe-v1: `30c060205c6130a08eed2561493b4d742a1a91e81308d955b1dc89954596927e`
- partner-depth-recenter-independent-v1: `f84dbf7877d7f08e3445e9799c0c37e7be12b5aba81fef5d2498c632bd36c46a`
- stored-curve-proxy-probe-v2: `25ab804ab572e021124b90a6619023fd7e60b000bab4be4d91666eb668f3b318`
- stored-curve-proxy-independent-v2: `337129357541a5a3c4189989089f34f6ab0355f419e3fd74e2bdb4283e76dd0c`
- retained-proxy-failure: `5ade83de8ab63c5f7af7ea4902c08b8cc9064ce4bb4256189125ffabee5ba26e`
- unapproved-anchor: `58425e677617459b39a57353934fa3fe8af8a027b58702a4b2bac2e4d2cb0ee6`
