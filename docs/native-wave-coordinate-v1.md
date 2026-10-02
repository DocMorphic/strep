# Bounded coordinate follow-up for native foot support

The [decoder-aligned warm repair](native-support-clock-repair-v1.md) left
one rate failure in its closest wave proposal. This follow-up measures the
existing coordinate method on all four saved wave proposals. It changes no
production method, source-relative cap, authoring box or release requirement.

## Reproduction and scope

Use the completed decoder-aligned fit as `--repair-from`, the same source and
support draft, and a fresh output directory. The existing CLI accepts:

```powershell
.venv\Scripts\python.exe scripts/native_support_job.py <source.glb> <draft.json> reports/<fresh-output> --joint-rates --joint-swivel --joint-foot-orientation --repair-from reports/native-support-fit-native-joint-wave-repair-v1 --repair-iterations 4 --repair-trust 0.0000002 --repair-coordinates
```

The local evidence binds the exact source, draft, parent controls/outputs,
method archives and runtime. It uses Python 3.10.21, NumPy 2.2.6 and SciPy
1.15.3. All four warm starts retain the preceding numerical left-foot stance,
Y=0 plane, authored movement limits and four-bin 120 Hz rate gates with
1e-5 tolerance. The separate strict absolute-peak guard is recorded but is
not enabled as an additional selection gate in this comparison.

Each trial runs at most four iterations with an initial 2e-7-radian radius.
The conservative dependency graph selects controls associated with currently
positive constraints. Each control is screened in both directions at six
fractions of the radius inside its original box. The complete rounded-key
constraint vector ranks steps; up to three promising choices per iteration
are independently exported and decoded. A stalled iteration shrinks the
radius by four. A better numerical score alone cannot accept a clip: the
final fitter and native preview conversion each apply their full audits.

## Terminal measurements

The four trials screen **20,356 numerical candidates**, independently
decode **13 intermediate step probes**, and take **13 repair steps**.
Intermediate step acceptance is distinct from final motion acceptance.
Failed-row groups below are positional speed, positional acceleration,
angular speed and angular acceleration. Worst excess is the largest positive
normalized constraint excess, rather than a realism score.

| Proposal | Before failed rows | After failed rows | Initial worst excess | Final worst excess |
| --- | --- | --- | --- | --- |
| 1 | 8 / 4 / 1 / 2 | 8 / 4 / 1 / 2 | 0.00379086411 | 0.0037830542 |
| 2 | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 | 3.23377306e-05 | 3.22636415e-05 |
| 3 | 23 / 4 / 4 / 4 | 23 / 4 / 4 / 4 | 0.00701338467 | 0.00700423531 |
| 4 | 14 / 4 / 0 / 8 | 14 / 4 / 0 / 8 | 0.00204734954 | 0.00203978617 |

All four proposals still pass sampled support height and fail their source
rate gates. **Zero repaired clips are accepted.** Both fitting and native
conversion retain the exact input; the selected input still fails its
authored support screen. Root tracks and boundary poses are unchanged and
unknown contact labels stay unknown. Trials 1 and 4 lower their worst excess
while increasing summed squared excess, so the lower worst value cannot be
presented as a general quality improvement.

The closest proposal remains at one failed positional-speed row. Its four
iterations screen the same five conservative columns; only the second
iteration takes a step, changing one bend parameter by approximately
-1.25e-9 radians. The worst excess falls from 3.23377306e-5 to
3.22636415e-5 without satisfying the constraint. This small coordinate
study establishes neither feasibility nor impossibility. Whether coupled
changes can reduce that row without violating other rows remains untested.

All four proposal GLBs and the selected native input pass headless Godot
4.7.2 import and native-time joint checks: five clips, 600 frames, 77 bones,
one skinned surface and non-looping playback each. Maximum differences are
5.437e-07 metres and
9.795e-07 basis elements. These are CPU pose/import
checks, not live browser, GPU skin deformation or human quality verification.
All original source, parent and method hashes remain intact at completion.

No production source changes are made for this follow-up. The preceding
commit `b6e920a` passed [hosted source checks](https://github.com/DocMorphic/strep/actions/runs/37042343190),
including the 1,661-test geometry/Studio selection and 15 JavaScript suites.
Those completed checks are not rerun solely for this documentation update.

Local evidence remains ignored rather than bundled into the public repo:

- `reports/native-wave-coordinate-canary-v1/result.json`: terminal matched
  results, source/method bindings, native conversion and engine evidence.
- `reports/native-support-fit-native-wave-coordinate-v1`: four outputs,
  controls, complete screens, independently decoded probes and archives.
- `reports/native-wave-coordinate-validation-v1/verification.json`: current
  documentation, method and terminal evidence hashes.

These are historical development wave motions with numerical stance times
and earlier root/forearm edits. There is no new model inference, model update,
human submission, licensed training-data admission or formal held-out result.
The study does not establish whole-sole planting, horizontal contact,
balance, collisions, action correctness or animator cleanup time. Broader
action/style, scene/partner/finger, rig and release validation remain required.
All 14 capabilities remain unapproved, the formal 72-by-five population is
untouched and the single full-project goal remains active.
