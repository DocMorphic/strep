# Decoded finger proposal diagnostic

This follow-up checks whether the saved proposal from the old-witness omission
experiment survives actual float32 animation export. It does not change candidate
acceptance, replace the Studio animation, or approve a contact interaction.

## Method

`replay_finger_proposal.py` binds the completed finger experiment and constraint
diagnostic by their recorded hashes. It reconstructs the same native finger
controls, original motion limits, measured palm bounds, 962 signed-witness
ceilings and 63 protected-time triangle pairs. The saved parameter scale remains
authoritative; reconstructing it through degrees and radians permits only four
machine epsilons of relative roundtrip error.

Eight predetermined fractions of the saved proposal are evaluated in order:
1, 1/2, 1/4, 1/8, 1/16, 1/32, 1/64 and 1/128. The largest fraction passing the
unchanged motion and palm gates is selected for diagnostic export. Old-witness
failures remain recorded. If none passes, the full rejected step is retained as
a diagnostic instead. Neither selection path confers approval.

Exported GLBs are independently decoded. Checks preserve body/wrist poses,
unselected channels, native clocks and outside-window motion. Motion and palm
gates are reevaluated on the decoded poses. Fourteen declared timestamps compare
donor and diagnostic using full-vertex signed depths in both directions and
proper triangle crossings. Donor crossing counts come from the hash-bound prior
audit; diagnostic crossings and both versions' depth queries are evaluated anew.

## Motion and contact result

Only the quarter step passes both motion and palm gates. Its fixed-axis triangle
violation falls from 1.048854 to 1.015514 mm; this quantity is an objective
residual, not a penetration depth. It still violates 196 old signed-witness
ceilings, with maximum excess 0.041278 mm. Both diagnostic exports explicitly
remain rejected.

The two palm markers move 0.002500 and 0.000052 mm. Relative-vector drift is
0.002500 mm, and unit-normal changes are 0.000249980 and 0.000001954. These pass
the original bounds but do not establish convincing contact: the original palm
marker gap is already 22.624 mm.

## Geometry result

The fourteen queries total 3,344 donor versus 3,346 diagnostic proper pair-time
crossings. The protected time retains all 63 crossings. Of 28 directional
maximum-depth comparisons, seven increase, three decrease and eighteen are
unchanged. The largest increase is 0.035259 mm; the largest decrease is only
0.000332 mm. At the exact protected time, donor depths of 1.896476 / 1.685679 mm
become 1.928990 / 1.720938 mm.

Thus a lower fixed-axis objective does not demonstrate better mesh clearance.
This proposal causes actual geometric regressions as well as signed-witness
violations. The experiment does not justify dropping those ceilings. The next
repair should track fresh surface geometry across the edit window and preserve
the original motion/contact gates; this local proposal is not evidence of
general infeasibility.

Completed local artifact hashes (SHA-256):

- Result: `49a48566ed050772696803da6091961f62fa1028822abbf708ea9c92f2eaad34`.
- Request: `32a94e078916fd7be22da8b516d518b961a0261c8da77f957a9ac80ce32111e6`.
- Decoded checks: `484f0f97f19b4354023205a8717797e7397352f99bf0f240dca7ba8262009296`.
- Geometry: `443e5238ec041e9c90f28bb959d5304090dd58c6af77eeb835c549dccb06a4fb`.

All recorded replay inputs and outputs were rehashed after completion.

## Reproduction and limits

```powershell
.venv/Scripts/python.exe scripts/replay_finger_proposal.py reports/finger-triangle-repair-v1 reports/finger-proposal-groups-v1 reports/<fresh-replay-output>
```

The replay requires the separately acquired rig and bound local experiment
artifacts; they are excluded from the public repository. The minimal source
suite passes all 876 tests, including six replay selection/scale checks. Commit
`6a49600` also passed hosted Windows and Linux checks.

This is a selected development pair and fourteen sampled times, not held-out
evaluation, continuous collision certification, self-collision validation,
engine validation or human review. No generation or training occurred. All
release capabilities remain unapproved.
