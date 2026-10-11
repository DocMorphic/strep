# Kenney reference proportions and alignment

The explicit reference diagnostic passed 12 generated-fixture tests and ran on
the same static Kenney derivative and 19-role profile used by the seven-motion
development transfer. Both resource records independently replayed successfully.
No existing clip, mesh, profile or model was changed.

`scripts/rig_reference_diagnostics.py:diagnose` accepts a validated rig, an
explicit target profile, distinct source joint names and finite neutral joint
positions. It applies the existing rotation/root transfer to synthetic identity
source global rotations. It measures mapped edge lengths, direction differences,
pelvis-relative joint differences and whole-mesh bounds. It supports explicit
humanoid role mappings and optional intermediate helpers; it has no action list.
Tests cover uniform scaling, a known head proportion change, shifted coordinate
origins and root offsets, immutable inputs and invalid/degenerate references.

For this actual study, the supplied reference positions came from the retained
SOMA77 skeleton. Identity-rotation skeleton FK reproduced those positions within
1 micrometre, and reproduced identity global rotations within `1e-6` per matrix
element. That checks the synthetic reference assumption for this skeleton. It
does not independently validate model generation or the animated source GLB.

The existing leg scale is **1.3262414267**. These target/reference ratios remain
after dividing by that scale:

| Mapped edge | Ratio relative to leg scale |
| --- | ---: |
| Hips → Spine2 | 2.001 |
| Spine2 → Chest | 5.881 |
| Chest → Neck1 | 0.776 |
| Neck1 → Head | 1.448 |
| LeftArm → LeftForeArm | 1.235 |
| LeftForeArm → LeftHand | 1.467 |
| LeftLeg → LeftShin | 0.918 |
| LeftShin → LeftFoot | 1.085 |

The paired torso roles are target `Spine` and `UpperChest`, respectively. Target
`Chest` remains an intermediate helper in this profile. Thus these are mapped
landmark differences, not a finding that an individual anatomical vertebra is
5.881 times longer. The mapping and different character proportions both require
consideration before choosing a correction.

After alignment, pelvis-relative position differences are **0.643272 m** at
Chest, **0.648437 m** at Head, **0.663082 m** at LeftHand and **0.661036 m** at
RightHand. The source/target hip-to-thigh directions still differ by about
55.6–55.8 degrees. Most selected primary child edges align to source directions;
branch landmarks and edge lengths are not made equivalent by that rotation.
A constant root offset cannot change these pelvis-relative differences.

This explains why leg scaling alone is insufficient as a general contact
strategy. It does **not** establish which difference caused the measured
[floor failures](kenney-source-target-floor-v1.md), or approve an alternative
mapping. The next comparison should retain the baseline and test an explicit
torso mapping alternative, then use authored whole-body support/contact targets
and bounded correction. Original raw clips must remain separate from transfer
and correction outputs. Sole-only adjustment cannot address every hand/head
witness found in the floor comparison.

Local detailed evidence is in `reports/kenney-reference-diagnostics-v1`,
`reports/rig-reference-diagnostics-source-checks-v1` and the associated guarded
job/resource records under `reports/central-hand-physical-v1`. These remain
excluded from Git. No engine, human, cleanup-time, physical-balance,
continuous-time or release approval follows from this diagnostic.
