# Direct comparison of retained support corrections

The larger-iteration study still compares candidates against its common input. Passing that check does not prove that a new selected output improves every measurement relative to the earlier three-step output. `audit_support_iteration_pair.py` measures that difference directly for completed cases while the rest of the population continues.

Each pair is bound to frozen matching protocols, identical source assets, completed per-case selection/audit hashes, unchanged skin geometry and weights, and the exact selected GLBs. The script decodes every integer, half and quarter frame, including the terminal frame. It measures per-vertex floor-depth differences, integer-frame root acceleration and predicted-support patch speed. Recomputed support peaks must exactly reproduce the retained case audits. It rechecks consulted inputs after measuring.

The first snapshot preserves the full 24-case denominator: 13 targeted, four pair-audited and the remainder explicitly unmeasured or untargeted. Those four pairs contain 2,868 comparison times, or 5,736 posed meshes across both versions. These are completed case results, not the completed population or final engine proof.

| Case | Foot-peak change, left/right (m/s) | Largest per-vertex floor increase (mm) | Samples above the 1µm reporting threshold |
| --- | ---: | ---: | ---: |
| Backpedal, rig02 | 0 / 0 | 0 | 0 |
| Backpedal, rig03 | 0 / −0.008923 | 0.007167 | 1 |
| Grapevine, rig01 | −0.012422 / 0 | 0.002069 | 4 |
| Grapevine, rig02 | −0.010620 / 0 | 0.019357 | 3 |

The unchanged backpedal GLB is an exact control: all floor, root and foot differences are zero. The other backpedal improves its right-foot peak but raises root acceleration locally by 0.162413m/s² at frame41, despite a slightly lower clip maximum. Both dance cases clear their previous raw-relative foot-peak reporting comparison. Their clip-wide floor maxima remain unchanged, while small local depth increases remain. These micrometre-scale changes are numerical preservation diagnostics, not evidence that a viewer would notice a defect.

The evidence is `reports/support-iteration-pair-audit-v1/snapshot-v1.json`, including hashes of the captured population results and each completed pair audit. No failed or pending case is represented as a zero-error result. Predicted support is unconfirmed; none of these metrics supplies action correctness, naturalness, balance, continuous-time clearance, an animator rating or cleanup time.

A developer observation request is pending for the separate four-stage partner review. No actual user notes have arrived or been entered as evidence. The project-wide goal remains active while the 12-step population continues.

## Expanded partial snapshot

`snapshot-v2.json` retains all24 population rows and13 targeted cases, with10 completed direct pairs:7,050 comparison times and14,100 posed meshes. The population worker remains active; this is not final engine verification. Four pairs have zero changes in the decoded floor, root and foot measurements. Six improve at least one foot peak.

The added grapevine rig03 and broad-jump rigs01/03 are unchanged controls. Kneel-rise right-foot peak changes are -0.005993, -0.093095 and -0.036948m/s for rigs01/02/03. Their maximum local floor-depth increases are0.004076,0.002138 and0.000515mm, respectively;14,4and0 sampled times exceed the unchanged1micrometre reporting threshold. Maximum local root-acceleration increases are0.007860,0.073466 and0.009879m/s². Thus even lower clip-wide peaks can coexist with local increases. Five of the ten pairs have floor-depth increases above the reporting tolerance; the largest remains0.019357mm in grapevine rig02.

The review packager now supports four versions: raw transfer, common input, earlier correction and further correction. Direct-pair evidence is bound to both selected motion hashes, consulted inputs and sampled timeline. Seven tests pass, including rejection of swapped versions and changed assets/protocol/timeline. The actual four-version package has not been built: remaining population, engine and common-input quarter-frame evidence must finish first. Existing reviews are unchanged. These are development diagnostics; no human notes, ratings or cleanup time have been supplied.

Subsequent snapshot-v3 adds exhausted-walk rig01:837 comparison times with zero decoded floor/root/foot differences. Total11 paired cases,7,887 comparison times and15,774 posed meshes. Two targeted exhausted-walk rigs remain pending.

## Twelfth pair and review controls

Snapshot-v4 adds exhausted-walk rig02: both support-speed peaks decrease (left0.029083m/s, right0.029803m/s), but root acceleration gains0.098620m/s² locally and0.003681m/s² at the clip maximum versus the earlier output. One sample exceeds the1micrometre floor reporting tolerance, by a maximum local depth increase0.001191mm at frame18.25. These are genuine tradeoffs against the earlier correction despite retained common-input checks.

Twelve pairs now cover8,724 comparison times/17,448 posed meshes. Seven improve at least one foot peak; five are unchanged decoded controls. Six retain local floor-depth increases above tolerance. One targeted case remains pending, with all24 population rows still retained.

The review packager now includes measured frame shortcuts for local floor/root increases and support-speed peaks, preserving fractional times. Eight tests pass, including fractional/terminal witnesses and invalid-frame rejection. Studio's quarter-frame slider, same-frame version switching, visible character and scoped selected-result note were verified in the browser using the previous24-case catalog; no console errors. Actual new-catalog buttons remain untested until the pending study can be packaged. See review-landmark-verification.json and quarter-frame-review.png. No fabricated developer observations or release approval.
