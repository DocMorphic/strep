# Between-key floor constraints in motion correction

The preceding [whole-clip study](coupled-clip-sequence-v1.md) left a backpedal window blocked by floor penetration between animation keys. Rechecking the retained proposals with the auditor's float32 clock confirms that blocker at frame 76.5. Integer-key floor constraints alone cannot represent it.

`coupled_half_floor.py` adds all mesh-vertex floor rows at both half-frame neighbors of every editable key. This pilot includes six half frames and 53,064 additional rows. The margin uses the actual serialized pose and the original vertex depth plus the unchanged 1 micrometre allowance. Derivatives use central differences on continuous local translations/rotations before float32 serialization, with the same sampling clock. Repeated trust proposals at identical coordinates reuse the derivative model. Full nonlinear step guards and independent exported-file audits still decide acceptance.

The three frozen preflight directional derivative errors are below 1.73e-7 against a 2e-4 threshold. Separate tests cover boundary half frames, an actual retained floor violation, directional derivatives, cache invalidation, and invalid derivative steps. The combined correction regression suite passes all 32 tests on the provisioned development machine; one new actual-rig test requires retained local study fixtures.

## Matched experiment

`reports/half-floor-pilot-v1` compares key-only proposals with key-plus-half proposals, starting from the same latest verified backpedal / rig 02 clip. Both edit frames 75–79, use at most six iterations, the same three trust bounds and eight step fractions, and preserve the cumulative original edit/contact/geometry limits. The objective measures excess root acceleration across the entire clip. Export acceptance additionally requires at least 0.1% whole-clip improvement and preserves the starting clip's per-center root values within the existing numerical allowance.

| Measurement | Starting / key-only result | Key-plus-half result |
| --- | ---: | ---: |
| Whole-clip squared excess score | 44.543349 | 44.015960 |
| Root acceleration peak, m/s² | 11.661140 | 11.597101 |
| Root centers above original reference | 7 | 7 |
| Accepted correction steps | 0 | 4 |

The additional rows unlock a **1.18%** score reduction. The new method stops at iteration five rather than exhausting its budget. Both methods pass all eleven independent preservation checks and actual Godot import checks, totaling 600 actor-frame samples. Only the new method passes the improvement requirement. Five half-floor model builds take 19.75 seconds total on this machine; this is additional work, not an equal-runtime comparison. Request, source, implementation, resource, output and completion hashes are verified in the retained summary.

The original raw peak is 7.495190 m/s², so it remains unrestored. All seven failing centers remain (22, 23, 64, 65, 77, 80, 111). Maximum sampled floor-depth increase is 0.996500 micrometres against the original correction reference, below the unchanged 1 micrometre allowance; that preserves existing geometry and does not imply zero absolute penetration. Half-frame checks also do not prove collision-free continuous playback.

A retained final-stop diagnostic again identifies frame 76.5 / vertex 8631: the smallest three fractions at the last trust bound would improve the objective but increase floor depth by about 1.025–1.026 micrometres. Anchor and rotation guards pass. The added continuous proposal rows therefore help but still do not guarantee the serialized trial will satisfy the floor constraint; the actual guard correctly rejects these steps. Further work needs to account for this mismatch without widening acceptance tolerances.

## Reproduction and next evidence

With the separately acquired runtime/rig and retained parent study artifacts available, use a fresh output directory:

```powershell
.venv\Scripts\python.exe scripts/study_half_floor_pilot.py prepare reports/half-floor-pilot-new --parent reports/coupled-clip-sequence-v2 --diagnostic reports/coupled-geometry-diagnostic-v2/backpedal-02-block-1.json
.venv\Scripts\python.exe scripts/study_half_floor_pilot.py run reports/half-floor-pilot-new
```

Preparation freezes both variants and refuses to overwrite an existing attempt. Raw inputs, unsuccessful proposals, exported candidates and engine proof remain local. This is one selected development case, not held-out evidence, a new learned model, or animator approval. Replication across the remaining diagnosed actions/rigs is needed before generalizing the correction method. Scene/partner reliability, style/editing usability, developer review and independent animator cleanup measurements remain separate open release requirements. All fourteen release capabilities remain unapproved.
