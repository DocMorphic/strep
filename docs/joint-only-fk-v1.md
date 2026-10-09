# Joint-only native pose evaluation

The native pose solver previously skinned the complete mesh in calls that immediately discarded the vertices and used only rotations or joint positions. `PoseProblem.fk(..., vertices=False)` now returns the same three pose tensors and `None` for vertices. The default continues to skin the complete mesh. Sparse derivative and vector assembly use the joint-only path before explicitly skinning their selected dependencies; coupled neighbor-position assembly also skips its discarded mesh.

Full geometry still selects extrema from every original vertex and retains every tied dependency. Collision populations, reference clocks, authored contacts, eight skin weights, physical tolerances, saved-motion checks and acceptance rules are unchanged. This removes redundant computation; it does not relax the motion problem or repair an animation by itself.

## Validation on 2026-10-09

351 checks passed across 13 CPU-native solver modules, including exact native joint/rotation derivative parity, a mesh-free joint call, full-skin selection instrumentation, dense versus sparse derivatives across box/sphere/cylinder geometry, coupled neighbors, saved representations and interval continuation histories. The guarded test worker exited successfully with sampled peak process-tree RSS of 638,885,888 bytes. Independent replay checked its 123 resource observations.

Two separate guarded workers evaluated the original saved box-lift frames 78–80 with the 77-joint, 18,056-vertex SOMA skin and derivative row chunk 4. The comparison mode forces full skinning back on for the newly optional calls; every other operation uses the same bound inputs and implementation. After three warmup calls, 40 joint-call timings were collected in each process. The complete coupled pair was measured once; vector records were then retrieved from its cached assembly.

| Measurement | Discarded full skin | Joint-only |
| --- | ---: | ---: |
| Median joint call | 11.620 ms | 1.654 ms |
| Complete coupled pair | 8.888 s | 8.150 s |
| Sampled process-tree peak RSS | 712,634,368 bytes | 663,814,144 bytes |

All eight saved numerical outputs are bitwise identical: 1,068 inequality values, their 1,068 × 525 Jacobian, and the offsets, Jacobian, limits, scales, row indices and distance flags for 2,265 vector records. Both workers exited successfully under unchanged RAM/RSS/time guards; independent replay checked 57 and 55 resource samples. Local evidence, bound worker source and copied method files are under ignored `reports/joint-only-fk-v1/`.

The isolated joint call is about seven times faster in this sample. The complete coupled computation shows a much smaller difference. End-of-work worker RSS is nearly unchanged (697,679,872 versus 697,241,600 bytes); sampling can miss short peaks, and the allocator retains memory. These sequential measurements are descriptive, not repeated end-to-end optimizer benchmarks or a reliable estimate of future peak RAM. They do not justify reducing the separate 2 GiB estimate used to admit a full contact continuation.

## Remaining work

The retained contact interval remains byte-for-byte unchanged; its stage-2 result SHA-256 is `58ce89c8d6698560bf5c4a792e6c0f2ef10fea7de68a10ed6c9a555dddd45df9`. Complete physical and keyed passes remain 0/62. No corrected clip, new generation, training, engine import, human score or release approval was produced. All fourteen release capabilities remain unapproved. Resume the retained interval when its existing resource profile admits it, and continue broad action, scene/partner, rig, editing/style, engine and actual developer-review validation.
