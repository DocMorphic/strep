# Whole-component correction improves its guide but leaves more crossings

The [fresh recovery model](recovery-component-model-v1.md) provides ten complete component groups at an independently verified, motion-passing internal anchor. A new correction step uses those groups without pretending their 64 vertex pairs are nine-row triangle groups. The actual stored-export trial is complete: the selected export passes the original motion, contact, reference and positive-separation checks, but still fails the full mesh gate and has more proper crossings than its starting anchor. It remains unapproved.

## Objective and hard local bounds

`scripts/native_material_component_support_step.py` minimizes the sum of complete component/time maximum fixed-axis deficits, with one nonnegative slack per group. Every ordered left/right vertex pair constrains that slack. Unequal component sizes contribute once each; their individual vertex rows do not add objective weight. Group metadata requires distinct ordered original vertex IDs, their complete Cartesian product, exact typed witness identities, a finite time and unit world axis. Every component row must occur exactly once. Duplicate groups, including the same pair with actors reversed, are rejected. The caller still authenticates complete source topology, target material descriptors and same-point derivatives; metadata alone is not proof of geometry membership.

The solver retains all original native norm rows and columns, control/trust bounds and declared parameter equations. Starting worst contained-vertex depth remains a hard ceiling. All existing triangle rows now retain their starting global worst deficit as an additional hard local ceiling, without adding triangle slacks to the objective. Every positive full-mesh separation guard remains hard. Explicit per-row clearances preserve the component guide's 10 nanometre target, legacy triangle goals and event zero; original contact and mesh acceptance limits are unchanged.

The returned solver status is preserved. A declared 81-fraction ray checks every represented native norm, box bound, containment ceiling, legacy triangle ceiling and positive guard with zero acceptance allowance. Parameter equations retain the declared 1e-9 proposal tolerance. A nonzero step must strictly improve the sum of component deficits. Such a step is provisional: the represented local model does not enclose nonlinear skinning, stored motion, contact or collision, and improving the sum does not guarantee every component improves.

## Stored-export experiment

Reuse all 180 fully replayed same-point stencils of the ten-frame model, with no fresh derivative queries. Three new 100-variable conic models contain 90 controls and ten component slacks. They retain all 30,450 native norms, 2,132 material rows and 3,132 positive guards from the complete 519,840 triangle/time-pair partition. The three variants add no parameter equations, eighteen event-preserving equations or seventy-two uniform-increment equations. Original sources, 54 absolute storage choices, caps, clocks, references and edit limits remain exact.

The solver statuses are `Solved`, `AlmostSolved` and `Solved`. Strict ray selection accepts fractions 0.9999990463256836, 0.9999847412109375 and 0.0078125 of the respective raw solver steps. Export each strict candidate at the original four declared fractions, then audit and decode both complete actor files. The table gives failures at full, half, quarter and eighth of each already checked candidate.

| Variant | Stored motion failures | Centered continuous motion failures | Actual positive-guard failures |
| --- | --- | --- | --- |
| Original norms | 13 / 5 / 0 / 1 | 5 / 0 / 0 / 0 | 5 / 0 / 0 / 0 |
| Event preserving | 11 / 5 / 4 / 0 | 4 / 0 / 0 / 0 | 8 / 0 / 0 / 0 |
| Uniform increment | 4 / 9 / 6 / 4 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

All twelve exports satisfy the represented affine guards. The original full step fails one original contact row; the other eleven pass the original point-contact checks. Every export passes reference bounds. Only the original quarter and event eighth pass all original stored motion constraints. Both also pass actual positive guards, but both exceed the additional starting legacy-triangle deficit ceiling in the actual nonlinear observations. This measured mismatch remains visible; the affine ceiling is not presented as an exported nonregression certificate.

The original stable selection rule chooses the lowest ten-frame maximum partner vertex depth, then crossing count, among changed exports passing original motion/reference/trust and actual positive guards. It selects the original-norm quarter, whose actual maximum control step is 0.0049999952316263085. The full original 1,673-sample scan is run once for that changed export. All other exports and their ten-frame queries remain saved without speculative full-scene approval.

| Complete scene | Maximum partner vertex depth, mm | Proper crossing records | Samples with crossings | Over-limit vertices |
| --- | ---: | ---: | ---: | ---: |
| Starting verified storage-corrected anchor | 4.680554928 | 29,642 | 1,575 | 0 |
| Component objective, selected original quarter | 4.680528900 | 29,805 | 1,577 | 0 |

The selected actual fixed-axis component deficit sum falls from 0.126649833271653 m to 0.125893915144876 m across the ten groups. Its vertex depth changes by only approximately 26 nanometres, while 163 crossing records and two crossing samples are added. All ten-frame exports retain 164 recorded triangle crossings at the declared guide times. This is a failed collision correction, despite an improved guide objective and motion-passing selected export. The historical lower-depth branch stays retained; this is not a matched comparison against the earlier triangle objective, whose anchor and guide population differ.

## Verification and next action

The separate original-context reader reconstructs every complete component group and material corner identity, all three conic matrices/vectors/cone populations, solver statuses and every strict ray prefix. It manually decodes all twelve exports, reproduces complete native/scalar/contact/reference observations, all component merits, actual legacy-triangle ceiling results, full-mesh positive guards and ten-frame mesh queries. It verifies selection and the full archive's transport and original clocks/limits. The preceding complete-model replay binds all 180 stencils, 90 columns and 9,120 exact-rational affine coordinate enclosures. No producer solver, model, Job, centering or guard-builder API is used by the consumer. Skin/norm/collision predicates are shared; this does not prove solver optimality or independent collision arithmetic.

Thirty-eight focused tests pass without skips, including complete unequal Cartesian populations, duplicate reversed groups, missing or mislabelled witnesses, all conic slack rows, hard native/guard/containment/legacy bounds, status preservation, invalid iterates, strict retreat and observer isolation. The source workflow registers the new test while preserving every other workflow byte. Raw trials, matrices, actor payloads and consumers remain under ignored `reports/`.

Next inspect the actual legacy-triangle and motion defects, and the crossing identities that regress despite improved component support, before another correction. A lower guide sum cannot substitute for the unchanged zero-crossing gate. There is no source/candidate promotion, learned-model change, neural inference, production anatomy, engine import, animator review or cleanup-time evidence. All fourteen release evidence arrays remain empty and the full-project goal remains active.
