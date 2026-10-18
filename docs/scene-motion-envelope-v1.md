# Explicit motion envelopes for scene-guided authoring

Development component, 2026-10-18. All original release requirements and
failed experiment results remain intact; no capability is approved.

The previous rejection ledger found that high-five proposals were locally
blocked only by source speed/acceleration preservation. Requiring every motion
value to decrease would prohibit ordinary timing changes and faster character
styles. Physical contact and penetration requirements need separate treatment.

`scripts/scene_motion_envelope.py` adds a scene-bound authoring policy. All four
complete skin/joint speed/acceleration tracks require explicit units and
ceilings. A ceiling may be one number for the whole clip or one value for every
original interval. The policy binds the exact compiled scene, reference metric
file, 30 fps clock and frame count. Missing tracks, changed populations,
incorrect units, negative/nonfinite limits and physical-metric overrides reject.

The policy comparison maps every original motion scalar to its positive
budget excess and passes every floor/object/contact/orientation/degeneracy
array through unchanged. The old strict source comparison, original raw
values, complete policy and separate absolute budget assessment remain visible.
Reducing an already failed bound does not make that bound pass. A usable final
asset must still pass every applicable motion and physical requirement.
No physical epsilon or automatic agility/strength/fitness mapping is added.
These are explicit game-author limits, not measured human capacities.

The standalone command creates a fresh, editable template:

```text
python scripts/scene_motion_envelope.py context.json reference-metrics.npz motion-policy.json
```

The template uses each original **whole-clip maximum**, with no multiplier or
extra headroom. It permits redistribution in time while preserving those global
ceilings. Existing files are never overwritten. Editing a template creates a
new author policy that must be frozen before generation; it cannot reinterpret
a previous failed trial or change the project's fixed release criteria.

The 87 local source checks pass: 20 new envelope tests plus the existing 67.
All 87 also pass on hosted Windows and Ubuntu at
`b543f9971d790fed2f74d38d8dadef0eb0d4a173`
([focused run 39123364217](https://github.com/DocMorphic/strep/actions/runs/39123364217)).
Tests cover permitted temporal redistribution, unchanged physical rows, tiny
over-cap violations, complete interval ceilings, visible failed references,
source binding/ownership and reserved-name protection, invalid/omitted data,
and the actual exclusive-output CLI. The original hook, scene compiler, full
skin/gradient/metric and independent observation regressions stay included.

## Frozen experiment and actual samples

Preparation v1 uses the original producer's maxima, like the public CLI. It is
preserved and **was never sampled**. Before new sampling, separate preparation
v2 freezes each ceiling at the maximum across the unchanged ordinary producer,
independent raw and decoded GLB observations. Every original representation
therefore passes its own ceiling. This includes the recorded numerical
differences between required representations, without a multiplier, added
tolerance or headroom. Each source file is hash-bound in the preparation
receipt. This separate policy does not change a previous failed experiment.

All physical scalar values remain exact. The comparison makes owned Float64
copies, including lossless conversion of Float32 observations; input dtype and
byte encoding need not match. Every original motion scalar maps to one budget
excess. Raw arrays, policies and strict source comparisons remain available.

The unchanged checkpoint then generated **six actual clips**, pairing ordinary
and envelope-guided sampling for the original box actor and both high-five
actors. The prompts and seeds are unchanged: box A, 180 frames, seed 77;
high-five A/B, 120 frames, seeds 77/88. Each uses 100 steps, CFG 2/2, no
postprocessing, base timesteps 0/10/20/30/40 and a 0.01 prediction-space L2
budget. Every fresh ordinary raw array exactly reproduces the previous ordinary
sample. All original authored geometry, contacts and clocks remain in use.

| Case | Accepted local steps | Maximum contact error, ordinary → guided | Finished result |
|---|---:|---:|---|
| Box A | 0/5 | 824.015 → 824.015 mm | Exact ordinary raw arrays and GLB; intended grip still fails |
| High-five A | 5/5 | 991.971 → 981.104 mm | Physical metrics regress and motion ceilings fail |
| High-five B | 5/5 | 932.516 → 928.321 mm | Physical metrics regress and motion ceilings fail |

The original point tolerance is 30 mm. **None of the six clips satisfies the
intended contacts, and no changed clip is adopted.** Retaining a local proposal
does not guarantee that subsequent denoising preserves it. Motion ceilings are
separate from contact and penetration requirements; all remain mandatory.
The model job completed in 117.562 seconds with a 1,781,878,784-byte process-tree
peak under its 3 GiB cap and unchanged 600 MiB free-memory reserve.

Local evidence: `reports/scene-motion-envelope-tests-v1`,
`reports/scene-motion-envelope-prepare-v1`,
`reports/scene-motion-envelope-prepare-v2` and
`reports/scene-motion-envelope-pilot-v1`.

## Independent exported-file and local-decision replay

`reports/scene-motion-envelope-replay-v2` checks all six complete saved GLBs
and independent raw observations across **15,167,040 vertex/frame pairs**,
preserving all eight skin influences and 36,108 faces. Maximum saved skin
component error is 5.740e-7 m. The existing NumPy geometry libraries are shared;
Torch, guidance, decoder and sparse Torch skinning are excluded.

Both high-five edits fail physical nonregression and the frozen motion
ceilings in **both** independent raw and saved-file checks. Box raw arrays and
GLBs remain exactly ordinary. All six still fail the original point contacts.
Every one of the 40 archived callback feature/metric files and 25 local ray
comparisons replays exactly: 15 box rejects and ten local high-five accepts.
The complete local and final populations remain separate, without an epsilon.
The replay finishes in 66.500 seconds with a 116,686,848-byte peak under its
512 MiB cap and unchanged 600 MiB reserve.

The first replay stopped because its verification assertion compared raw
Float32 bytes to normalized Float64 bytes. It is preserved as a failed check;
the fresh v2 replay verifies losslessly normalized bytes and complete scalar
values. No motion file, policy, physical tolerance or earlier result changed.

The next direction is to connect the **existing** native positional/temporal
conditioning path to these complete authored skin-contact observations, with
final complete output checks authoritative. Repeated small
nudges late in sampling have not solved these interactions. Contacts, full
primitive/partner triangles, timing semantics, calibrated style/capability
response, rig transfer, engines and genuine review/cleanup remain required
under the same entire-project goal.

The completed checkpoint is `reports/scene-motion-envelope-progress-v1`.
Its streaming audit verifies 7,837 current source, archive, checkpoint, cache,
asset, data and resource bindings plus the prior whole-goal receipt. It finishes
in 54.156 seconds with a 66,961,408-byte peak under its 512 MiB cap. The fixed
release contract is unchanged except for goal line 3 and the two permitted
progress fields. All 14 capabilities remain unapproved; the single entire-project
goal remains active.
