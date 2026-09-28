# Sustained contact after a single-frame correction

The timed request already specifies standing-to-kneeling during 0–2 seconds, an upright kneeling pause during 2–3 seconds, then rising. The prior correction studies constrain only one frame. This experiment proposes keeping the same fixed knee surface patches and targets throughout the pause. These are development authoring choices, not human-confirmed support annotations.

The unchanged body input and both single-frame corrections were decoded at 240 samples over frames [60,90). All three miss the proposed full-interval contract. At the unchanged 20 mm contact tolerance:

| Version | Left knee samples within tolerance | Right knee samples within tolerance | Maximum left/right error |
|---|---:|---:|---:|
| Body input | 0% | 6.25% | 78.64 / 44.68 mm |
| Limb-zero prior | 30% | 5.83% | 56.68 / 91.60 mm |
| Body-reference prior | 2.5% | 10.42% | 63.99 / 44.68 mm |

All three retain floor clearance within the 5 mm screen during the sampled pause. Passing the earlier center-frame contact screens therefore does not establish sustained support. This audit adds a new proposed contract; it does not retroactively claim the earlier solvers promised interval contact. Five focused track tests pass, including detection of a single touch that fails a hold.

`reports/knee-hold-pilot-plan-v1` freezes a first-case pilot using the body-reference candidate as its initial motion and the original body-corrected trajectory as its preservation reference. The two fixed target positions, 5 mm floor limit, 20 mm contact tolerance, joint/root budgets and four-sweep/80-iteration settings remain unchanged. Contact spans frames 60–89, with 13 editable context frames on each side: frames 47–102. Preflight finds 29 infeasible contact frames; only frame 62 already satisfies the new contract. No surrounding non-contact frame fails preflight.

The prepared-trajectory runner validates input hashes, finite shapes, interior edit windows, masks and pose budgets before fitting. Five rejection tests pass for changed trajectory bytes, invalid windows and omitted mask frames. A validation-only execution accepted this plan. No interval fit has run yet: it follows the currently running eight-case single-frame cohort.

The independent auditor checks actual engine evidence, all key/eighth-frame floor samples, every declared contact interval, before/after edit budgets and exact outside-motion preservation before export. It also compares patch speeds across the full edit window, including entry and release, against a reconstructed body reference. These new runner/auditor paths are compiled and input-tested; their full fitting/export audit remains unexecuted. No default, visual, dynamics or release approval is asserted.


## Completed hold pilot

The four-sweep pilot and independent exported audit completed. It fails onset and release contact and reaches 5.07945 mm sampled floor penetration against the unchanged 5 mm screen. Left/right contact coverage is 219/240 and 236/240 samples, respectively. Both knees peak in speed at the release boundary (frame 90). Pose and local edit-step bounds pass; the three global root-step failures were already outside the edit window in the source. All 180 Godot frames match. Exact failing ranges and the next solver questions are in `reports/knee-hold-pilot-audit-v1/decision.json`. No quality or release approval.
