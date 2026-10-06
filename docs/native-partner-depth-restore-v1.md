# Depth-first partner feasibility restoration

Depth-first restoration produces a meaningful motion step while preserving the original native constraints in the proposal model. The full-size export reduces measured penetration but fails original native/contact and geometry checks. A smaller step needs bounded Float32 storage repair before it can be considered as an unapproved correction anchor. No solver result grants asset acceptance.

## Ordered proposal objectives

`scripts/native_partner_depth_restore.py` reads the original depth limit through the source-bound geometry policy and retains every original native norm, cap and scale as hard conditions. It uses separate nonnegative penalties for existing partner depth-floor deficits and complete surface excess. First it minimizes the worst depth-floor deficit. It then locks that numerical optimum within `1e-9` and minimizes complete surface excess. A third phase locks both numerical optima and minimizes normalized control magnitude.

Every existing partner witness remains in the depth objective. All original surface conditions remain represented through certified reduction, including all nine scalar conditions per triangle block and every singleton witness. These are local fixed-normal/barycentric guides. Intermediate depth violations remain explicit; the original full geometry policy and asset acceptance never change.

All phases retain the pinned Clarabel 0.11.1 settings, one solver thread, 100 iterations, a 30 second limit per phase and `1e-9` feasibility/gap tolerances. A failed later phase retains the last successful point. Each returned step is reevaluated against the original native norms and complete affine population; decoded checks remain authoritative.

## Retained complete model and numerical repair

The experiment reuses the byte-exact independently replayed thirty-control model, nine source-rate arrays, original reference/contacts, source-scale storage and seven fixed one-neighbour component corrections. All 1,707 native times, 1,673 geometry times, 29,290 original native norms, 277,385 scalar surface conditions, 118,367 equivalent encoded surface rows and 2,840 partner depth witnesses remain.

The first implementation completed all three solve phases but returned no proposal because a small trust-edge overshoot lay outside the certified proof box. Its result and archived implementation remain immutable. After that worker exited, the implementation was corrected to project tolerated solver overshoot into the original trust box before converting to the authoring box. The corrected study is separate, and a regression test exercises this edge. No trust region or asset limit is widened.

In the corrected study, the depth phase returns `Solved` after 41 iterations; surface and minimum-norm phases also return `Solved`. Trust projection changes a component by approximately `1.84e-13`; maximum final control step is 0.02. The depth-phase optimum is approximately 0.0294603102, and reevaluated projected depth deficit is approximately 0.0294604615. Their difference exceeds the nominal phase-lock tolerance, so numerical solver locks are not exact certificates. Predicted native excess is approximately `-2.05e-10`. The complete surface excess is approximately 2.33625848.

## Exported fractions

| Fraction | Stored native failures | Unrounded native failures | Contact failures | Full geometry assessed |
| ---: | ---: | ---: | ---: | --- |
| 1 | 7 | 13 | 1 | Yes, failed |
| 0.5 | 18 | 0 | 0 | No, before storage repair |
| 0.25 | 12 | 0 | 0 | No |
| 0.125 | 12 | 0 | 0 | No |

Every fraction passes cumulative original-reference displacement and selected rotation bounds. The full-size geometry audit reports maximum vertex depth approximately 5.146019 mm against 5 mm, 30,425 triangle records, 84 contained vertices and 1,595 failed samples. The starting anchor had approximately 5.195942 mm depth, 30,505 triangle records, 102 contained vertices and 1,594 failed samples. Reduced depth does not establish complete geometry success. The full-size motion's native/contact failures exclude it from acceptance.

The smaller steps pass every unrounded native/contact condition but fail after storage. The half-size step therefore receives a bounded one-neighbour quaternion component search at fixed continuous controls, using the existing source-bound policy and original caps/scales. This search addresses measured storage failures; it does not alter the motion objective or geometry limits.

The half-size search uses an eight-stage/thirty-two-probe-per-stage budget. Ten neighbour probes clear all eighteen initial stored native failures; contacts pass throughout. The final list contains twelve absolute one-neighbour component corrections. All eleven raw probes, twenty-two actor exports and two appended original-library variants are retained. The repaired clip passes every original native/contact condition and cumulative reference bound. Maximum original-reference joint displacement is approximately 0.587 mm for A and 0.584 mm for B; selected-track change is below 0.068 degrees, against 30 mm and 5 degree limits.

Complete repaired geometry reports depth approximately 5.171110 mm against 5 mm, 30,483 triangle records, 93 contained vertices and 1,595 failed samples. Its worst depth improves from the starting anchor, while the additional failed sample remains visible. It is retained only as an unapproved native-feasible correction anchor for a fresh local model. The unrepaired half-size clip has no full geometry audit, so the effect of component repairs on full geometry is not isolated. Appended variants preserve the original five animations and binary prefix, with identical decoded repaired motion at all native times.

## Validation and remaining scope

Fifteen new focused cases cover objective ordering, zero native penalty coefficients, hard native limits, complete surfaces, later-phase fallback, malformed models and original trust projection. Existing producers and Studio jobs remain unchanged. Raw exports, rejected studies, derivatives, drivers and method archives stay local and excluded from Git.

Before recentering, a smaller step must pass all stored native/contact/reference checks and retain a measured complete geometry improvement. Rebuild the complete local guidance at any such anchor; do not reuse stale witnesses or derivatives. Only unchanged full decoded geometry acceptance can approve an asset. The broad release goal remains open, including production humanoids, diverse actions/rigs/objects/partners, engine validation and developer/animator cleanup evidence. No new engine, rendering/GPU, physics, anatomy, model sampling/training or human review is claimed. All fourteen release evidence arrays remain empty.


All 100 focused tests pass with zero skips. Parsed CI adds only the new suite; hosted CI is not asserted green. The complete-model consumer binds the prior full thirty-column derivative replay by exact arrays and unchanged methods, reevaluates every proposed affine row, and replays every raw payload/world/native/reference condition. A separate consumer imports neither search nor storage wrapper and reconstructs all eleven probes directly with scalar `nextafter`. Both appended variants preserve the original animation library/binary prefix and complete repaired worlds. Full geometry clocks/limits/observation transport verify; predicates are not independently recomputed. All workers exit zero with locks free. Original inputs and archived implementations remain unchanged; the new proposal helper changes only between the retained rejected and corrected versions.

The source-bound next-model anchor is `reports/partner-depth-restoration-anchor-v1.json`; it explicitly has `asset_accepted: false` and requires fresh complete witnesses and derivatives.

| Local receipt | SHA256 |
| --- | --- |
| `reports/partner-depth-restore-probe-v1/result.json` | `cd5ad32eb83dec67b9e49999c8c5b0997277e3e05ea5b89108299b5419d8ec3c` |
| `reports/partner-depth-restore-probe-v2/result.json` | `ed35a0822d8acb214e124056c0313a7b27eeff17b2bfa6c14b3b1b9f3bb38116` |
| `reports/partner-depth-restore-independent-v2/result.json` | `de16cd1a9a01367833f2de8738f98793dc314d5e6e1546f05c3f6164ce634e82` |
| `reports/partner-depth-restore-storage-v1/result.json` | `0c9241618e0f1cebe15f3826d82483b06b25bf2b9df1b483ae7a23be552241f1` |
| `reports/partner-depth-restore-storage-independent-v1/result.json` | `e3bda9027236c3c29064f97965d10ac6f981a6d9bebadf3f1cbc0fadc54a3c50` |
| `reports/partner-depth-restoration-anchor-v1.json` | `14d494622f3c13848e92978bf7b269320996ecff5e9252db5811227fd5411ba9` |
