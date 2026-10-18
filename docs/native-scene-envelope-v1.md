# Native pose conditioning with authored scene guidance

Development experiment, 2026-10-18. This measures a combined generation path;
it does not approve a motion, action family or release capability.

The [previous text-only envelope experiment](scene-motion-envelope-v1.md)
missed the intended hand contacts by roughly 0.8–1 metre. Strep already has a
native pose-conditioning path: earlier high-five runs place individual palms
near their targets but fail actual partner contact and collision checks.
This experiment combines that existing conditioning with full authored scene
guidance, rather than presenting native conditioning as a new capability.

## Frozen inputs and comparison

Both actors retain their original frame-60 native pose constraints, prompts,
120-frame clocks and seeds 77/88. The constraints compile exactly to the
previous generation records. Before new sampling, motion ceilings are frozen
at exact maxima across each unchanged native-conditioned CUDA producer,
independent raw and decoded GLB observations. There is no multiplier, added
headroom or physical epsilon. Earlier text-only policies and failures remain
unchanged; these native controls are a separate, explicitly bound reference.

The box source reference misses its original grip targets by over 0.6 m.
Preparation records that failure and rejects those poses as native grip
constraints. No target, object trajectory or action scope is changed. The box
still requires a valid fitted reference before this conditioning path is
appropriate. The high-five source's known overlap remains unapproved;
diagnostic sampling does not waive the strict source preflight.

The unchanged checkpoint generates six clips: native constraints alone,
native constraints plus energy guidance, and native constraints plus retained
guidance, for each actor. All use 100 steps, CFG 2/2, no postprocessing,
base timesteps 0/10/20/30/40 and a 0.01 prediction-space L2 budget. Both new
native controls reproduce the old native-conditioned raw arrays exactly.

| Actor | Maximum fixed-reference contact error, native → energy | Native maximum floor depth | Retained changes |
|---|---:|---:|---|
| A, seed 77 | 22.455 → 20.391 mm | 10.430 mm | None; exact native raw arrays and GLB |
| B, seed 88 | 19.259 → 17.327 mm | 8.328 mm | None; exact native raw arrays and GLB |

Energy guidance accepts five local steps per actor, but both finished clips
regress physical observations and exceed the frozen native motion ceilings.
Retained guidance rejects all 30 tested rays. **Every rejected ray worsens
floor observations**; some also worsen palm normal or tangent observations.
None is rejected solely for motion preservation. Repeating the same late-step
fractions is therefore not the next action.

## Actual generated partners

Individual fixed-reference contact screens pass for all six clips. These
screens use the supplied source partner track; they do not prove contact
between the two independently generated actors. A separate paired evaluation
uses both generated actors, the original placements and all three original
contact IDs. It retains the original 30 mm point tolerance.

| Pair condition | Actual palm gap | Maximum partner depth at contact frame | Vertices above existing 5 mm diagnostic |
|---|---:|---:|---:|
| Native only | 33.282 mm | 13.483 mm | 180 |
| Native plus energy | 30.300 mm | 13.647 mm | 184 |
| Native plus retained | 33.282 mm | 13.483 mm | 180 |

All three pairs fail the intended palm contact. The energy-guided pair gets
closer while increasing body overlap. Opposing-normal errors remain about
18.14 degrees; actor A's world-normal error remains about 23.41 degrees,
above the existing provisional 15-degree diagnostics. These screens are not
new release thresholds or animator approval.

Raw and independently decoded saved-file observations agree on these failures.
At the original contact frame 60, both directions query all 18,056 vertices
against the other body's 36,108 triangles, using conservative broad-phase
pruning and exact signed-distance batches of at most 32 points. This frame
is a failure witness. **The other 119 partner frames are unchecked in this
new study**; no complete-scene clearance is claimed. Edge-only, continuous,
self-collision, forces, semantics, engine and human checks remain open.

## Verification and next action

Independent model-free replay checks all six complete exports across
13,000,320 vertex/frame pairs, preserving all eight weights/indices and all
faces. Maximum skin-component fidelity error is 6.195e-7 m. All 40 callback
archives and 30 ray comparisons replay exactly; complete original metric rows
and losslessly normalized physical scalar values remain present. Guidance,
decoder, sparse Torch skinning and Torch itself are excluded from this replay.
Existing NumPy geometry libraries are shared; this is not independent physics.

Public source is unchanged from the 87-case suite that passes locally and on
both hosted operating systems at `b543f9971d790fed2f74d38d8dadef0eb0d4a173`
([focused run 39123364217](https://github.com/DocMorphic/strep/actions/runs/39123364217)).
Those source bindings are requalified rather than rerunning identical tests.

All jobs use serial worker locks and the unchanged 600 MiB free-memory reserve.
Preparation completes in 41.766 s with a 1,347,280,896-byte peak under its
2 GiB cap. The model completes in 108.375 s with a 1,805,307,904-byte peak
under its 3 GiB cap. Model-free export replay completes in 58.250 s with
114,700,288 bytes; paired witness checks complete in 133.985 s with
287,662,080 bytes, both under 512 MiB caps.

Local evidence is retained under `reports/native-scene-envelope-prepare-v1`,
`reports/native-scene-envelope-pilot-v1`,
`reports/native-scene-envelope-replay-v1` and
`reports/native-scene-envelope-pair-witness-v1`.

The bottleneck is physical floor/orientation/partner geometry. The current
authored scene energy has **no partner collision term**, so closer fixed-point
targets cannot establish a solved interaction. Next work must address coherent,
collision-safe source/contact poses and partner-aware complete-output correction.
No changed output is adopted. The qualified reference, Studio selection,
checkpoint and release contract remain unchanged. General actions, meaningful
style controls, editing, rig transfer, transitions, engine/offline packaging
and actual human review/cleanup remain part of the same active project goal.

The checkpoint `reports/native-scene-envelope-progress-v1` verifies 7,860
current source, archive, checkpoint, cache, asset, data and resource bindings,
and binds the prior whole-goal receipt. Its streaming audit completes in
59.313 seconds with an 80,191,488-byte peak under the 512 MiB cap. Only goal
line 3 and the two permitted release-matrix progress fields change; all 14
capabilities and all original release requirements remain unapproved and intact.
