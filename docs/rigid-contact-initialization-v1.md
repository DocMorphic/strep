# Rigid hand-shape initialization screen

The previous preventive repair kept 220 existing contact-pose crossings and
10.107 mm maximum vertex penetration. Before another local rig solve, test
whether the same surface marker and hand shape give a useful contact geometry
under a broader orientation search.

## Protocol

Use the independently decoded pair from `reports/contact-pair-prevention-v1`.
Bind both source clips, original scene/contact metadata and the exact selected
hand regions: 2,872 vertices and 5,717 incident triangles per actor, using the
complete skin weights. Both contacts are on `LeftHand`, vertex 14712. The scene
still labels this geometry-derived marker `anatomical_review_pending`.

Rigidly place each marker at its unchanged authored target (1 mm pair gap),
align its actual area-weighted patch normal exactly to the target normal, and
hold actor A's twist at zero. Sweep actor B through 0..345 degrees at 15-degree
intervals. Exact normal alignment is a subset of the authored 20-degree normal
allowance; these 24 samples do not exhaust that allowance or continuous twist.

Run this separately for the source animated skin and the rig's node-default
rest skin. The rest condition is a distinct initialization diagnostic, not a
repair that preserves original animation edit limits. No supplied mesh,
weights or connectivity are altered. Rigid transforms move the full source
geometry so containment can use the original closed, winding-consistent
partner surface. Test crossings between both selected hand regions and test
every selected hand vertex against the complete closed partner mesh.

A sampled hand screen passes only with zero proper/uncertain pairs, no
degenerate faces and both directional maximum vertex depths at most 1e-8 m.
This remains a floating-point discrete diagnostic: no exact collision
certificate, self-collision/whole-body approval, joint reachability, original
angle-budget compliance, temporal validity or animation quality is inferred.
In particular, transformed complete bodies can affect containment depths; these
rigid placements are not rig-feasible character configurations.

## Results

| Condition | Screens passing | Fewest crossings | Twist at fewest crossings | Depth at that twist | Lowest depth at any twist |
| --- | ---: | ---: | ---: | ---: | ---: |
| Animated hand shape | 0/24 | 188 | 270 degrees | 8.584371 mm | 5.671466 mm at 285 degrees |
| Rest hand shape | 0/24 | 284 | 15 degrees | 20.394468 mm | 8.674410 mm at 90 degrees |

Every sample retains the authored marker contact. Proper crossing counts span
188..1,072 (animated) and 284..846 (rest). The stored `best` row and preview
geometry rank screen pass first, then intersection/uncertainty count, then
maximum depth. This is a diagnostic ranking, not a quality or rig selection.
No GLB is exported and no Studio selection changes.

The separate hash-bound inspections render the actual selected hand mesh from
three orthographic views per actor, marking the anchor and normal. Both images
were inspected. With the animated shape, 54 vertices lie within 20 mm of each
marker; maximum outward tangent-plane heights are 5.147981 and 5.135570 mm.
For the rest shape, 52 vertices lie within 20 mm, with maximum height 7.761854 mm
for both actors. This is surface relief relative to the local marker plane,
not measured penetration or a proof that the authored target is impossible.

## Decision

No collision-free initializer was found in this finite exact-normal sweep.
Changing twist or replacing the fingers with this rest shape alone is not a
qualified fix. The observed local surface relief motivates a separate
contact-region authoring experiment: select physically compatible points
within an explicit palm region, inspect the chosen points, and fit the rig
while checking the complete meshes. This would be a new authored condition,
not a silent movement of the old marker or a relaxed result for the old study.
Retain the original benchmark and all original failures. Joint reachability,
full contact interval, floor/body collision, motion rates and human review
remain requirements before any animation can be accepted.

## Reproduction and provenance

```powershell
.venv/Scripts/python.exe scripts/study_rigid_contact_initialization.py reports/contact-pair-prevention-v1 reports/paired-edit-jobs/relinearized-v2 reports/<fresh-animated> --contact palm-to-palm
.venv/Scripts/python.exe scripts/study_rigid_contact_initialization.py reports/contact-pair-prevention-v1 reports/paired-edit-jobs/relinearized-v2 reports/<fresh-rest> --contact palm-to-palm --pose-source rest
.venv/Scripts/python.exe scripts/inspect_rigid_contact_geometry.py reports/<completed-study> reports/<fresh-inspection>
```

Each study rehashes 3,528 inputs, 81 archived methods and 27 outputs. All were
rechecked. The animated study archive precedes the optional rest-mode driver
change; use that archived driver for exact historical reproduction. The rest
archive matches current methods. Result SHA-256 values:

- Animated: `120950c6fb5b8ab3715b681607dc6b7256ade8f08e7a073d1e83d5f82a846ebc`.
- Rest: `d9098114967d0ef7d05059e009d779cf0edbca6d89f11339dfd4c0cb9fd0941f`.

Local inspections are `reports/rigid-contact-inspection-v1/hands.png` and
`reports/rigid-rest-contact-inspection-v1/hands.png`, with input and renderer
hashes in each `inspection.json`. Approximate painter-order rendering is for
inspection; numerical geometry reports remain authoritative. Source geometry
and reports remain excluded from Git.

Six new tests cover shape/winding preservation, aligned and opposite normals,
anchor-centered twist and angle wrapping, invalid input rejection, and the
separation of hand screening from rig/quality approval. All 1,028 model-free
source tests pass. Both study workers and the test worker are terminal. No
training, dependency/model/data acquisition or reserved held-out use occurred.
