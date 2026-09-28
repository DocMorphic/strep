# Clipped-start support comparison

The start-of-clip experiment is complete on the first declared combat seed and both previously tested rigs. It isolates an artificial contact ramp: the draft weights started at 0.25, 0.75, 1 even when predicted support was already active at frame zero. The complementary horizontal-reference term pulled the feet toward the original drifting track during those first frames.

Both variants start from the same saved weight-10 temporal correction and receive six fitting sweeps over frames 0–11. The control keeps the original start weights; the candidate removes only the generated clipped-onset ramp. Internal observed releases, custom weights, the repaired ending, and all later parameters are preserved. The candidate rejects unrecognized custom onset weights rather than silently overwriting them. Contacts remain predictions, and no frames are extrapolated outside the clip.

| Rig | Raw root acceleration max | Initializer | Equal-budget control | Retained start support |
|---|---:|---:|---:|---:|
| CesiumMan | 4.3521 | 4.7289 | 4.7289 | 4.7289 |
| Quaternius female | 7.0346 | 12.1455 | 11.6345 | 7.7791 |

Acceleration is in m/s². The second rig's remaining maximum is at frame 72, outside the edited start window and earlier temporal window. Floor penetration is unchanged at 0.694901 mm and 0.499745 mm respectively. Predicted-support p95 speeds improve, but individual speed tails remain; this is not overall motion-quality approval.

All four variants per rig—raw, initializer, control and candidate—were decoded and imported into Godot. The checks cover 1,200 actual actor-frames, 19 bones on the first rig and 65 on the second. Frames 12–149 remain unchanged by the start repair. Nine focused tests pass, covering clock reversal, hard limits, input preservation, internal releases and custom weights.

Evidence: `reports/support-start-v1`, `reports/support-start-summary-v1/summary.json`, the summary's `figures` directory, and `reports/support-start-tests-v1.json`. The summary verifies the entire declared population and source/export/engine hashes. This is a development comparison on one action and seed; independent animator review, held-out actions and release acceptance remain open.

The next comparison combines start/end support policies and root-correction curvature across the entire clip, initialized from raw transferred motion. It tests broader actions and a third rig under a fixed protocol; see `whole-support-breadth-v1.md`.
