# Release target discontinuity

## Third completed case

The unchanged broader study separately completed its first gesture case, beckon-left on rig01. `reports/whole-support-breadth-interim-v7` verifies7 of24 cases. For this gesture,300 engine poses pass and floor depth falls60.05→0.94 mm; left/right support speed falls0.01745/0.01188→0.000298/0.000143 m/s. Root acceleration rises0.43326→1.84554 m/s², with the new peak at frame1. This is an additional boundary/dynamics regression, not a release-window observation; the gesture's drafted support spans the clip.

`reports/support-release-interim-v3` independently verifies three of four cases, 1,530 engine poses and zero passing dynamics screens. Backpedal on rig01 lowers left/right support speed to0.07426/0.06036 m/s and root acceleration to4.47854 m/s², but worsens right-foot global acceleration and three release windows. Release19 rises to7.44587 m/s² versus3.46889 raw and3.17424 prior. The extended reference diagnostic in `reports/support-release-reference-v2` retains all31 releases and11 regressions. At this release, a6.84 mm offset remains before switching targets; the next candidate step is7.99 mm versus1.29 mm raw. The last case is still running and the study protocol is unchanged.

## Earlier two-case analysis

The second release-hold case has completed: dance on rig01. Both completed cases pass1,080 actual Godot pose checks and decoded edit limits, but neither passes the frozen dynamics screen. The broader unchanged support study now has6 of24 completed cases; all inputs and unfinished cases remain in `reports/whole-support-breadth-interim-v6`.

For dance, left support peak speed changes from0.13228 m/s raw and0.19742 prior to0.07891 candidate; right changes from0.16627 and0.15830 to0.13292. Root acceleration improves slightly from11.06850 prior to11.04837 m/s², below raw12.71317. Five individual release windows still regress. See `reports/support-release-interim-v2/summary.json`; passing playback is distinct from passing the movement screen.

`analyze_support_release_reference.py` checks the retained completed artifacts and recomputes every release acceleration window from decoded centroid tracks. It records20 releases across the two completed cases, including all8 regressions, without rerunning fitting. Input hashes and all rows are retained in `reports/support-release-reference-v1/summary.json`.

At all eight regressions, drafted support weight changes from1 to0 at release, while the horizontal reference term changes from0 to30 before patch normalization. The foot therefore switches from an anchor to the uncorrected swing path while an offset remains. For dance's right-foot release45, the prior frame's corrected-to-raw offset is7.92 mm. The candidate moves6.56 mm in the next frame versus1.40 mm raw; peak acceleration becomes10.27 m/s² versus3.50 raw and3.85 prior. Release193 has10.15 mm residual offset and9.24 m/s² peak versus4.00 raw and4.11 prior.

This identifies a discontinuity in the objective, not proof that it explains every acceleration change. Several failing windows differ only slightly; none is removed or excused. A subsequent correction should carry the offset smoothly into swing or constrain actual foot dynamics, and must inspect the full swing so a later spike cannot hide outside the current release window. The current four-case ablation continues unchanged. Contact labels and physical intent remain unconfirmed; no quality or release approval follows.


## Complete four-case result

The fixed held-support study completed all four cases and1,980 actual Godot actor-frames. Independent `reports/support-release-final-v1` recomputes the unchanged numerical screen:0/4 pass. The final backpedal rig03 improves L/R support max speeds from original-prior0.21935/0.20414 to0.11288/0.10649m/s, but root acceleration rises from7.59451raw/12.14903prior to13.66230m/s². Release acceleration regresses at Left32,Left129,Right86, including the small regressions rather than dropping them.

`reports/support-release-reference-final-v1` recomputes ALL42 releases and14 regressions. The final case adds residual offsets14.81/12.21/5.56mm at its three regressing releases, all with support weight1→0. This retains the objective-discontinuity evidence, not proof of sole causation. Trial exec90122 exited0 and was consumed. The exact waiting actual-foot acceleration pilot began on its declared backpedalrig01 input with no changes to its frozen protocol.
