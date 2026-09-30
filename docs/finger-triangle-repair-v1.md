# Finger-only repair with measured palm preservation

The protected-time crossing is influenced mainly by finger bones. This study
adds native-key finger curves, keeping body/arm/wrist motion fixed while bounding
the actual palm surface geometry. The completed experiment accepts no change;
the saved donor remains the output. A diagnostic on its local solver model
identifies a useful next comparison without relaxing candidate acceptance.

## Explicit change in control scope

The preceding approach experiment freezes the complete contact pose. This is a
separate finger-only alternative: 19 nonterminal finger joints per actor, with
114 scalar controls total, may change inside the existing authored window
[1.4083333333, 2.5917225951] s. Their single triangular correction envelope peaks
at the exact protected time, 2.0917225950783 s. The original GLB key clocks and
rotation interpolation are retained; clips are not resampled onto 30 fps keys.

Local rotation budgets reuse the earlier finger fitter's edit limits: thumb
base 8 degrees, other bases 5 degrees, and distal joints 12 degrees. These are
source-relative edit budgets, not anatomical limits. Bounds additionally cap
adjacent native correction-angle changes at 5 degrees before quantization.
Proposal poses use double precision; acceptance and export use float32 keys.
Arm, wrist, other body channels and motion outside the edit window remain exact.

Fixing a wrist does not fix skinned palm geometry. The declared contact vertex,
14712, is influenced by several base finger bones: roughly 35% index, 35% ring,
14% middle, 6% pinky, 10% hand, and a small thumb contribution. Consequently this
experiment measures the actual vertex and its adjacent surface triangles.
It limits each palm vertex's displacement and the change in their relative
contact vector to 1e-5 m. Each area-weighted unit surface normal may change by
at most 1e-3 in vector norm (about 0.0573 degrees).

The source marker gap is already 22.623660 mm. That lies within the saved scene's
30 mm annotation tolerance, but it is not evidence of convincing palm contact.
Preserving this geometry is a regression check, not a high-five quality result;
the marker choice and contact target remain subject to review.

## Objective and gates

A fresh surface query at the exact protected time finds 63 proper triangle-pair
crossings. Every pair contributes nine fixed-direction vertex inequalities to
the objective, requesting 1e-8 m separation. All original position/angular speed
and acceleration limits on the 148-pose source clock stay fixed. The same 962
signed vertex witnesses retain their existing per-witness ceilings. Three local
iterations are allowed, with the prior trust sizes and eight exact backoffs.

Exports independently check native clocks, unchanged body/wrist poses, frozen
outside-window motion, original motion limits, measured palm bounds and old
witness ceilings. Fresh full-surface queries cover fourteen declared timestamps:
the thirteen prior witnesses plus the exact protected contact time. This is not
a continuous collision check or a self-collision audit.

## Completed outcome

The first iteration rejects all 24 exact trials because each has a negative
preserved constraint margin, then stops. The active fixed-axis violation remains
1.048854 mm; it is not a penetration-depth measurement. Both output GLBs are
byte-identical to the donors. The actual palm displacement and normal drift are
zero. All 63 protected-time crossings remain, with 3,344 proper pair-time
crossings summed across the fourteen queries. No candidate is published to
Studio or approved for quality.

## Saved-model diagnostic

`diagnose_finger_proposal.py` reuses the immutable local derivative model and
trust radius 0.1. It omits one constraint group at a time only inside this
diagnostic; it neither evaluates nor exports an edited motion and cannot accept
an animation. The objective rows and their directions remain fixed.

| Diagnostic omission | Predicted fixed-axis violation (mm) | Solver status |
| --- | ---: | --- |
| None | 1.048820 | AlmostSolved |
| Original motion rows | 1.048739 | Solved |
| Palm preservation rows | 1.048820 | AlmostSolved |
| Old signed vertex ceilings | 0.915439 | AlmostSolved |

Removing old vertex ceilings permits the largest predicted reduction, about
0.133415 mm from the original value. This is evidence about this local model,
not proof of nonlinear feasibility or an instruction to discard those bounds.
The returned proposal still has a slightly negative predicted remaining margin.
Before changing the correction method, compare actual decoded geometry and
original motion/palm gates for that proposal. Determine whether the old signed
surrogates are preventing genuine surface improvement or correctly detecting a
regression. Preserve every rejected result.

## Verification and provenance

The complete minimal suite passed 868 checks before two group-selection tests
were added; all 12 new finger/diagnostic tests pass. They cover serialized
roundtrip, native clocks, shared sampler isolation, body and outside-window
preservation, per-finger limits, narrow envelopes, actual skin normal changes,
invalid controls and separation of diagnostic constraint groups. The CI list
now contains 870 tests. Prior commit `028be4c` passed hosted Windows/Linux checks.

Local completed artifacts:

- Finger trial result: `reports/finger-triangle-repair-v1/result.json`, SHA-256
  `1f072d6989ef553aa47c7dd8474578f99c46e10be0ce16e66bbc6a6afc063235`.
- Trial request: `adb1ffc0c5b46989262c26c56a327abce03c536e186988c1880011c3dfeb4423`.
- Decoded checks: `2981255e0c344632b13f91d455e3abebc23754460769b7d8b8020ddd59e8e3af`.
- Fresh geometry: `1fdf5761c87cf41fd90e174946ec67f6cbf49e0f09f5213a02571272abf6ae30`.
- Group diagnostic: `reports/finger-proposal-groups-v1/result.json`, SHA-256
  `38bc32cf8c1ebf1f177c5091e068280962e9d75d202910311ac42f3bd62a57f0`.
- Diagnostic proposals: `b5a6c6b1f2d78d28c7bf2713ef51dc1e54f01fa7baa403f0ff6f75b0ca44bcd8`.

```powershell
.venv/Scripts/python.exe scripts/study_finger_triangle_repair.py reports/scene-pair-hand-norm-larger-trust-v1 reports/<fresh-finger-output> --iterations 3
.venv/Scripts/python.exe scripts/diagnose_finger_proposal.py reports/<completed-finger-output> reports/<fresh-diagnostic-output>
```

No generation, training, held-out use, new engine validation or human quality
approval occurred. General interaction quality and all release gates remain open.
