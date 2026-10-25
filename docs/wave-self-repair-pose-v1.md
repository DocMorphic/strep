# Bounded self-intersection repair: single-pose feasibility

The [location diagnostic](native-surface-locations-v1.md) identifies the worst
sampled wave pose at 2.2312500178813934 seconds, with 106 proper-crossing pairs.
Two bounded proposal methods were tested on the existing floor-corrected clip.
**Neither produces an accepted repair.** The more useful method reduces the
crossing count to ten, but six of those pairs are new.

## Fixed experiment contract

The candidate SHA256 remains
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.
Root and node translations stay fixed. Only arm skin nodes 14–19 can rotate;
the torso, neck and leg nodes stay unchanged. Separate trials permit rotation
edits of at most 10 or 25 degrees per node. These are experimental edit limits,
not an anatomical range-of-motion model.

Every selected triangle pair contributes all nine vertex separation terms.
SLSQP proposes edits with full-mesh floor constraints and rotation-norm bounds.
Each trial has two proposal rounds, each with a 60-iteration budget. Every
proposal is retained, including optimizer failures and bound violations.
The complete native triangle screen evaluates the resulting geometry; solver
success and a lower fitting objective never constitute acceptance.

The first method chooses separation directions from the intersecting source
triangles. All four proposals retain 107 proper crossings, including six new
pairs. Independent replay also finds slight strict angular-limit overruns in
all four. One exploratory producer flag included a tiny angular tolerance;
the strict replay rejects it. Historical result bytes remain unchanged.

The second method uses triangle separation directions from the original GLB's
default-node reference pose, transported through the current common ancestor
of the triangles' dominant skin joints. That pose is not asserted to be the
inverse-bind pose. Directions are fitting guides, not collision certificates.
An explicit interior angular fitting reserve of 0.001% leaves room before the
unchanged nominal acceptance limit.

| Nominal cap | Round | Proper pairs | New pairs | Strict edit bounds |
| --- | ---: | ---: | ---: | --- |
| 10 degrees | 1 | 13 | 2 | Fail |
| 10 degrees | 2 | 24 | 13 | Fail |
| 25 degrees | 1 | 10 | 6 | Pass |
| 25 degrees | 2 | 10 | 6 | Pass |

The two 25-degree proposals have maximum edits of approximately 24.99975
degrees. Their floor depth remains 2.69896 mm, below the declared 5 mm limit.
All proper hand/head crossing records disappear at this pose. The remaining
ten pairs are concentrated in the left shoulder region: six with dominant
skin node 17 on both triangles and four between nodes 13 and 17. This does not
approve that region, establish anatomical quality, or excuse the new pairs.

## Rotation-dependency preflight

`scripts/native_self_edit_preflight.py` now identifies recorded proper-crossing
pairs that rotation-only permissions cannot move. It follows every editable
joint's descendants and every positive skin influence. A triangle pair whose
six vertices are all unaffected cannot be repaired by those rotation edits.
Zero sampled derivatives and tiny weights are never used as proof of invariance.

The helper reports unchanged vertex IDs and both invariant and potentially
affected pairs. An empty invariant set does not prove feasibility. Translations,
weights and topology must remain fixed for its stated conclusion to apply.
This conservative test does not detect every common-rigid or bounded-angle
infeasibility case.

For this pose, 530 vertices may respond to the permitted arm rotations and
2,743 remain unchanged. No proper-crossing pair is wholly unaffected. Thus
this preflight does not establish an impossible request; proposal directions,
nonlinear geometry and the allowed angular range still matter.

Local source validation passes 73 Python cases across preflight, location
metadata and the existing self-surface screen. Full/focused source inventories
contain 659/208 Python files; no full hosted CI pass is asserted.

## Evidence and remaining work

Development-checkout reports retain:

- `reports/wave-self-repair-pose-v1/`: current-pose directions and all four failures.
- `reports/wave-self-edit-preflight-v1/`: initial replay failure from comparing
  direct decoded matrices with the producer's zero-edit hierarchy composition.
- `reports/wave-self-edit-preflight-v2/`: 73 passing tests, exact producer-path
  replay, strict bound rejection, and dependency preflight. The zero-edit
  composition differs from decoded input by less than 1e-12; no historical
  observations or limits were changed.
- `reports/wave-self-repair-pose-v2/`: reference-guided proposals and `locations.png`.
- `reports/wave-self-repair-reference-replay-v1/`: independent reconstruction,
  complete surface replay and strict bound decisions for the new proposals.

Next, resolve the remaining shoulder crossings without new pairs, then carry
the proposal mechanism into bounded temporal windows. Full-clip native and
serialized checks, explicit contacts, engine replay, action preservation and
human review remain necessary. No clip was exported or promoted by this study;
the original remains selected. The broader action, rig, object and partner
requirements remain part of the project goal.
