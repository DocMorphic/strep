# What counts as realistic motion

The acceptance rule is a set of gates, not one averaged score. A clip can look smooth while doing the wrong action, miss the box, or skate across the floor. Structural validity is only the first gate. The machine-readable rubric is `benchmarks/acceptance-v0.json`.

## Physical and task checks

| Check | Initial target / assessment | Current coverage |
|---|---|---|
| Action | Correct sequence, body part, direction and outcome; roll finishes standing, lift actually moves an object, high-five includes mutual reaction | Human review pending; no automatic semantic pass |
| Weight and balance | Believable anticipation, push-off, momentum, support changes and recovery; no unexplained floating or stiff synchronized limbs | Animator review required; no validated physics/COM solver yet |
| Feet | Independently annotated planted-foot drift ≤2 cm per stance and p95 speed ≤5 cm/s | Current contact labels come from the model; only a screening proxy |
| Ground/collisions | No unintended visible body/floor/object/partner intersection; joint depth >1 cm triggers review | Joint-only depth available; mesh checks missing |
| Loop | Translation-normalized next-pose prediction error ≤2 cm, next local rotation prediction error ≤5°, root velocity gap ≤0.15 m/s and heading gap ≤2°; visually continuous playback | Numeric screen for run-loop trials; intended forward travel retained |
| Transition | No root/pose/velocity pop through the actual five-frame blend and segment boundary; plausible action change and usable final pose | Boundary diagnostics, then human assessment; a roll naturally changes speed, so whole-clip jerk is not a realism verdict |
| Hands/objects | Calibrated grip/palm error ≤3 cm and timing within two frames at 30 fps | Targets are provisional, wrist/palm calibration pending |
| Interaction outcome | Box follows grasp; high-five hands actually meet and both actors react | Baseline has no object trajectory; two-person tracks are independent |
| Asset usability | Rest-pose/scale preserved through transfer; correct engine axes, timing, root motion and markers | Pending rig transfer and engine selection |

These numbers are **our provisional engineering targets**, not universal scientific or industry cutoffs. They were set after seeing the first run-loop sample. Calibrate and version changes against licensed, action-matched reference motion and the actual target rig; never tune a threshold merely to make generated clips pass. The geometric five-centimetre floor threshold in an upstream skating detector is a contact-detection heuristic, not an allowed amount of foot sliding.

Loop scoring accounts for discrete time: the last frame normally precedes the first by one frame, so demanding identical endpoints can reject a valid moving cycle. Extrapolate the last root-relative joint pose and local orientation by one frame using the previous step, then compare to frame zero. Also report raw endpoint gaps for diagnosis and check velocity/heading. This constant-velocity proxy is not proof of a seamless loop; curved fast motion and acceleration need reference calibration and visual review.

Straight-running heading uses the root trajectory over 0.5-second windows, excluding speed below 0.2 m/s, with an initial p95 angular-error target of 3° from requested +Z. Natural pelvis twisting is not itself heading drift. Boundary heading uses one-frame prediction too. During initial implementation the endpoint and heading definitions were corrected for these issues before human review; early diagnostic screens were regenerated. This remains exploratory, not a preregistered test.

For a box grasp, require at least three consecutive contact frames before assessing attachment. A high-five is a brief impact: one frame of contact can be valid, so it must not be judged by a sustained-grasp rule. No contact is a miss, not zero timing error. No box trajectory is unsupported, not a successful lift inferred from arm motion.

Kimodo's official benchmark also covers foot skating, predicted-vs-geometric contact consistency, positional constraint error and text alignment. Our first metrics are related proxies, not a claim to have reproduced the full official evaluator. It warns that predicted-contact skating is unreliable when contact consistency is poor. [Official metric definitions](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html).

## Human review and cleanup

Use two reviewers independently. Score action correctness, weight/balance/momentum, coordination/timing, contacts/collisions, and starts/ends/transitions from 1 (wrong/unusable) to 5 (polished/convincing). Acceptance requires each reviewer to give at least 4 in every applicable category, with no major defect and all required measured gates satisfied. Record disagreement and confidence. Review at normal speed first, then slow motion; compare randomized previews without generator/seed labels. A self-review by the assistant is exploratory and not a blind animator rating.

Time actual animator edits to this same rubric. Include clips abandoned at the time limit; don't report only successfully repaired clips. No cleanup-time threshold is asserted before a matched reference workflow exists.

Keep all five seeds for each case, including failures. Report median, worst case and acceptance fraction, and distinguish actor files from paired trials. Five seeds are a feasibility sample, not proof of reliability on arbitrary actions. FID on this tiny set would not establish realism. Later evaluation needs held-out actions, rigs, objects and partners.

The current original-precision streamed encoder has small-model equivalence tests but lacks a full 8B resident comparison. Label this execution variant explicitly when reporting results.
