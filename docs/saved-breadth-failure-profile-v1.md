# Saved breadth failure profile

`scripts/saved_breadth_failure_profile.py` identifies recurring diagnostic failures across a complete saved action study. It joins every declared case, actor and seed against caller-pinned coverage metadata, checks each stored screen against its original numerical threshold and preserves missing exports, missing measurements and context-dependent N/A entries. It runs no model, pose, geometry or engine. Action names and families are caller data, not a supported-action whitelist.

```powershell
python scripts/saved_breadth_failure_profile.py PROTOCOL.json COVERAGE.json EXECUTION_FREEZE.json FRESH_OUTPUT --protocol-sha256 PROTOCOL_SHA256 --coverage-sha256 COVERAGE_SHA256 --execution-sha256 EXECUTION_SHA256
```

All three explicit source hashes are required. The protocol and execution freeze supply the original joint/mesh floor and predicted-support-speed thresholds; the tool does not choose new limits. Missing/duplicate/unknown actor-seed rows, changed family/context fields, incompatible screen values and unsupported review/quality flags reject. Context-dependent screens must stay null, even when some incidental joint measurements exist. Every case remains in the output; recurrence means all of that case's declared eligible actor/seed rows fail the stored mesh-floor screen, without an inferred success for excluded contexts.

The complete-data budgets are 16 MiB per JSON input, 1,024 cases and 32,768 actor/seed rows. Over-budget inputs reject instead of returning a subset. A fresh output contains exact input snapshots and a source-bound result. Inputs and the implementation are rechecked before completion; mutation during snapshotting retains partial output without a complete result. The artifact is a saved-metadata reduction, not fresh verification of the original exports or newly computed contact measurements. It expects unreviewed development coverage; actual human evidence belongs in the separate role-validated review importers.

## Current full-population result

The pinned [raw breadth development baseline](breadth-baseline-v2.md) contains **all 390 actor clips from 72 cases and 12 families**, including both independently generated actors for six partner cases. Five fixed seeds are retained for every case. All source rows report exports available. The newly reduced denominators and original thresholds reproduce the saved coverage:

| Stored diagnostic | Applicable clips | Pass | Fail | Context N/A |
| --- | ---: | ---: | ---: | ---: |
| Mesh floor, at most 10 mm | 200 | 61 | 139 | 190 |
| Joint floor, at most 10 mm | 200 | 153 | 47 | 190 |
| Predicted-support speed p95, at most .15 m/s | 200 | 188 | 12 | 190 |

There are no missing diagnostic measurements among the applicable rows. The other 190 clips need their declared scene/partner/physical context; N/A is not a pass. These are the existing diagnostic screens, not frozen release acceptance or the complete official model benchmark. A percentile speed pass can hide a brief slip, and floor clearance does not establish balance, semantic correctness, transitions or natural movement.

**Eleven actions fail the mesh-floor screen in all five saved seeds:**

| Family | Frozen case ID |
| --- | --- |
| locomotion | `locomotion-lateral-cross-step` |
| parkour | `parkour-broad-jump-stick` |
| parkour | `parkour-running-leap` |
| ground/recovery | `ground_and_recovery-kneel-rise` |
| ground/recovery | `ground_and_recovery-belly-crawl` |
| ground/recovery | `ground_and_recovery-side-roll-recover` |
| ground/recovery | `ground_and_recovery-cross-legged-rise` |
| dance/performance | `dance_and_performance-heel-toe-shuffle` |
| dance/performance | `dance_and_performance-waltz-sway` |
| dance/performance | `dance_and_performance-robot-popping` |
| everyday tasks | `everyday_tasks-scratch-head` |

This recurrence is limited to those fixed development seeds and measured rig outputs. It does not prove that the action is intrinsically impossible, establish a population failure probability or compare every later correction. The result preserves all 72 cases, including cases with mixed seed outcomes and the context-dependent cases, rather than publishing only this eleven-case list.

These observations identify broader correction/data-review targets alongside the current grip investigation. Ground support, landing/recovery and dance require distinct authored support semantics; foot-only correction is insufficient for knees, hands or rolling bodies. The context-dependent population needs actual geometry/partner validation, while semantic correctness across every family still requires human review. The existing [developer packets](developer-packet-review-v1.md) retain all 390 clips. No rating, cleanup record, held-out release claim, training admission or supported-action claim is created by this reduction.

## Source validation

An isolated public-source copy passes **46 checks in 1.23 s**. The tests retain all partner actors/seeds, exact threshold-boundary passes, missing-export denominators and context N/A; reject unknown/duplicate/incomplete populations, conflicting flags, nonfinite metrics, unsupported review claims and excessive complete-data budgets; and preserve incomplete outputs under mid-run input or method mutation. Only the new script and test are copied. No model, downloaded rig, vendor checkout, engine or renderer is used. An initial 39-case focused run passed, followed by 43 isolated cases after field-presence/mutation checks. Three additional malformed-schema cases bring the final isolated implementation to 46 checks. The earlier v1 reduction and source proof remain preserved; v2 reproduces identical case/family/total reductions under the strengthened JSON validation. The documented CLI is also executed on the real 390-row saved population and reproduces the complete API result exactly. The existing source CI job includes this new module, with its other tests, dependencies, action pins, thread settings and 90-minute limit unchanged.

The actual reduction and isolated receipts remain local under ignored `reports/current-breadth-failure-profile-v2` and `reports/saved-breadth-failure-profile-source-check-v2`. Original raw coverage, protocols, exports, later correction studies and live/queued worker methods remain unchanged. Real human/cleanup records remain zero, all fourteen release evidence arrays remain empty, and the single full-project goal remains active.

reports/current-breadth-failure-profile-v2/result.json SHA256: `f7838d54240223df7badc3416492edb82a0871d43496c9fb0795263fa2bdee84`.

reports/saved-breadth-failure-profile-source-check-v2/result.json SHA256: `af46527bc5d5856955a3ccfc6a8358c36231911def035fd3cc9ed15c75e725d7`.
