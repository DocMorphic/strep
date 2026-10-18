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
Tests cover permitted temporal redistribution, unchanged physical rows, tiny
over-cap violations, complete interval ceilings, visible failed references,
source binding/ownership and reserved-name protection, invalid/omitted data,
and the actual exclusive-output CLI. The original hook, scene compiler, full
skin/gradient/metric and independent observation regressions stay included.

The separately versioned preparation study freezes three policies from the
unchanged ordinary box/high-five actor samples before new sampling. It verifies
every cap equals the corresponding original global peak exactly, all physical
rows remain byte-identical and every original motion row maps to a budget
excess. No earlier source sample or comparison is rewritten. Local evidence:
`reports/scene-motion-envelope-tests-v1` and
`reports/scene-motion-envelope-prepare-v1`.

Next execute matched sampling with the frozen envelopes, retaining the strict
source and envelope comparisons side by side. Per-call retention, final raw
checks and independent saved-file checks remain distinct. Contacts, full
primitive/partner triangles, timing semantics, calibrated style/capability
response, rig transfer, engines and genuine review/cleanup remain required
under the same entire-project goal.
