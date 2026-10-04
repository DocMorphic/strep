# Explicit pose targets on native animation curves

`scripts/native_pose_lift.py` transfers explicitly supplied `ContactPose` rotations into existing native `SceneEdits` curves. It supports multiple ordered target poses, parent/child rotations and multiple explicitly edited actors. It does not choose anatomical channels or restrict actions to a prompt list.

```python
from native_pose_lift import PoseLift, fit

lift = PoseLift(edits, [(first_pose, first_controls),
                        (second_pose, second_controls)])
native_controls, search = fit(lift, evaluations=60,
                              maximum_calls=3000, maximum_seconds=120)
for actor, path in candidate_files.items():
    edits.export(actor, native_controls, path)
residuals, target_report = lift.decoded(candidate_files)
```

This is a Python diagnostic API. It does not provide a Studio command, select a candidate for playback or approve a corrected animation. A pose can already fail its own contact conditions; lifting it does not turn that failure into success.

Pose targets and native edits must share the exact source `SceneContacts` instance and the same complete actor/node rotation population. Native translations cannot enter this transfer. Existing native permissions define each actor's window, protected intervals, knots, rotation budgets and displacement conditions. Targets must be strictly ordered, distinct and interior to every edited actor window. At most 32 targets and 96 complete control components are supported; no target or track subset is returned to fit that budget. Different source instances, track populations or animation epochs reject.

For each native knot vector, the search uses `raw / sqrt(1 + dot(raw, raw))`, with raw components bounded by 20. Every normalized vector lies strictly inside the unit ball. Existing native-key edit vectors are convex blends of these knots and zero-valued endpoints, so their norms also stay inside the declared track budget. Float32 serialization still receives the existing independently decoded edit audit and its recorded serialization allowance. Hard knot bounds do not imply displacement, contact, rate or geometry acceptance.

The objective measures source-relative local rotation targets on the actual native interpolation behavior at each supplied time. Native keys, clocks, interpolation modes and edit support remain unchanged. The continuous proposal minimizes normalized geodesic rotation errors with a small raw-control regularizer; the retained vector minimizes largest normalized target error and then squared normalized target error over all visited vectors, including derivative evaluations. The search also reports the Float32 proposal's target errors. `decoded()` requires every saved edited actor, verifies its static payload, animation population, selected index, frozen keys and native edit limits, then samples the independent GLB reader to measure target error again.

Explicit evaluation, objective-call and time budgets stop the search while retaining an observed vector. Evaluation-limit termination is reported as exhaustion rather than solver success. Mandatory final measurements can extend elapsed time past the chosen budget. Reaching a target or obtaining optimizer success does not approve the motion. A protected time remains frozen even when that makes a requested pose unreachable.

Full contact clocks, held relative velocities, source positional/angular rates, displacement, loop/transition behavior, triangle geometry, import/rendering, dynamics, self-collision, anatomy and human review require separate checks. In particular, the original `SceneProblem` must capture source rate caps before fitting; rebuilding caps from the candidate would hide regressions. Original clips stay selected.

## Validation

Twenty-four synthetic tests check hard knot and native-key bounds; independently saved curve targets; native clocks, frozen endpoints, unselected tracks and source hashes; failure of original rate conditions despite accurate pose matching; unreachable protected targets; multiple pose times; explicit parent/child rotations; two edited actors with an unchanged third actor; incompatible populations and source instances; source mutation; and both evaluation and call exhaustion. These tests use small synthetic rigs and do not provide motion quality evidence.

## Retained pose transferred into an actual clip

The earlier [guarded sphere-hold pose](guarded-contact-pose-v1.md) is transferred at 3.914583333 seconds onto the same canonical source GLB. Twelve forearm, wrist and first-finger tracks receive explicit native permissions matching the donor's 45-degree maxima and 0.22 m displacement condition. The edit window is the original hold interval `[2.0, 4.0333333015441895]`, with three knots at its endpoints and the donor time. Native interpolation support outside that interval stays frozen. These are new diagnostic permissions; original source rate caps are captured before fitting and remain unchanged.

The lift converges in five evaluations, 185 objective calls and 1.015 seconds. Its independently saved GLB matches all twelve local rotation targets with at most `4.734007e-7` degrees of error. All native edit/static-payload audits pass, with a maximum key change of 12.118542 degrees. This produces a real editable diagnostic clip, which remains separate from the selected original.

The complete motion audit includes 1,617 native/contact/rate times, 717 uniform 120 Hz rate times and 303,593 condition rows. All original native conditions pass. The candidate introduces 1,888 failing rows: eight positional acceleration, 356 angular speed, 155 angular acceleration and 1,369 point/held-speed rows. Native-key vector bounds, joint displacement and positional speed still pass. Whole-clip maxima alone can hide these per-joint, per-bin failures: overall angular speed is unchanged, while 356 individual angular-speed rows fail their original caps.

Every contact group retains its 5 mm point position limit, but held relative-speed conditions fail:

| Contact group | Source peak position | Candidate peak position | Source peak slip | Candidate peak slip |
| --- | ---: | ---: | ---: | ---: |
| Left grip | 2.025305 mm | 2.044865 mm | 3.067484 mm/s | 8.926707 mm/s |
| Right grip | 2.017649 mm | 1.986111 mm | 3.086231 mm/s | 25.353741 mm/s |
| Left neighbours | 4.688172 mm | 4.670285 mm | 3.141276 mm/s | 14.345711 mm/s |
| Right neighbours | 4.686497 mm | 4.653599 mm | 3.168697 mm/s | 35.436339 mm/s |

The held-speed limit remains 5 mm/s. Each stage includes all four groups, all 1,033 original contact times per group, ten correspondences and twelve separate game-frame speed populations per group. Full incident-surface audits cover 10,330 point-normal observations per stage. Surface failure counts improve from 6,198 to 2,394, but both stages still fail their authored 15-degree conditions. No contact region, target, normal limit or missing context is silently changed.

Verification independently reconstructs all 720 editable native quaternion keys using explicit half-angle/Hamilton arithmetic, re-decodes the saved candidate at every motion time, reconstructs source rate caps, recomputes all 303,593 native conditions and reproduces every failure decision. Saved point reductions, all 96 source/candidate speed populations and 20,660 surface decisions also replay. The verifier does not recompute full incident-surface skin or run complete geometry, engine or rendering queries. An initial verifier helper used NumPy advanced indexing in the wrong axis order; its failed source/log are retained, and only that helper is corrected without changing producer code, targets or tolerances.

The canonical source reader uses normalized supplied skin weights and differs from the earlier raw Godot import epoch. No full motion geometry or engine audit is attempted for this candidate; they remain unverified. No original-rate or contact allowance is relaxed. This failure does not prove that another timing or coupled correction is infeasible. Next correction must handle contact position/speed and motion-rate constraints jointly with surface orientation throughout the interval. Original clips remain selected, all 14 release evidence lists stay unchanged, and the full project goal remains active.

Local evidence: `reports/native-pose-lift-development-v1`, `reports/native-pose-lift-verification-v1` and `reports/native-pose-lift-clean-source-v1`.

The next [coupled native/contact proposal API](coupled-native-contacts-v1.md) protects native motion rates, point positions, held speeds and individual surface conditions in one proposal. Its actual correction study remains in progress; no accepted result supersedes the failures above.
