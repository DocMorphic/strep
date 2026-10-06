# Explicit editing of clip boundary poses

Authors can now opt into editing a clip's opening or ending pose through `BoundarySceneEdits` in `scripts/native_scene_boundary_edit.py`. This is a separate authoring contract; existing scene and bridge editors retain their original endpoint preservation. Broader windows alone could not address the retained scene's crossings at time zero and the clip endpoint.

## Permission and preservation rules

The request contains the existing scene-bound `permissions`, an explicit `start`/`end` policy for every edited actor, and a typed acknowledgement that changed boundaries need their start/end compatibility checked again. Each policy is `preserve` or `edit`. An editable start must be the true clip start; an editable end must be the true clip end. An interior window cannot acquire extra boundary freedom.

Protected times also protect interpolation support. Editing an endpoint is rejected if that endpoint or its adjoining open interpolation segment intersects a protected span. An endpoint can be the only editable key, including a window containing only the first or last segment. Two-key LINEAR tracks are supported without inserting extra keys. Selected tracks still require existing skin-joint rotation/translation channels; adding a channel to a static joint is not implemented by this contract.

Native clocks, unselected tracks/clips, static rig/mesh/bind data, original track-change limits and displacement bounds remain explicit. The contract permits at most 96 complete control components. With both boundaries preserved, valid exports are byte-identical to the legacy editor. `append_candidate` restores the complete original animation library and appends a separate selected variant; it does not select or approve the candidate. Prior start/end transition approval is never inherited.

Callers must separately audit source motion rates, cumulative edits against the original reference, contacts, geometry, engine readback and boundary compatibility. The key/static audit alone does not approve motion. There is no Studio UI integration or automatic Apply for this new contract yet.

## Actual broader source proposals

The completed experiment uses the retained generated two-actor scene, not a production action. Both actors receive a full-clip window, editable clip boundaries, five authored knots, the existing joint-6 rotation track, the original 5-degree track limit and 30 mm joint-displacement bound. The original nine source-rate arrays are retained byte-for-byte; contact targets and limits remain unchanged. No previous boundary approval is inherited.

Four deterministic proposals apply a constant 0.25-degree rotation around each actor's pivot-to-declared-contact-vertex line, with both sign choices. Every proposal is exported and independently decoded at all 1,707 times, retaining the complete 665,730 pose/vertex-query population. Contact constraints pass for all four, and cumulative original-reference displacement and track-change bounds pass. All four proposals nevertheless fail their original rate caps and remain rejected.

| Proposal signs | Failed exported source rows | Failed unrounded source rows | Failed contact rows |
| --- | ---: | ---: | ---: |
| Negative and negative | 26 | 8 | 0 |
| Negative and positive | 25 | 4 | 0 |
| Positive and negative | 25 | 4 | 0 |
| Positive and positive | 24 | 0 | 0 |

Independent evaluation identifies every exported failure as a joint-acceleration or angular-acceleration row. The positive/positive unrounded proposal passes every native condition, while its stored Float32 quaternion keys exceed 24 angular-acceleration rows. The maximum angular-acceleration excess beyond the original cap plus tolerance is approximately `0.000595862 rad/s²`. This is measured serialization sensitivity, not permission to increase a cap. Negative-sign proposals additionally introduce physical joint-acceleration failures in the unrounded curve.

Zero controls retain the source motion and pass the original native conditions. Eight appended variants, two actors for each nonzero proposal, preserve all original clip libraries and binary prefixes. All 1,707 decoded matrices per variant match their corresponding saved probe. Source files, original rate caps and current/archived methods remain unchanged for the final implementation. The earlier prototype observations remain retained separately.

Geometry is not assessed for these rejected proposals, and no new engine run is claimed. They cannot be treated as collision corrections or usable motions. The next solve must handle stored-key precision while protecting original rates, then measure complete geometry and readback.

## Complete surface guidance requirement

The unchanged source geometry report contains 30,502 total triangle records across all 1,673 native geometry samples. The current surface guide expands each triangle record into nine vertex-pair rows, so it would need at least 274,518 rows before additional vertex/object/plane rows. This exceeds both its default 20,000-row budget and its current maximum of 100,000. This is a read-only lower-bound calculation from the complete saved population, not a solver run. A complete compact or streamed guide is needed before a full-clock broader solve; dropping samples or triangle pairs would change the experiment.

## Verification and local evidence

All 120 focused software tests pass with zero skips, including 43 new boundary-contract tests, legacy editing tests and preceding geometry diagnostics. They cover preserved export bytes, opted endpoints, single-segment windows, two-key tracks, protected spans, real decoded motion constraints, appended libraries, malformed permissions and attempts to exceed original track rules. Parsed CI adds only the boundary suite, retaining all other workflow fields. The actual proposal and independent receipt drivers exit zero and release the worker lock; rejected raw results remain immutable.

| Local receipt | SHA256 |
| --- | --- |
| `reports/boundary-scene-probe-v2/result.json` | `eb696dc9a3812ceffba088a57722d221b8cc6196282dcbff6d57d0f8945ab103` |
| `reports/boundary-scene-probe-independent-v2/result.json` | `704a25fabd0ad7dc71bd76753de31df20acb10c4c2d57506b458fad718741f0d` |
| `reports/boundary-scene-source-v2/result.json` | `12b75322dafb4e9b2f8c1fd1114cb5861335b51dc76257cd8dc3c0b3508a80d3` |

Local source checks and the complete-population guide estimate are retained in `reports/boundary-scene-source-v2/`. Generated study outputs remain excluded from the public repository. No live HTTP/browser, rendering/GPU, physics, production anatomical query, new model sampling/training or human review occurred. Broad production actions, rigs, objects, partners and developer/animator cleanup remain open. All fourteen release evidence arrays remain empty; the full-project goal remains active.
