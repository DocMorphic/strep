# Explicit skin conditioning and original-reference engine fidelity

The corrected crawl passes sampled Godot authoring import after a separate skin-weight export. Seven existing development actions also pass original-reference skin fidelity after that export. Four raw actions still fail floor checks. This is import and numerical evidence, not realistic-motion or release approval.

## Method

Use the existing `native_skin_export.run` to produce a derivative GLB and retain `original.glb`. Its checked uint16 weight grid changes weights only: original binary payload, animation, mesh positions, binds and other scene data remain intact. Originals are never overwritten or automatically selected for replacement.

Run the existing Godot 4.7.2 `native-authoring` capture on the explicitly bound derivative. Replay the actual pose, skin, topology and geometry observations. The new `audit_conditioned_skin_fidelity.run` then compares every imported vertex, in original mesh order, against the immutable original at every declared capture time. It also measures the native derivative against that original. A derivative-relative match alone cannot establish original fidelity. The existing 0.1-mm skin tolerance is unchanged.

This uses headless authoring seeks and CPU skin observations. GPU rendering, live playback, physics, continuous-time behavior and human motion quality remain unverified. Existing development seed-77 actions and rig transfers are reused; no new generation, training or reserved held-out data is used.

## Corrected crawl

The unchanged corrected GLB first failed imported skin fidelity at 0.170879 mm despite passing pose and floor checks. The separate conditioned export then passes all sampled import conditions at all 2,017 capture times. Maximum imported error against the original corrected mesh is 0.002642 mm; native derivative error is 0.002546 mm. The original correction and its motion caps remain unchanged.

The first conditioned wrapper failed after its engine capture completed because it called a nonexistent scene API. That failed wrapper and its completed subordinate capture are retained. A fresh replay uses those observations without rerunning the engine; original-reference fidelity and conditioned native floor checks pass.

## Seven-action development comparison

All 1,020 original keys are retained. Error values below compare imported skin with the original, rather than merely with the conditioned export.

| Action | Samples | Previous maximum error (mm) | Conditioned maximum error (mm) | Raw floor screen |
| --- | ---: | ---: | ---: | --- |
| Jump and land | 120 | 0.144323 | 0.002469 | Pass |
| Crawl | 120 | 0.173554 | 0.002659 | Fail |
| Dance | 150 | 0.099366 | 0.001644 | Pass |
| Wave | 120 | 0.096257 | 0.001341 | Pass |
| Kick | 120 | 0.100121 | 0.002150 | Fail |
| Get up | 180 | 0.127009 | 0.002945 | Fail |
| Run, roll and stand | 210 | 0.692680 | 0.005803 | Fail |

All seven pose and original-reference skin comparisons pass. The same four floor failures remain: peak depths are 263.015, 49.727, 662.040 and 978.276 mm respectively. Previous selected-joint rotation-speed diagnostic failures remain recorded and were not reexecuted; those authored diagnostic caps are not anatomical calibration.

Fresh capture replay reproduces every recorded engine observation and original-fidelity array for all seven cases. The public auditor also checks the dense corrected crawl. This replay executes no additional engine jobs.

## Verification and provenance

Fifty-five related Python tests pass, including six new fidelity tests that reject missing vertices, nonfinite data, changed animation, invalid clocks and original-reference drift. Resource admission and execution limits are unchanged. Recorded resource-policy replay passes for the complete studies: seven-action capture 44.531 s/62 observations; full capture/fidelity replay 92.359 s/109 observations; dense crawl fidelity replay 42.563 s/60 observations.

Private immutable evidence lives under ignored `reports/crawl-passing-native-engine-v1`, `crawl-conditioned-export-v1`, `crawl-conditioned-engine-v1`, `crawl-conditioned-fidelity-replay-v1`, `kenney-conditioned-breadth-v1` and `conditioned-breadth-replay-v1`. The initial failed validation command named a nonexistent test module; its failure is retained separately from the successful 55-test run.

Hosted review-packet tests revealed that clean CI checkouts lacked Three.js. Both source and focused contact/rig workflows now install the tracked viewer lockfile with `npm ci --ignore-scripts`. A fresh local prefix successfully installs that exact lockfile offline and contains both Three.js build files and the GLTF loader. One previous focused Windows shard was canceled; that cancellation is not diagnosed by the dependency fix. New hosted outcomes remain required.

The next integration is an explicit conditioned-export option with original-reference receipts in the authoring/game-package pipeline. Floor correction, actual playback, scene/partner interaction, style/editing, held-out evaluation and developer/independent cleanup reviews remain required by the single project-wide goal. All fourteen capability approvals and release gates remain unchanged.
