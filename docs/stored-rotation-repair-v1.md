# Bounded stored quaternion repair

The retained proposal's six serialized rate failures can be removed with three one-neighbor Float32 component adjustments. Every original native and contact condition then passes on the complete decoded clock. Complete geometry still fails, so the proposal remains rejected.

## Explicit storage contract

`scripts/native_rotation_storage_repair.py` wraps an existing boundary authoring contract without changing old editors or jobs. Its policy binds the canonical authoring request, requires explicit acknowledgement, permits exactly one neighboring Float32 step per component, and limits the correction list to at most sixty-four entries. Duplicate components cannot accumulate extra steps.

Corrections require an existing editable rotation key. Frozen keys, native clocks, unselected tracks and static payloads remain protected. The continuous intended curve is unchanged; corrections apply only to its stored representation. Original control boxes, near-unit quaternion requirements and strict track bounds still apply.

The asset audit compares the entire selected payload against the requested component corrections, in addition to the existing static/clock/permission audit. A plain export or a different correction cannot inherit the repair's audit. Appended variants restore the complete original library and retain the repaired payload in the new clip. None of these checks confer native, geometry, engine or quality approval by themselves.

## Complete retained scene experiment

The experiment starts from the one-eighth compact-surface proposal with thirty fixed controls and the original source-scale storage policy. It preserves all nine source-rate arrays, contact intent and limits, original-reference bounds and all 1,707 native times.

It plans neighboring values for all four quaternion components and both directions on interpolation-support keys of the measured angular-acceleration failures. The search has explicit limits of four stages and sixty-four probes per stage. It stops a stage on a complete-native merit improvement; this finite search is not an exhaustive feasibility proof.

Five neighbors are tested and retained separately. Failed native row counts are `6, 3, 3, 5, 0`; contacts pass in every probe. Three corrections reach a native-passing point:

| Actor | Existing node | Native key index | Quaternion component | Neighbor direction |
| --- | ---: | ---: | --- | ---: |
| A | 6 | 108 | w | +1 |
| A | 6 | 48 | w | -1 |
| A | 6 | 48 | z | +1 |

These are existing generic fixture identifiers. Original-reference maximum joint displacement remains approximately 0.251 mm and maximum selected-track change remains below 0.027 degrees, within the original 30 mm and 5 degree limits. Both appended variants retain every original clip and binary prefix; all 1,707 decoded world arrays per variant match the final probe byte-for-byte.

Full geometry is evaluated at all original 1,673 times with original topology and limits. It reports 30,508 triangle records and 1,592 failed samples, with approximately 5.196477 mm maximum depth against the unchanged 5 mm limit. The original source's depth is approximately 5.191161 mm. The unrepaired one-eighth proposal did not receive a full geometry assessment, so this comparison does not isolate the effect of the three component corrections.

## Independent verification and limits

All 125 focused software tests pass with zero skips, including twenty-five new storage-contract and real export/append tests, plus the existing norm, restoration and serialized-ray suites. Parsed CI adds only the new suite. Software tests establish implementation behavior on generated fixtures.

A separate consumer binds every input, saved artifact and archived method to its receipt. It reconstructs every correction with scalar `nextafter`, verifies every other selected component, independently decodes every probe, and directly reevaluates all original uniform-time rate arrays and contact conditions. Cumulative original-reference limits and appended libraries/world arrays also pass. Geometry populations and full observation transport are verified; geometry predicates are not independently recomputed.

The proposal remains unselected and unapproved. Stored feasibility alone does not make motion collision-free or realistic. The next geometry proposal must preserve this stored-key handling while improving complete scene geometry under the original limits. Broad production actions, rigs, objects, partners, engine evaluation and developer/animator cleanup remain open.

| Local receipt | SHA256 |
| --- | --- |
| `reports/stored-rotation-neighbor-probe-v1/result.json` | `81e4f8d2bf74e928aeca7c7d63cdc37793c4fd87d34d459ce4b42ca911eb738a` |
| `reports/stored-rotation-neighbor-independent-v1/result.json` | `a87d3f822cafc12e37a39d4781640106c508ce3bf19e08c91797bca28d1f8d80` |

Both CPU drivers exit zero and release the worker lock. Original source and method bytes remain unchanged, and generated outputs stay outside Git. No new engine run, rendering/GPU, model sampling/training or human review is claimed. All fourteen release evidence arrays remain empty and the full-project goal remains active.
