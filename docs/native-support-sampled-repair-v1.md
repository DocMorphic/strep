# Repairing between-key support violations

An opt-in deterministic correction now refines native lift corridors using
independently decoded exported GLBs. It addresses the broader development
study's [between-key height and displacement failures](native-support-action-breadth-v1.md).
Default smoothing and its output bytes remain unchanged. This is one component
of general animation authoring, not a complete motion model.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py character.glb draft.json reports/my-refinement --sampled-support-repair --sampled-support-iterations 8
```

Use a fresh immediate reports directory. This mode uses the original smoothing
proposal, with 1–16 refinement iterations; it cannot be combined with the
separate joint-rate/warm-repair modes. Studio does not yet expose this option.

## Method and evidence

Quaternion interpolation and forward kinematics can violate a world-space
condition between otherwise valid key poses. Each iteration measures the
serialized GLB at the unchanged 120 Hz/native-key/midpoint audit clock,
including exact fractional stance/edit boundaries. A fractional violation
tightens both neighboring key corridors. An exact native key affects only
that key; nearby fractional times are never snapped.

Penetration increases the local lower lift bound, excessive gap reduces the
upper bound, and ankle displacement reduces the signed lift radius. Every
restriction must remain inside the original reachable key box with exact
frozen ends. An infeasible restriction is rejected rather than discarding the
sample or moving the boundary. Smoothing retains its existing objective within
the tightened corridor. No authored draft, geometry, root, clock, displacement
limit, angle limit, source-rate cap or final selection tolerance is widened.

Full, half, quarter and eighth restrictions are tried in that order. A decoded
proposal is accepted only if its worst normalized support excess decreases,
or its total excess decreases with equivalent worst excess. This is a finite
sample search, not a convergence or continuous feasibility certificate. The
seed, every exported probe, rejection reason, tightened key limits and decoded
scores remain hash-bound in the normal job outputs. The last improving proposal
is passed to the existing independent job audit; failure to improve retains
the best earlier proposal, and failed final rate selection retains the input.

The native-key clearance reserve remains 0.25 mm. The original final sampled
height screen is nonpenetration to 5 mm; its displacement allowance remains
1e-7 m and local-angle allowance 1e-4 degrees. Repair success does not imply
every fractional height equals the native-key reserve.

## Matched development results

The unchanged seed-77 Cesium dance and Quaternius female/male get-up clips are
reused, three assets across two rig families. They are already examined
development cases, not new generation or formal release held-out evidence.
Each case uses four original smoothing variants and the same authored draft.
All twelve seeds reproduce the earlier study byte-for-byte.

Ten proposals initially fail support checks: four dance, two female get-up
and four male get-up. Each repairs its sampled support failure in one accepted
step; two already passing female proposals remain unchanged. All twelve final
proposals pass the original support/preservation screen. Twenty-two seed/probe
exports are retained for exact replay.

Dance final left minima are 0.2255–0.2323 mm; left maximum gaps are
4.8830–4.9368 mm, within the original 5 mm limit. Right minima are
0.1705–0.2445 mm. Repaired get-up right-ankle displacement is approximately
29.999748–29.999757 mm; the previously passing female variants retain their
original approximately 30.0000005 mm observations within the same numerical
allowance.

**All twelve final source-rate selections still fail; all three exact fitting
inputs remain retained.** Female rate failure counts remain 92/16/10/9,
92/16/10/9, 89/16/10/9 and 89/16/10/9. Male counts remain 93/15/10/9,
92/15/10/9, 88/15/10/9 and 88/15/10/9. Dance gains four speed failures per
variant; counts become 4/8/8/3, 4/8/8/3, 4/7/8/3 and 4/7/8/3. Improved contact
does not establish derivative quality, and this regression is retained.

Requests and results are local under `reports/native-support-sampled-cases-v1`.
Exact probe replay and actual Godot audits are tracked separately under
`reports/native-support-sampled-audits-v1`.

All 22 seeds/probes replay byte-for-byte from their saved lift restrictions.
Actual Godot 4.7.2 imports each input and four final proposals: 15 clips,
14,915 sampled bone poses and 105,578,760 reconstructed vertex observations.
Bone/clock and complete skin correspondence checks pass. Maximum bone position
error is 5.3105e-7 m, basis error 1.5821e-6, and skin vertex distance
9.50950e-5 m (0.09510 mm). All twelve imported proposals pass sampled height
checks; all three inputs retain their authored height failures. The imported
height checks do not independently certify ankle displacement, angle bounds,
motion rates or GPU appearance.

All 626 bound evidence files rehash, including original studies, seeds,
attempts, archived implementations, exact replays and actual engine resources.
Receipt: `3b1e9cce959bd9d1d96a2c6e9d2b84bfe87bc583b243a4a6da521fbea9c9ba29`.
The receipt remains local at
`reports/native-support-sampled-evidence-v1/verification.json`.
Matched fitting result hash:
`c4a8114324b71f952d4967f454477b6568f88ac560a2aea70e470ee8026cb36a`.
Replay/import coordinator result hash:
`5dbbdf4275d6a9507f4b36dd4de10bef9532a2caae617adc5e227def93247bd8`.

## Tests and remaining scope

Seventeen new tests cover exact/fractional dependencies, corridor restrictions,
frozen-end rejection, worst-first acceptance, mode validation, real GLB/source
preservation, archived attempts and unchanged final rate selection. A synthetic
GLB has alternating four-degree leg keys with valid key heights and actual
between-key penetration. Refinement removes its sampled penetration, and
every saved probe replays byte-for-byte. It is a geometric regression fixture,
not a human naturalness evaluation.

The existing full model-free suite passes 1,438 Python tests and 14 JavaScript
suites; the subsequently added alternating-leg regression passes in its full
17-test group, totaling 1,439 distinct Python checks. All new tests enter
Windows/Linux CI. No fresh browser/GPU render, independent contact annotation,
training, human cleanup submission or release approval is implied. Knee, hand,
body, object and partner contacts, stationary soles and realistic motion-rate
tradeoffs remain required work; all 14 release capabilities stay unapproved.
