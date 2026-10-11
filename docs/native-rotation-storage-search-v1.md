# Bounded stored quaternion repair search

An earlier generated two-person study found three smaller surface proposals that pass every original native and contact condition after bounded one-neighbour Float32 repairs. Their complete geometry assessments still fail, so none is selected or approved. Those retained results use the earlier angular-only planner; the extension below also targets the other measured source rates without changing acceptance limits.

## Search contract

`scripts/native_rotation_storage_search.py` now searches existing permitted rotation keys on the interpolation support of all four measured source-rate failures: positional speed/acceleration and angular speed/acceleration. It follows strict ancestors for joint-position failures; the joint's own rotation can also be considered for orientation failures. Speed uses two uniform pose samples and acceleration uses three. It plans all four quaternion components and both neighbouring values, restricted to the existing editable key population. Contact and displacement failures remain visible but do not create additional freedoms.

Every component choice is absolute relative to the nearest stored value of the fixed intended curve. A later choice may restore that value or replace the previous neighbour with the opposite neighbour; it cannot accumulate additional steps. The existing source-bound storage policy, maximum correction count, permitted/frozen keys, clocks, unit requirements, control boxes and strict track bounds remain.

The search has explicit stage and probe budgets. It retains the first full-native merit improvement as the next numerical anchor and stops when every condition passes or the finite search makes no improvement. This greedy search is not an exhaustive feasibility method.

The caller retains fresh exports and independently decodes every actor. The helper checks complete finite worlds, the exact original residual vector, native norm population, caps and scales for every observed probe. A passing contact/native result does not confer geometry, transition, engine or quality approval. Existing editors, exporters and Studio jobs remain unchanged.

This extension addresses the [development kick diagnosis](kenney-kick-temporal-layout-v1.md), where stored positional acceleration was a demonstrated failure as well as angular acceleration. Seven additional regression cases cover all four rates, strict position ancestors, distinct two/three-sample support, frozen keys and duplicate choices. When only angular acceleration fails, its existing ordering is preserved. The historical motion results below are from the earlier angular-only implementation and do not establish the new paths on a generated kick.

The ancestor rule follows the `T * R * S` local-transform order and parent/local world-transform composition in the [official glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#transformations). This explains which rotations can affect a joint origin; it does not prove that any neighboring stored value will satisfy motion, contact or geometry limits.

## Extension checks and completed actual-motion study

At commit `d728d91`, the complete focused
[Windows/Linux workflow](https://github.com/DocMorphic/strep/actions/runs/38177394381)
passes **683 Python checks per OS**: 616 contact/rig, including storage search
and repair suites, 35 lineage and 32 game packages, plus the offline editor.
The complete decoder acceptance path, original cap/scales checks, stage/probe
budgets and storage envelope are unchanged; only failure-support planning and
the result's scope text change. The broader source inventory remains pending,
with no full-inventory pass claim.

A twelve-candidate kick ray study deferred before starting under the unchanged
resource policy. All 594 admission observations replay with matching archived
bindings; no motion exports or ray-search outcome exist for that attempt.
Its local protocol remains in `reports/kenney-kick-rotation-ray-v1`.

The follow-up study targets the finer-layout `1-4` proposal, whose
single stored failure is positional acceleration while its unrounded motion
passes. It preserves the same 72 controls, four tracks, source cap arrays,
rate clock, root, endpoints and full 2,017-time floor population. The explicit
boundary contract preserves both endpoints and must reproduce the prior stored
keys exactly. A source-bound one-neighbor policy permits up to 64 absolute
component corrections; search allows four stages and eight probes per stage.
Every exported candidate must receive static/frozen-key and strict track audits,
complete fresh native decoding and the full declared floor audit. A passing
native candidate can be archived as an unapproved appended variant preserving
the original animation library; it still needs geometry and engine review.

The driver subsequently executes in `reports/kenney-kick-position-storage-v1`.
Its [completed study and seeded continuation](kenney-kick-position-storage-v1.md)
produce a stored-native pass with eight corrected components. Fresh replay
reproduces all conditions and the still-failed complete floor audit. This is
now actual development repair evidence, while geometry, engine and human
approval remain absent. No release gate or capability approval changes.

## Three complete retained proposals

The study uses the half, quarter and eighth fractions of the preceding converged surface direction. Each unrounded motion already passes native conditions. Their intended thirty controls remain fixed, along with all nine byte-exact source-rate arrays, original contacts, original-reference bounds, 1,707 native times and 1,673 geometry times. The initial three component corrections from the earlier anchor remain explicit.

Each case permits eight stages and at most thirty-two probes per stage. All thirty-one raw probes are retained, with sixty-two actor exports: three starting points and twenty-eight neighbour probes. Contacts pass throughout.

| Proposal fraction | Initial native failures | Tested neighbours | Final component corrections | Final native failures | Maximum geometry depth |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | 15 | 12 | 9 | 0 | 5.205827 mm |
| 0.25 | 18 | 8 | 8 | 0 | 5.199232 mm |
| 0.125 | 15 | 8 | 7 | 0 | 5.195942 mm |

Every final stored motion passes all original native/contact conditions and cumulative original-reference bounds. Maximum final displacement stays below 0.930 mm and selected-track change below 0.106 degrees, against 30 mm and 5 degree limits. Six appended variants retain every original animation and binary prefix and reproduce all 1,707 decoded world samples each.

Full geometry uses every original time, topology, actor/object query and limit. It remains failed in all three cases. Triangle record counts are 30,469, 30,503 and 30,505; failed sample counts are 1,595, 1,595 and 1,594. The depth limit remains 5 mm. The eighth fraction's depth is slightly lower than the starting repair's approximately 5.196477 mm, but still above the original source's approximately 5.191161 mm. This is not a geometry solution. The unrepaired smaller fractions lacked full geometry assessments, so these comparisons do not isolate the effect of the discrete corrections.

## Independent replay and remaining work

A separate consumer imports neither the new search nor the storage wrapper. It reconstructs every selected payload directly from the fixed controls and scalar Float32 `nextafter`, checks unique permitted components and strict track/unit bounds, and independently decodes every saved probe. All residuals and complete world arrays replay exactly. Original rate/contact and reference measurements pass at every final point. All six original-preserving appended libraries and complete worlds also replay.

Complete geometry clocks, original limits, scores and observation transport verify. Geometry predicates are not independently recomputed. This is generated-fixture numerical evidence, not production motion or human realism assessment.

Sixteen new software tests pass, covering permitted interpolation support, absolute replacement/restoration, complete real export/decode, already-passing motion, unsupported contact failure, false/incomplete native evidence, changed caps and finite budgets. Forty-three existing focused storage/restoration cases also pass. The initial combined run exposed a test fixture with an unsatisfied original contact; the passing-path fixture was corrected and the rejected case retained separately. All fifty-nine distinct focused cases pass across the final checks with zero skips. Parsed CI adds only the new suite; hosted CI is not asserted green.

| Local receipt | SHA256 |
| --- | --- |
| `reports/pair-storage-search-probe-v1/result.json` | `5cecd085a216f532bd7d2b680b5b7ebf4dea4e5e41c3f4da0000a0c2579e882e` |
| `reports/pair-storage-search-independent-v1/result.json` | `9e6611f0f35e5bd19e4516013c5241ec19f8b6707b9c4f279cf668675fc589d2` |

Both CPU drivers exit zero with worker locks free; original inputs and current/archived numerical methods remain unchanged. Generated outputs stay outside Git. Next address demonstrated geometry failures under unchanged external limits, using these stored-feasible points as numerical inputs rather than approved animations. Broad production actions, rigs, objects, partners and developer/animator cleanup remain open. No new engine, rendering/GPU, physics, anatomy, model sampling/training or human review is claimed. All fourteen release evidence arrays remain empty and the full-project goal stays active.
