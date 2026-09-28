# Whole-clip support correction across action families

This study is running, not complete. Its protocol is frozen in `reports/whole-support-breadth-v1/protocol.json`; it started after the exact endpoint-batch process completed. The fifth retained interim contains five completed cases and19 pending cases. No new generation, checkpoint changes or training are involved.

The experiment combines the revised planted-foot reference term, clipped-start/end handling, and a root-correction curvature penalty. Each candidate begins with zero edits on the raw transferred clip. All frames may change within the original absolute and adjacent-edit limits. The fitting budget is six sweeps with root-curvature weight 10 and support weight 40, without action-specific tuning. Weight 10 was chosen during earlier combat development comparisons; these results will not qualify as held-out evidence.

The fixed population is the first declared seed (1301) for every existing floor-eligible action, on all three existing rigs: CesiumMan and the Quaternius female and male characters. There are eight actions and 24 candidates, processed in this order:

1. Backpedal and check behind.
2. Grapevine dance.
3. Beckon with the left hand.
4. Broad jump and stick the landing.
5. Kneel and rise.
6. Tie a shoe.
7. Exhausted walking.
8. Jab, cross and retreat.

Swimming, stair traversal, box lifting and both handshake actors remain explicit context-dependent exclusions from this floor-only comparison. They remain part of Strep's scope and require their own scene or partner validation. Foot correction alone cannot establish knee/hand support, balance, landing quality, semantics or realism in the included actions either.

Every raw/candidate pair is retained. Independent verification decodes whole and half-frame meshes, measures floor depth, predicted contact speed/hover and root acceleration, and checks protected transforms and hard edit limits. Additional traces retain maximum support speed and its frame as well as p95, preventing percentile summaries from hiding brief slips. Actual Godot import checks both clips at all frames and bones: 8,640 planned actor-frames across variable clip lengths. Failures and pending inputs remain in the population; they are never discarded or counted as successes.

Implementation: `scripts/support_whole_clip.py`, `scripts/relax_whole_support.py`, `scripts/study_whole_support_breadth.py`, `scripts/support_velocity_traces.py`, and `scripts/summarize_whole_support.py`. The running study freezes its 30 implementation files and native-skin/engine resources. Do not modify these dependencies while it runs.

Sixteen focused curvature/solver/population/engine-accounting tests pass; five additional summary tests pass. Reports are `reports/whole-support-tests-v1.json` and `reports/whole-support-summary-tests-v1.json`. The initial explicitly partial summary is `reports/whole-support-summary-pending-v1`; it records 0/24 complete, 24 pending. A future completed summary must be written to a new directory and verify the actual exports and engine evidence. No release gate is approved by this study.

The second retained interim, `reports/whole-support-breadth-interim-v2`, verifies two of 24 inputs and 600 actual engine actor-frames. Backpedal rig01 improves floor penetration and support-speed maxima. On rig02, predicted-support hover drops from roughly 100/105 mm to 4.34/9.68 mm, and p95 foot speeds improve from 0.160/0.131 to 0.133/0.083 m/s. However, maximum foot speeds worsen from 0.209/0.143 to 0.286/0.208 m/s, and peak root acceleration increases from 7.495 to 11.673 m/s². Its floor penetration rises from zero to 0.590 mm. The constraints/export checks pass; the mixed movement quality is not approved. Twenty-two inputs remain pending, including the active third rig.

The third interim, `reports/whole-support-breadth-interim-v3`, verifies all three backpedal rigs and 900 actual engine actor-frames, retaining 21 pending inputs. Rig03 shows a similar tradeoff to rig02: predicted-support hover falls from 93.36/98.16 to 10.45/20.20 mm and p95 speeds fall from 0.160/0.129 to 0.112/0.095 m/s, while maximum speeds rise from 0.182/0.173 to 0.219/0.204 m/s. Root acceleration rises from 7.595 to 12.149 m/s², maximum local rotation step rises from 16.158 to 18.166 degrees, and floor penetration rises from zero to 2.658 mm. Bounds and import checks pass; motion quality remains unapproved. The active study has moved to grapevine dance.

The fourth interim, `reports/whole-support-breadth-interim-v4`, retains4/24 completed and20 pending inputs. Grapevine dance on rig01 reduces floor penetration64.345 to1.556 mm and root acceleration12.713 to11.068 m/s². Right-foot maximum predicted-support speed improves0.1663 to0.1583 m/s, but the left worsens0.1323 to0.1974 m/s. Bounds/import checks pass; this mixed quality remains unapproved. The active study proceeds with dance on rig02.

The fifth interim, `reports/whole-support-breadth-interim-v5`, retains5/24 completed and19 pending inputs. Grapevine dance on rig02 increases floor penetration0 to1.453 mm, root acceleration20.549 to20.945 m/s², and maximum predicted-support foot speeds0.2099/0.2980 to0.2961/0.2981 m/s. These regressions remain explicit despite passing edit/import checks. The study proceeds to dance rig03; the separate release-hold experiment remains frozen to its original four-case population.
