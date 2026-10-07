# Trace the remaining hand crossings before continuing correction

The [grouped pair comparison](grouped-crossing-priority-v1.md) reduces the total recorded crossings, but aggregate counts do not explain where intersections persist. A saved-data comparison now covers every triangle-pair identity at all 1,673 original geometry samples in four complete, motion-passing exports from the same starting Job. No collision query or completed full-scene scan was repeated for this comparison.

| Export strategy | Maximum partner vertex depth, mm | Proper crossing records | Samples with proper crossings | Distinct crossing face pairs |
| --- | ---: | ---: | ---: | ---: |
| Depth-focused | 4.483570315 | 29,937 | 1,589 | 103 |
| Unguarded triangle support | 4.683168168 | 30,385 | 1,609 | 97 |
| Guarded triangle support | 4.693651534 | 30,044 | 1,588 | 97 |
| Grouped pair deficit | 4.691474461 | 29,757 | 1,580 | 99 |

Every recorded proper crossing in these four exports belongs to source face IDs 84–95 on each actor. Exact source index connectivity gives nineteen disconnected components, each with eight vertices and twelve faces. This particular component uses vertices 56–63; all eight have one positive skin influence of exactly unit weight on node 8, whose source name is `test_LeftHand`. This is a binding of the generated fixture, not an inferred anatomical region or a reason to omit any triangles from the complete geometry gate.

The grouped result has crossings at time zero through the sampled time 1.191666722 s. Its 99 distinct face pairs have sample-index episodes retained in the raw trajectory report. An episode is consecutive observed samples; its first/last times do not certify continuous collision duration. Compared with the depth-focused result, 27,687 crossing records match exactly, 2,250 disappear and 2,070 appear at other pair/sample identities. Against the preceding guarded result, 1,439 disappear and 1,152 appear. The lower total therefore includes crossings moving between faces, not just intersections being removed.

Both the depth-focused and grouped outputs are nondominated under the two recorded quantities, maximum partner vertex depth and crossing count. This comparison does not replace the existing depth-first selection rule or claim either output is optimal. The known geometry rejection remains in force for every export.

The original partner contact names vertex 59 on each actor at 0.5000000149011612 s, with a 20 micrometre position limit. It specifies neither a palm surface patch nor an opposing-normal constraint. Its meaning is an authored point correspondence. Satisfying it cannot certify a realistic high-five; topology and semantic review remain separate requirements. The remaining intersections are in the same rigidly weighted hand component as that vertex. Both clip endpoints are already editable, so a frozen endpoint is not the explanation.

## Explicit internal continuation

An experimental branch now starts from the grouped original-norm half step. The alternative depth-focused output and all original studies remain immutable. The existing internal-anchor constructor authenticates both actor payloads, every original decoded scalar/vector motion norm, contacts, source rates, static/reference bounds, control/trust limits and the unchanged 53 absolute storage choices. The represented step is 0.009999999995342682, within the original normalized trust of 0.02. A separate reader uses the original-context manual storage decoder, reproduces all observations and binds the known 4.691474461 mm / 29,757-crossing full-scene failure to identical export bytes.

Only the numeric anchor and its actor-file/control pins change. Every original non-anchor Job field remains exact. This is an internal solver seed, not an approved animation, a changed source selection, an engine export, or relaxation of the collision gate. Its derivatives and witnesses must be rebuilt rather than copied from the earlier pose.

## Fresh complete model at that pose

The new full-scene depth peak occurs at 0.3375 s, on actor B vertex 59 toward actor A. Add that time while retaining all eight prior guide times, including the earlier peak at 0.3385416716337204 s. The result has nine guide times; the original 1,707 native and 1,673 geometry clocks stay unchanged.

Every original central stencil is observed again at the moved pose: 90 controls, 180 complete perturbations, all 30,450 native vector norms and all native caps/scales. Each of those same poses also supplies both entire 152-vertex/228-triangle meshes at the nine guide times. There are no additional world perturbations solely for the full meshes. Every declared guide's source vertex and three ordered target corners exactly reconstruct from those complete point populations.

All crossing and positive contained-vertex witnesses are selected afresh. There are 1,274 rows: 140 complete crossing pairs contribute 1,260 ordered corner rows, and fourteen contained vertices contribute the remaining rows. All 180 native stencil vector populations differ from the prior pose; 114,784 entries in the complete native Jacobian change. Original cap/scale arrays remain exactly equal. This establishes a fresh local model rather than stale derivative reuse.

Complete affine guard coverage is rebuilt at the new pose and trust box. The 467,856 triangle/time pairs divide into 467,424 pairs separated by outward coordinate bounds throughout the represented affine box, 292 positively separated candidates supplying 2,628 corner guards, and 140 explicitly unresolved pairs. No subset of triangles or controls defines the coverage. These bounds concern exact arithmetic on the represented affine point model, not nonlinear skinning or exported collision freedom.

The separate model reader reconstructs the original-context anchor, all nine complete witness populations, all 180 native/material/full-skin stencils and every one of the 90 derivative columns. It also reproduces the 18 event-preserving and 72 uniform-increment equations, independently assembles the complete 467,856-pair guard partition and all guard values/columns, and verifies all 8,208 affine coordinate enclosures with exact rational arithmetic. The guard-builder and model-construction APIs are not called by this reader. Existing skin/norm/collision predicates are shared, so this is not independent collision arithmetic.

The fresh model capture and its reader solve zero proposals. The next experiment can use this authenticated pose-specific model with the existing hard native/depth/guard constraints, then evaluate the actual stored exports. No repeated full-scene scan is needed until a changed, eligible export exists.

Raw diagnostics, internal anchors, captures, stencils and readers remain in ignored `reports/`. Existing source APIs are unchanged, so validation here is the complete-data replay and publication byte/hash checks; no neural inference, training, installation, browser or production-anatomy query was performed. All fourteen release evidence arrays remain empty. Arbitrary-action quality, broad rig/object/partner coverage, engine integration, animator review and cleanup time still require their own evidence; the full-project goal remains active.
