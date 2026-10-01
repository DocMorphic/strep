# Separately authored shared palm meeting target

The previous frozen-contact repair kept selected palm anchors over 22 mm apart.
This experiment declares a new contact condition, while preserving the old
benchmark and every previous clip. It tests whether the existing native-key
editor can create the desired meeting pose and exposes what remains wrong in
the complete approach/departure motion.

## Authored condition and controls

The target midpoint is the mean of the two original skinned palm anchors at
2.091722595 seconds. Its facing axis is the normalized difference of their
outward surface normals. Actor A's target is 0.5 mm behind the midpoint along
that axis and B's is 0.5 mm ahead, giving 1 mm separation and opposite normals.
Contact scoring requires at most 0.5 mm error per target anchor, at most 2 mm
anchor separation, and at most 20 degrees error per target normal. These are
pose screens, not distributed contact or collision approval.

Both upper arm, forearm and hand may rotate within the existing window
1.408333333 to 2.591722595 seconds. Only the protected span containing this
contact is replaced; unrelated protected spans remain. A triangular native-key
correction envelope peaks at the meeting time. There are 18 controls, with at
most 15 degrees additional correction per joint from the component bounds.
Export still enforces the original-reference 45-degree arm edit budget.

The geometric fitter minimizes actual skinned-anchor and normal error, with a
small control regularizer. It does not optimize motion-rate constraints or
collisions. Every result remains diagnostic until independent checks pass.
Native clocks, root/translation/scale channels, unrelated rotation channels
and motion outside the edit window must remain exact after export.

The full geometry audit retains all 53 predeclared interval times. It queries
the complete triangle candidate population and both full vertex-depth
directions. The hash-bound donor snapshot is reused only with matching source
ancestry, topology and sample clock. Original motion-bin caps are recomputed
from the original reference clips, not rebased to the changed candidate.
Floor depths are recorded for donor and candidate at every audited time.

## Completed decoded evidence

The pose fit reaches its 150-evaluation budget; optimizer convergence is not
claimed. Independently decoded geometry nevertheless measures a 1.000019 mm
anchor gap, target-anchor errors below 0.000019 mm, and normal errors below
0.000003 degrees. It passes the newly authored pose screen.

The original motion limits fail: 551 position-speed rows, 136
position-acceleration rows, 638 angular-speed rows and 111 angular-acceleration
rows exceed their caps. Largest excesses are 0.065828 m/s, 5.410387 m/s^2,
0.257073 rad/s and 35.567881 rad/s^2 respectively. A well-matched meeting pose
therefore does not establish a usable motion clip. No threshold is relaxed and
nothing is selected for Studio.

## Complete geometry audit and decision

All 53 interval samples completed. Fourteen samples fail the unchanged mesh
regression guard. The candidate introduces 4,567 proper triangle pair-time
crossings and increases directional maximum depth in 12 observations. Aggregate
crossings fall from 4,780 to 4,688; that total does not override the new crossings.
No new uncertain pairs appear. Fourteen samples exceed 5 mm vertex penetration;
maximum depth is 21.532285 mm at 1.690827727 seconds.

At the meeting time itself, both directional maximum depths are about 18.455 mm
and 560 triangle pairs cross. Thus even the accurately fitted target pose fails
full geometry, not only its approach trajectory. Floor penetration is unchanged,
with a pre-existing maximum of 6.003415 mm. The candidate remains diagnostic and
is not selected for Studio or approved for publication as animation-quality evidence.

The next repair must consider distributed hand geometry at the contact pose,
then fit approach and departure under the original motion limits. Merely adding
pose-fitting iterations or smoothing the current triangular time envelope cannot
establish contact-pose validity. The old frozen-contact benchmark remains intact.

All 992 model-free source tests passed. Rehashing verified 3,108 bound inputs,
72 archived methods and 60 output files. The completed result SHA-256 is
`e4d6ace5568ee738dd9a6e228944af0d915de851a9f30f2f909b4602ba56c4d4`.
Raw results and generated GLBs remain local under ignored `reports/`.
No training, held-out evaluation, browser validation or engine import was performed
in this study. All 14 project release capabilities remain unapproved.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_shared_palm_meeting.py reports/coupled-headroom-continued-v1 reports/<fresh-output>
```

The command requires the bound local rigs and prior studies, excluded from Git.
Five new model-free tests verify the shared midpoint, facing normals, actor-swap
symmetry, rigid scene transforms, invalid-normal rejection and separation of
pose-screen success from collision approval.
