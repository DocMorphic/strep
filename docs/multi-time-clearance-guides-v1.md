# Multi-time partner guides and pose axes

Partner-clearance proposals can now use multiple explicit actor/skin-pair/time/axis descriptors. This addresses the previous single-frame experiment: its repaired clip still has 29,478 proper triangle crossings across 1,544 of 1,673 sampled geometry times, from the start to 1.186458349 s. Its maximum vertex depth is 4.969956705 mm at 0.341666667 s, rather than the original guide's 0.34375 s. A local guide improvement is insufficient evidence of whole-clip improvement.

`scripts/native_pair_clearance_guides.py` adds `linearize_pair_guides(problem, value, base_worlds, guides, ...)`. Each descriptor uses the existing eight-field [single-guide contract](reusable-clearance-guide-v1.md). Up to 64 descriptors and 4,096 total pair rows are accepted, across existing actors and native times. Descriptor order, A-outer/B-inner pair order, individual clearance/scale values, row offsets and point-coordinate offsets remain explicit. Exact duplicate descriptors reject rather than silently reweighting the objective. The complete point/control population and native Jacobian have declared resource budgets; no oversized subset is returned.

Every original norm, cap, scale, control and native-clock sample stays in the model. All guides share the same complete perturbation worlds. Central differences and boundary one-sided offsets use the original native stencil scheme, with each guide's continuous origin and units. Observers receive isolated copies. The caller still has to authenticate the decoded base and suitable continuous problem; the API does not approve an asset or infer an interaction.

`scripts/native_pair_guide_axis.py` adds `choose_axis(left, left_faces, right, right_faces, baseline_axis, ...)`. Both skin patches and their indexed triangles are explicit. It tests both signs of the baseline, every face normal, and every nonzero cross of unique indexed patch edges. Only exactly zero edge crosses are omitted. Each candidate scores every selected vertex pair using the declared clearance and scale. Ranking minimizes squared negative pair deficit, then maximizes minimum pair gap, with the first stable tie. All candidates and the selected index are recorded.

The present axis limits are 256 vertices per patch, 4,096 pair rows and 8,192 requested axis tests. An oversized complete family rejects before ranking; it is not truncated. All explicit triangles must be nondegenerate. This is a finite floating-point proposal heuristic. It does not prove an optimal separating plane, whole-mesh collision freedom, feasible controls, continuous physics or semantic contact correctness. Triangle topology, native motion limits and final geometry acceptance stay separate.

**169 distinct focused local tests pass with zero skips**: the existing 122, 28 multi-time cases, and 19 axis cases. Actual placed meshes at multiple native times and mixed units reproduce single-guide numerical results and every complete native stencil. Boundary differences, total budgets, malformed final descriptors, reversed actor order, observer mutation/failure, complete axis ranking and stable ties are covered. Both suites are registered once in Linux/Windows CI; hosted success is unverified. Existing single-guide APIs and clips remain intact.

## Complete retained-clip experiment

At the verified [48-choice seed](offline-clearance-job-v1.md), use the earliest stable maximum archived partner depth in each of four declared intervals, plus both endpoints and the exact contact event. The seven native times are 0, 0.234375, 0.3416666666666667, 0.5000000149011612, 0.7968750149011612, 1.140625 and 1.2000000476837158 s. All 448 explicit pairs are retained. The contact-time soft clearance is zero; other guides use 100 micrometres. This changes proposal targets only. Original contact limits, all 30,450 norms, 90 controls, 1,707 native samples, 1,673 geometry times and every original rate/reference/edit/trust/storage limit remain unchanged.

The fixed-axis experiment builds 180 complete central stencils at this new point. Every proposed fraction is exported and decoded. A separate manual consumer exactly reproduces all complete native/point/gap stencils, all native and 448-pair derivative columns, event rows, strict ray prefixes, guide losses, export payloads/worlds/vector norms, contact/static/reference observations and seven-frame geometry queries. No candidate passes decoded motion, so no full geometry scan is selected.

The next comparison rebuilds a finite pose-axis family independently at each of the same seven frames. All seven selected directions change. The baseline guide penalty changes from 224.385068561 to 15.678587816 because the objective's axes change; this is not a motion-quality improvement. Both runs start from the same controls, stored choices and original constraints. The second run reuses all 180 independently verified complete native/point stencils at that identical point, reprojects every gap and all 90 guide columns, and makes zero new native perturbation queries. It retains all frames, pairs and original native columns. No derivatives from an earlier pose are reused.

| Variant | Fraction | Fixed-axis native failures | Fixed-axis seven-frame depth, mm | Pose-axis native failures | Pose-axis seven-frame depth, mm |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original norms | 1 | 19 | 5.467451 | 18 | 5.324474 |
| Original norms | 0.5 | 1 | 5.230848 | 6 | 5.102497 |
| Original norms | 0.25 | 5 | 5.113280 | 4 | 4.990910 |
| Original norms | 0.125 | 4 | 5.045103 | 1 | 4.956790 |
| Event key preserved | 1 | 10 | 5.305323 | 17 | 5.294436 |
| Event key preserved | 0.5 | 1 | 5.137569 | 5 | 5.087561 |
| Event key preserved | 0.25 | 2 | 5.053741 | 10 | 4.983456 |
| Event key preserved | 0.125 | 2 | 5.011851 | 5 | 4.954198 |

Every export passes reference/trust bounds and reduces its own actual guide penalty. The fixed-axis full original-norm step fails one contact; all other contacts pass. In both comparisons the smaller fractions pass the continuous proxy, while actual decoded motion still fails. All pose-axis exports pass contacts. The two eighth steps improve the seven-frame depth diagnostic versus the seed, but retain native failures and triangle intersections; no full-clip geometry improvement is established.

A separate pose-axis consumer reconstructs every full triangle/edge axis family, both signs, all pair scores and stable selection without importing the axis chooser. It verifies exact transport of all original cached norm/point stencils and native columns, independently recomputes all reprojected gaps and guide columns, and replays event rows, strict rays, every actual export and all seven-frame queries through the legitimate original manual decoder. Both consumers leave full-geometry transport false because no candidate qualifies. Shared collision predicates and the optimizer are not independently certified.

The APIs are backend proposal components. They do not add a multi-guide Studio control or replace the existing single-guide command. All results concern generated fixtures. Original assets stay selected, all fourteen release evidence arrays remain empty, and the full-project goal stays active.
