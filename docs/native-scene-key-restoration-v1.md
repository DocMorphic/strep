# Native key restoration under original motion limits

`scripts/native_scene_key_restore.py` adds a bounded native-only restoration helper for proposals whose stored assets fail motion or contact conditions. It recenters the local model on complete decoded assets and protects every original native norm. Geometry, transitions, engine readback and animation quality require separate checks.

## Restoration contract

The caller supplies the existing scene problem, starting controls and a callback that exports, independently decodes and retains every probe. The helper checks the complete actor/world population, recomputes native conditions from decoded worlds and requires the reported residual to match exactly. It retains every original cap, scale and norm row. Starting controls must lie inside the original boxes.

Each of at most four stages computes central differences of the continuous pose proxy, anchored to the decoded vectors, then solves with every native norm protected. Four bounded fractions may be tested. A stage can retain an improved failed point as the next numerical anchor; that does not select an animation candidate. A passing native point still requires original-reference cumulative bounds and complete scene evaluation.

Existing jobs, exporters and acceptance rules remain unchanged. The helper does not insert native keys, add pose freedom or infer animation quality from feasibility.

## Actual retained proposal result

The retained one-eighth compact-surface proposal passes every native condition before serialization, but its stored keys fail six original angular-acceleration rows. They belong to actor A, joint nodes 6, 7 and 8, at metric sample indices 23 and 53. These are existing generic rig identifiers, not inferred production anatomy. Contacts pass.

The experiment keeps the same full-clip boundary permissions, thirty controls, source-scale quaternion storage, nine byte-identical rate arrays and original contact limits. All 1,707 native times remain. Cumulative bounds retain the original assembly as their reference.

The restoration uses a `0.0001` normalized-control trust radius and `0.00001` central-difference step. Its model protects all 29,290 original native norms. Clarabel returns `PrimalInfeasible` for this local affine model, with twenty-one active cones. No repair direction or new repair probe is produced; the original six failures remain. This is not a global infeasibility proof or permission to change a cap.

The complete starting exports, decoded world arrays and residuals match the previous one-eighth proposal byte-for-byte. Independent direct rate evaluation reconfirms all six stored failures against the original arrays, while complete unrounded native conditions pass. There is no new geometry or engine assessment for this rejected point.

Continuous derivatives alone did not repair this measured stored-key defect in the tested trust region. The next experiment must test bounded changes to actual stored quaternion components, preserve the original clocks, protected keys, track bounds and contact intent, and independently decode every candidate. Any native-passing result must then undergo complete original-reference and geometry checks.

## Verification and scope

All 100 focused tests pass with zero skips, including eighteen new cases and related norm, restoration and serialized-ray suites. The new tests exercise actual exported translation restoration, passing-start behavior, complete decoded populations, unchanged caps, invalid settings, original boxes and unavailable directions. They establish helper behavior on generated fixtures. Parsed CI adds only the new suite. Broad production actions and developer/animator cleanup evaluation remain open.

| Local receipt | SHA256 |
| --- | --- |
| `reports/native-key-restoration-probe-v1/result.json` | `93a9157267f7929b94b3339723300b37866576c4d01afbb6c4c8da4030491813` |
| `reports/native-key-restoration-independent-v1/result.json` | `f8b6e132f40b707ac71cdc425074ecc9517a1aacda867347cdcd17d1102b7dbb` |

Original inputs and archived/current numerical methods remain unchanged. The proposal remains rejected. No rendering/GPU, new model sampling/training or human review is claimed; all fourteen release evidence arrays remain empty and the full-project goal remains active.
