# Bounded supplied-rig scene correction proposals

`native_scene_fit.py` generates editable GLB proposals against the source-bound
body, object and partner conditions in [native scene contacts](native-scene-contacts-v1.md).
Authors explicitly allow existing rotation or translation tracks to change.
No action names, SOMA joint names or automatic anatomical mappings determine
the controls. This is experimental correction infrastructure, not a demonstrated
general interaction solution.

```powershell
.venv\Scripts\python.exe scripts/native_scene_fit.py contacts.json permissions.json reports/new-scene-fit --iterations 4 --trust .02
```

The permissions schema is `strep-native-scene-edit-v1`. Its exact fields are
`schema`, `contacts_sha256` and `actors`. The SHA binds the complete contact
request, including actor hashes, animation indices, placement, objects and
contact conditions. `actors` names the subset permitted to change; other actors
stay unchanged. Each actor declares:

| Field | Meaning |
| --- | --- |
| `window_s` | Positive edit range inside the original shared clip. |
| `protected_s` | Explicit array of protected closed intervals or exact times. |
| `knots_s` | 3–12 increasing control knots, including the exact window endpoints. |
| `tracks` | 1–16 explicit `{node, path, maximum_change}` declarations. |
| `maximum_joint_displacement_m` | Original-relative bound for every skin joint on the 120 Hz motion clock, up to 22 cm. |

Track `node` is a skin-joint index. `path` is `rotation` or `translation`.
`maximum_change` is cumulative source-relative angle in degrees for rotation
(at most 45), or local translation-vector length in metres (at most 0.22).
The track must already exist and use LINEAR interpolation. Missing tracks,
helper nodes outside the skin, new channels, scaling edits and unsupported
selected interpolation are rejected. All animations must remain readable by
the existing decoder; unselected animation values and metadata are preserved.
Duplicate animation contents do not cause the selected index to be guessed.

For example, an actor's right wrist and forearm could each have a five-degree
rotation budget, or an existing root translation track could have a two-centimetre
budget. The author must select actual nodes from the supplied rig. These choices
do not label a motion anatomically correct or certify its physical plausibility.

## Preserved data and numerical limits

Only native keys whose entire open interpolation support lies inside the edit
window and outside all protected spans can change. Boundary/frozen keys, all
other tracks, native channel identities, clocks, duration, bind geometry,
mesh attributes, embedded image payloads and animation metadata are checked.
Controls blend source-relative rotation vectors or local translations across
the authored knots; native LINEAR interpolation remains the exported behavior.

Controls are dimensionless fractions of each track's budget. The trust argument
is a fraction, not radians or metres. The local solver currently supports up to
96 control components, 1–16 iterations and trust up to 0.02. Component boxes
are supplemented by cumulative native-key vector norms and decoded export
bounds. Rotation serialization allowance is 0.0001 degrees; translation allowance
is 1e-7 metres. These are explicitly recorded, not hidden authored budget changes.

Every edited actor retains original source maxima for all skin joints in four
fixed time bins on a 120 Hz uniform clock: world positional speed and acceleration,
world angular speed and angular acceleration. The existing sampled-motion
tolerance is 1e-5 in each metric's units. Position changes are also checked on
that uniform clock. These are sampled kinematic preservation screens, not
anatomical joint limits, force/balance constraints or continuous guarantees.
Separate foot-specific legacy/absolute-peak, floor and engine audits are not
replaced or reported as passed by this new contract.

All declared point/centroid contacts enter the proposal problem. World, moving
object and partner correspondences keep the earlier exact-touch/held semantics,
object-local hold errors and all twelve separate game-frame speed populations.
A missing held velocity population fails. Candidate skinning preserves every
loaded influence and primitive rather than approximating with a dominant bone.

The optimizer uses the existing minimax linear proposal and L1 step selection,
with bounded backtracking. Intermediate trials may violate numerical conditions;
they are retained as failures. Every evaluated trial is serialized to GLB and
independently decoded before its merit is used. Final contact and edit audits
run again on the saved proposal. `native_constraints_pass` depends on the actual
final decoded constraints, not an optimizer's success flag or claimed final merit.

## Output and current selection policy

A fresh job retains source GLBs, exact authored JSON, implementation snapshots,
original source-rate arrays, every evaluated control vector and GLB, final
proposals and contact observations. `request.json` records the original source
paths plus explicit actor-to-snapshot paths/hashes, so relative actor filenames
can be resolved from the archive. Source, copied request, actor and method
mutations reject. The original input snapshots remain available on failure.

**Originals remain selected in this experimental path, even if native checks
pass.** Proposals are separate files for further inspection. Whole-scene
geometry, actual imported-skin contacts, editable native SOMA conversion where
applicable, and developer/animator review remain separate requirements. The job
does not claim collision, engine, human-quality, training or release approval.
It does not change Studio's existing correction selection behavior.

## Retained development trials

Three four-iteration trials used the original source files and unchanged
contact/motion budgets. None passed. They are not new model inference or formal
held-out trials.

| Trial | Result |
| --- | --- |
| Synthetic body translation | A two-millimetre requested lift remains 1.98987 mm from its target, exceeding the 1 mm limit. Eighteen sampled positional-acceleration rows fail; maximum excess is 0.0009748 m/s². |
| Existing corrected sphere grip | Left position/speed stay at 2.21926 mm and 3.75622 mm/s. Right position worsens from 2.24677 to 2.41345 mm; speed improves only from 10.19763 to 10.18868 mm/s, still above 5 mm/s. Motion failures: 38 speed, 7 positional acceleration, 0 angular speed and 4 angular acceleration rows. |
| Existing high-five, seed 5101 | Hand separation decreases from 206.23257 to 170.58694 mm, still above 30 mm. Actor A fails 262/41/116/26 speed/acceleration/angular-speed/angular-acceleration rows; B fails 19/20/32/5. |

The sphere allows only the right forearm/wrist, each five degrees, over 1.5–4.5
seconds, with 3 cm sampled joint displacement. The high-five permits both actors'
left arm/forearm/wrist, each twenty degrees, over 1.5–3.5 seconds, with 22 cm
sampled displacement. Both start from zero source-relative edits. These finite
search results do not prove infeasibility or that larger budgets/data would solve
the interactions. Reduced target error is not animation-quality improvement.

An independent replay reconstructs all 76 GLB exports from 70 evaluated control vectors byte-for-byte,
recomputes all source rate arrays exactly, reproduces final merits and checks
final contacts with a separate full-skin evaluator. Maximum coordinate difference
is 4.30e-16 metres; 326 retained evidence files rehash. The first verifier stopped
because its NumPy indexing moved the joint axis before time; the corrected fresh
replay retains the failed observation and uses explicit time-first indexing.
No fitter inputs, computation or motion budgets were changed for that repair.

After the studies, request snapshot guards, explicit actor snapshot metadata,
trust-unit labels and the actual-final-merit check were strengthened. The replay
checks that the numerical problem class still matches the archived revision and
the optimizer's only change is the metadata unit label. All 132 focused model-free
checks pass, including 29 new fitting tests, both new lifecycle mutation cases,
duplicate animation indices, every joint/time displacement row, moving objects,
partners, protected interpolation and a passing unchanged-source fixture.
That passing fixture performs zero optimization iterations and is not evidence
of successful motion correction. An initial validation command named a nonexistent
test file and ran no tests; its corrected transcript is retained separately.

Evidence: `reports/native-scene-fitting-development-v1/verification-v2/verification.json`
and `reports/native-scene-fitting-validation-v2/checks.json`.

Next work should diagnose the near-static rate rows and serialized proposal model,
add complete scene geometry and actual imported-skin checking, and reuse only
source-bound evaluated proposals. Increasing iteration counts alone or loosening
the recorded budgets is not supported by these results. All fourteen capability
gates and the full-project goal remain open.
