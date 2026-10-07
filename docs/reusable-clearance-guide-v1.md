# Reusable partner clearance guidance and storage repair

`scripts/native_pair_clearance_guide.py` adds `linearize_pair_guide(problem, value, base_worlds, guide, ...)`. It builds fixed-axis skin-pair proposal guidance alongside the complete original native norm model. Actor names, selected skin vertices and time are explicit inputs; the hand IDs in this development experiment are not built into the API.

The guide contains `actor_a`, `vertices_a`, `actor_b`, `vertices_b`, `time_s`, `axis_world`, `clearance_m` and `scale_m`. Actors must be distinct existing participants, vertex lists unique and in range, the axis explicitly unit length, and the time already present exactly once in the complete native clock. The present resource limits are 96 complete controls and 4,096 selected pairs. Guide clearance is bounded to 0–0.1 m and scale to 1 micrometre–1 m. Values are not silently normalized or clocks extended.

Every selected A/B vertex pair is retained in A-outer/B-inner order. All original norm rows, caps/scales and control columns remain in the native model. Guide derivatives share its full perturbation worlds; no separate guide perturbation stencils are queried. Central differences are used where both samples fit. At a control-box boundary the guide uses the same recorded one-sided offset and its continuous origin. The decoded base and continuous origin remain distinct. The optional `stencil_sink(column, sign, sample)` receives copied complete controls, native vectors/caps/scales and guide points/gaps; a sink cannot mutate the calculation or replace the caller's world method.

The caller must supply authenticated freshly decoded base worlds and a suitable continuous problem, usually the verified stored-pair proxy. The builder does not authenticate supplied assets, solve a collision, infer contact semantics or approve an exported animation. Its residual/Jacobian can guide the existing hinge step, while original motion/contact/export/reference and geometry checks stay separate.

**107 focused local tests pass, zero skips**, including 20 new cases. Real placed meshes and unequal vertex groups reproduce the complete original norm/Jacobian and manually checked guide stencils. Boundary controls never query outside the box. Copies isolate observer mutations; observer failure leaves the caller's method intact. Invalid actors, IDs, units, clocks and oversized complete pair populations reject before world queries. The suite is registered once in Linux/Windows CI; hosted success is unverified.

The [previous verified internal seed](fresh-clearance-continuation-v1.md) is used for a fresh complete 90-column/180-central-stencil study through this public builder. All 30,450 original vector norms, 1,707 native samples, 1,673 geometry times, original rate/contact/static/reference/edit/trust limits and 45 absolute storage choices remain unchanged during the continuous comparison. Both guide variants use the same 64 hand pairs, 0.34375-s frame, fixed axis and 100-micrometre guide target. All eight directions/fractions are freshly exported and decoded:

| Guidance | Fraction | Decoded failures | Centered failures | Tested-frame depth in mm |
| --- | ---: | ---: | ---: | ---: |
| Original norms | 1 | 8 | 2 | 4.977786 |
| Original norms | 0.5 | 5 | 0 | 4.924126 |
| Original norms | 0.25 | 5 | 0 | 4.895895 |
| Original norms | 0.125 | 5 | 0 | 4.881417 |
| Event key preserved | 1 | 11 | 6 | 4.883050 |
| Event key preserved | 0.5 | 9 | 0 | 4.876069 |
| Event key preserved | 0.25 | 2 | 0 | 4.871687 |
| Event key preserved | 0.125 | 1 | 0 | 4.869267 |

Every export passes original contacts, reference budgets and represented trust/control bounds, and reduces actual projected hinge deficit. All eight fail decoded motion constraints. The smaller fractions pass the continuous proxy; a passing proxy is insufficient for an actual Float32 clip. No export is eligible for the study's declared full geometry selection, so its whole-clip geometry is unassessed. Independent manual stored-key reconstruction reproduces all 180 full native/point/gap stencils, all 90 native and pair-guide columns, event rows, strict ray prefixes, objectives, every actual export/world/reference/source-rate/contact result and tested-frame query without importing the public guide builder or step/ray/proxy/Job producers.

For a separate finite storage experiment, choose the fewest decoded native failures, then smallest actual hinge deficit among strict-box/reference/continuous-proxy passing guide-improving exports. This selects the event-key eighth step, with one failed row: A's node-8 wrist linear acceleration, frame 48, exceeds its original cap plus tolerance by 0.000126707249343 m/s². Continuous controls are held fixed. The existing balanced positional/angular search considers only permitted absolute negative/nearest/positive Float32 quaternion neighbors within the original one-ULP, 64-choice storage policy.

The start and 34 exported neighbors are saved. Neighbor `storage-0-33` adds actor A, node 6, native key 100, component 3, step -1; absolute choices increase from 45 to 46. All original decoded scalar constraints, all 30,450 vector norms and strict reference bounds then pass. No rate, contact or acceptance tolerance is enlarged. The repaired result's original normalized vector-norm maximum is negative. Its full geometry scan still fails: **4.889799077 mm**, **29,962 triangle records and 1,580 failed conditions**. The unchanged source assets stay selected.

A separate consumer replays every one of the 35 actual payload/world/scalar/vector/static/contact/reference observations. It independently reconstructs the full original positional/angular ancestor/key/component option population, round-robin prefix, absolute transitions, all merits and stable best eligible probed selection. The complete geometry archive is checked for transport fidelity using shared collision predicates. A first consumer reached all export checks, then failed on a stale archive-relative variable name during selection auditing; its script and failure note are retained. A fresh corrected consumer completes the whole replay. No producer or animation output is overwritten, and no model differences are rerun merely for publication.

A fresh genuine next Job copies this repaired internal seed. Every original non-anchor field stays exact; its anchor explicitly records the permitted added storage neighbor. Fresh Job reopening and the separate original-context manual export decoder reproduce controls, native worlds, original scalar/vector norms, contacts, static/reference bounds and payload audits. The known full geometry failure stays attached, geometry/quality approval remains false, and there is no library append or source selection. Both controls and stored pose changed, so another curve solve requires fresh derivatives at this 46-choice anchor.

These are generated-fixture development results, not broad action, production anatomy, continuous physics, engine, human rating or cleanup-time approval. All fourteen release evidence arrays remain empty; the full-project goal stays active.

Ignored immutable evidence SHA256 values:

- study: `d366f8b7274b1bda5b765e38edf6f9431340c968964ee9b494c430a6523ef8bf`
- study peer: `27991887c4bccd376441b3b1a91eedc809587ed6c130b23cc5170a0707083536`
- repair: `6253159bdb69c29397773d877f6d969e54b42eb3fe4304f5bbe59b0b307acd70`
- repair peer: `d5b4b8fc7a5c645fa4fd0b2ba48977d9adf545be75894f44f95733080783642d`
- anchor: `15164bf6bfd2cc3ce02dc87b750bcc3c15e68db0ed2ffb5472ccc4b4f71817f0`
