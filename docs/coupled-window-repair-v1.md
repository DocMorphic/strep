# Combined arm and finger repair across the edit window

The complete saved mesh audit contains 3,344 proper triangle pair-time
crossings. A native finger-control support audit finds 2,697 potentially
influenced pairs and **647 pairs that these controls cannot move**. Seven of the
fourteen queried times have no finger-influenced crossing at all. The largest
fixed-axis residual among unaffected pairs is 3.580943 mm, exceeding the
2.752983 mm largest residual among potentially influenced pairs. Simply expanding
the finger-only maximum objective would therefore leave a fixed worst row.

Control support includes every strictly positive skin influence, descendant
bones and interpolation support of editable native keys. Positive support is
only eligibility: it does not prove a usable derivative, sufficient movement or
feasibility under the other limits. Zero support proves invariance only within
this finger parameterization. All observed pairs, including unaffected ones,
remain in the audit; no convenient subset is presented as full coverage.

## Combined parameterization

`CoupledHandFingerMotion` merges the existing independent wrist/swivel/hand
rotation edits and native finger quaternion edits before evaluating the shared
hierarchy. Fingers follow the edited arm and retain their own local corrections.
It preserves the original arm source instead of treating an already corrected
donor as a new arm reference. A donor can differ in the arm channels, but changes
to finger baselines, unrelated channels, clocks, translations or scales are
rejected. Selected finger nodes must descend from the controlled hand.

The proposal path retains double precision; the actual acceptance path rounds
edited keys to float32. Export checks original 45-degree arm limits and the
existing per-finger limits, clones shared animation sampler descriptors, and
keeps native key clocks. These local editor checks alone do not validate motion
rates, palm contact or collisions; the repair study applies those separately.

## Experiment

`study_coupled_window_repair.py` combines 140 existing arm controls with 114 finger
controls, targeting all 3,344 observed pairs across fourteen times. Every pair
contributes nine inequalities along its saved separation direction. The
objective residual is not a mesh penetration depth. There is no removal of
finger-unaffected rows because arm motion can now influence them.

The original 148-pose position/angular speed and acceleration limits remain
fixed, alongside the original arm guide budgets, 962 signed-witness ceilings,
and measured palm point/relative-vector/normal bounds. The arm contact endpoint
stays protected. The original finger envelope and bounds remain unchanged.
The initial controls reconstruct the saved donor pair and reproduce its original
feasibility. The initial full-window fixed-axis residual is 3.580943 mm.

The study permits three iterations with trust sizes 0.1, 0.01 and 0.001. Its
sampled mesh guard checks actual complete surfaces before a numerically feasible
improving step can be accepted. Independent decoding then verifies clocks,
unselected channels, outside-window motion, original motion caps, palm geometry
and old witness limits, followed by fresh complete mesh queries at all fourteen
times. A failure is retained rather than promoted into Studio.

## Completed outcome and failure replay

The first iteration accepts no step. Trust 0.1 returns `InsufficientProgress`;
trusts 0.01 and 0.001 return `AlmostSolved`, each followed by eight exact
backoffs. All sixteen violate a preserved numerical constraint. The best
objective among these rejected trials is 3.224399 mm, compared with the initial
3.580943 mm. Both final GLBs remain byte-identical to the donors. All 3,344
sampled crossings remain, and the unchanged exports pass the independent mesh
guard. No proposed edit reached the mesh guard because numerical checks rejected
them first; this trial does not measure whether the new guard blocks useful
intersection migration.

An exact replay reproduces every recorded score and minimum margin within
1e-12, then reports the violated groups without changing any threshold. Every
serialized trial violates angular acceleration limits; fourteen also violate
old surface-witness ceilings. The smallest maximum angular-acceleration excess
is 9.048640e-6 rad/s^2 above the proposal cap. The largest old-witness excess is
2.662832e-8 m. These small failures remain failures under the declared protocol.

The unrounded nonlinear path also fails all sixteen proposals. However, a
separate baseline check finds that the unrounded reconstruction of the starting
controls already violates 116 old witness ceilings, with maximum excess
7.313127e-9 m, while the actual serialized donor passes. Thus the unrounded
comparison is not a feasible alternate starting animation, and its failures
cannot simply be attributed to the proposed change. The saved linear models
still use the actual serialized base values.

Next investigate feasibility restoration around the actual serialized controls,
retaining the original limits, rather than accepting a nearly feasible proposal
or dropping witness constraints. Before promoting any changed animation, also
expand mesh checks beyond the fourteen historical crossing times: those stop
at the contact instant while the finger edit envelope continues afterward.
The present unchanged output introduces no such release-phase edit.

Completed local results:

- Coupled study: `reports/coupled-window-repair-v1/result.json`, SHA-256
  `51c0f7a9d50d55a034537762a95bbf1242adfa161c88dc82d81f5f2764b226d7`.
- Study request: `0867b0ac74ff76c453eebb940362c6fb5c3c6b735527a1d3f0ac54070fc0aaa0`.
- Failure replay including baseline precision:
  `reports/coupled-window-constraints-v2/result.json`, SHA-256
  `106997290c582f5463f93500c77749a98512c7999cc56e2117bc28cfdadfa79d`.
- Replayed trials: `9c7e36a12e6db064284cf11d58df222b5d2d758a39b190bf611af41c3acb6f6a`.
- Baseline precision: `74972ec5dcafa5adaa0b145b66a4fb700fd4b2986a23d8e1555269b9f3a46eaf`.

The first failure replay remains saved separately; the second adds the starting
precision comparison. Neither generates or exports an animation.

## Verification and reproduction

The complete minimal source suite passed all 910 tests. Focused fixtures compare the combined export against sequentially serialized
arm and finger edits for both actors, exercise shared samplers, protect original
references and limits, and separate smooth proposal precision from serialized
acceptance. Window compilation tests retain every time and every crossing,
including empty times and unaffected pairs, and reject inconsistent inputs.

The completed support audit is local at `reports/window-triangle-controls-v1`:

- Result SHA-256: `0894e2d3489045cb4434c618da3409fac22d0592de2d7d8def43c92fc030101c`.
- Request: `d6526ecee59b79555426d031aa233af6597db3bd6efd131eba17025cb7d2af03`.
- Compiled triangles: `8822907b776089f336fb334ddecb75e3378ad24496f77a6c0015506ac47c17f9`.

```powershell
.venv/Scripts/python.exe scripts/audit_window_triangle_controls.py reports/finger-triangle-repair-v1 reports/paired-edit-jobs/relinearized-v2 reports/<fresh-window-audit>
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/<completed-window-audit> reports/triangle-hand-repair-v1 reports/<fresh-coupled-output> --iterations 3
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/<completed-window-audit> reports/triangle-hand-repair-v1 reports/<fresh-failure-replay> --diagnose-study reports/<completed-coupled-output>
```

These studies require bound local assets and previous artifacts, which remain
excluded from Git. This is one selected development interaction, not held-out
evaluation or universal interaction support. No training, human review or
animation-quality approval is implied.
