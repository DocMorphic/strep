# Clip-end support: controlled repair experiment

The support guide treated a clipped interval as a release. On the first input, both feet remain predicted as supporting through frame 149, yet their anchor weights fall from 1 to 0.75 to 0.25. Because the revised reference penalty uses the complementary weight, this also restores the pull toward the original drifting foot position just before the clip ends.

`support_clip_boundary.py` removes only the release fade for an interval ending exactly at the clip boundary. It preserves a real onset ramp, releases observed before the boundary, anchors, interval labels and their unconfirmed status. It generates no frames outside the clip. This is an explicit experimental policy, not an inference that a foot must stay planted beyond the available animation.

`reports/support-endpoint-v2` starts both candidates from the same completed motion-006-rig-01 correction. Each receives six alternating sweeps over frames 138–149, with identical original edit/step bounds and optimization settings. One retains the old weights as an extra-iterations control; the other retains support at the clip end. Exported frames before 138 are exactly unchanged. The control barely changes the spike, while the boundary policy removes it on this input.

| Final step speed (m/s) | Previous correction | Extra iterations, old weights | Retained endpoint support |
|---|---:|---:|---:|
| Rig 01, left | 0.275600 | 0.275586 | 0.0000202 |
| Rig 01, right | 0.093557 | 0.093604 | 0.0000244 |
| Rig 02, left | 0.276820 | 0.276786 | 0.0000025 |
| Rig 02, right | 0.261131 | 0.261119 | 0.0000012 |

The second input has now completed the same comparison in `reports/support-endpoint-batch-v1/cases/motion-006-rig-02`. Whole/half-frame floor depth remains 0.68954 mm and 0.50178 mm respectively. Root acceleration peaks remain 6.17194 and 14.50424 m/s²; these occur earlier and are not repaired by this tail-only change. Individual speed spikes elsewhere also remain. Do not interpret endpoint success as whole-clip realism.

Both inputs pass independent decoded edit/preservation limits and actual Godot imports of raw, parent, control and repaired clips: 1,200 actor-frame checks in total, 19 bones on rig 01 and 65 bones on rig 02. Eight focused boundary/solver tests pass, including immutable earlier frames, the fixed-window join, absolute/adjacent edit limits and JSON serialization. The inspected plot is `reports/support-endpoint-v2/figures/endpoint-speeds.png`.

The first attempt, `reports/support-endpoint-v1`, is retained as failed. It completed the control candidate but could not serialize a NumPy integer in the proposed policy's provenance. The fix converts that frame number to a plain integer; a serialization assertion was added. The new complete attempt has a separate folder and implementation snapshot.

The complete ten-input batch and independently verified population report are now finished in `reports/support-endpoint-summary-v1/summary.json` and `summary.md`. All ten matched inputs retain identical initializers, bounds and six-sweep budgets, exact EOF-only policy changes, preserved earlier frames and all four engine inputs. Together they cover 6,000 actual Godot actor-frame checks. The verifier's ten focused tests include hidden final-step spikes, absent support, incomplete traces and invalid extrema.

Retaining endpoint support reduces the final-step maximum in all ten pairs; the largest repaired final step is 0.00006687 m/s. All ten meet the proposed floor/p95-slide/hover proxy screens. However, eight still contain earlier support-speed maxima above 0.05 m/s, with a worst maximum of 0.677615 m/s. That comparison of maxima is diagnostic, not a new release threshold. Root-acceleration and floor extrema are unchanged between equal-budget control and repair in every pair. Endpoint success is not whole-clip realism.

`decision.json` binds the completed reference and endpoint summaries and retains the complete denominator. `population.png` plots both the reference-weight acceleration tradeoff and remaining support-speed tails; `plot.json` records the figure, script and decision hashes. The broader whole-clip study has now started its first of 24 action/rig inputs. These are development results; held-out actions, independent animator review and all release gates remain open.
