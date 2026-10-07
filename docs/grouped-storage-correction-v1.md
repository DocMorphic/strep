# A bounded storage correction removes three acceleration failures

The [grouped export comparison](grouped-continuation-comparison-v1.md) left an event-preserving half-step that passed its centered continuous proxy, reference bounds, point contact and actual positive-separation guards, but failed three stored angular-acceleration rows. Those rows belong to actor B nodes 6/7/8 at 0.45 seconds. The subsequent [empirical response guide](observed-secant-model-v1.md) did not reliably improve acceptance. This experiment keeps the half-step's numeric controls fixed and tests the existing bounded storage search instead.

`scripts/native_balanced_rate_storage_search.py` constructs options from every original failed positional/angular rate stencil and its permitted rotation ancestors. It retains all bracketing editable native keys and all quaternion components. Existing corrections can be restored or replaced; new corrections choose one neighboring Float32 value. Choices are absolute relative to nearest storage, so repeated searches cannot accumulate extra steps. Actor/joint groups are interleaved, and every declared option remains in the saved plan even when the finite probe prefix stops earlier.

The original authoring policy permits at most 64 distinct component corrections. The starting export uses 53. This study declares four stages with at most 64 probes per stage, fixed continuous controls, unchanged source/native-key clocks, and every original motion/contact/reference limit. Each evaluated probe is actually exported, audited, independently decoded and retained. Best improvement uses maximum positive native residual, then squared positive residual, with stable ties; early exit is permitted only when every original native condition passes.

## Measured result

The complete first-stage plan has 144 absolute options. Eight neighbors are evaluated. The starting export and the first seven neighbors each fail three native rows; the eighth passes all 30,450 original vector norms and all scalar motion/contact checks across the complete 1,707-sample native clock. Every probe also passes the original reference bounds. No derivative stencil, numeric control change or tolerance relaxation is used.

The successful choice adds one negative neighboring Float32 adjustment at actor B node 6, rotation key 108, quaternion component 2. It brings the correction list to 54, within the original 64-choice policy. Comparing actual exported channels against the starting export finds exactly one changed quaternion component; every other payload component and every native clock stays exact. This demonstrates a storage change capable of removing this specific rejection at fixed controls. It does not establish that all observed defects are purely rounding errors, or that one-component repairs generalize to other actions, rigs or clocks.

All 2,628 actual positive-separation guards pass. Complete nine-frame mesh queries retain 140 proper crossing records. The full original 1,673-sample scene scan records approximately 4.680554928 mm maximum partner vertex depth, 29,642 proper crossing records, zero over-limit vertices and 1,575 failed samples. It still fails the original collision gate.

| Motion-passing branch | Full maximum partner depth, mm | Proper crossings | Failed samples |
| --- | ---: | ---: | ---: |
| Previous grouped event quarter | 4.686034583 | 29,702 | 1,577 |
| Empirical-guide event eighth | 4.688772867 | 29,715 | 1,578 |
| Storage-corrected grouped event half | 4.680554928 | 29,642 | 1,575 |

The repaired half improves these measurements over both preceding grouped selections. The older depth-focused branch remains lower in depth at 4.483570315 mm, with more crossings at 29,937. None is collision-approved. Crossing counts alone do not demonstrate better anatomy, contact semantics or animator quality.

## Replay and failed-run preservation

The initial driver completed the entire native search and final nine-frame checks, then failed during full-scene logging because the progress callback supplied a duplicate `status` argument. Its failed driver, all nine exported probe pairs, search/plan records and partial scene archive remain immutable. A separately declared continuation reuses those exact bytes and completed search without repeating any storage probe or actor export. It decodes the final export again and creates a fresh complete scene archive after the original process's terminal error. The partial archive is retained as failed evidence, not relabeled complete.

The separate reader uses the original legitimate replay context, manually decodes all absolute storage choices, and verifies every complete probe's native vectors, scalar conditions, caps/scales, clocks, authoring and reference bounds. It reconstructs all 144 options from original rate stencils and permitted ancestors, actor/joint interleaving, the tested eight-option prefix, best-improvement ordering and early exit. It proves exactly one actual payload component changed, reconstructs all final nine-frame collision/containment queries and all 2,628 guards, and verifies complete scene-archive transport. It does not call the storage-search or storage-export producer APIs. Shared motion and geometry predicates remain in use; this is not independent collision arithmetic, continuous collision certification, or an exhaustive feasibility proof.

Existing public source APIs are unchanged. Validation consists of the complete actual-export experiment, separate replay, provenance/hash checks and exact failed-run preservation; no expensive study is rerun merely for publication. Raw outputs and readers remain in ignored `reports/`.

Next use this verified motion-passing result to investigate remaining full-mesh intersections. If its controls/storage become a new internal linearization anchor, that must be an explicit unapproved branch with newly authenticated native/material/guard models; this experiment makes no such promotion and reuses no derivative at the changed pose. Original assets remain selected, all fourteen release evidence arrays remain empty, and the full-project goal stays active. No arbitrary-action semantics, production anatomy, engine, animator review, cleanup-time or release approval is claimed. Hosted CI success is unverified.
