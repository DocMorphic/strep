# Articulated native scene-transition correction

The offline `scripts/native_transition_scene_fit.py` wrapper appends a bridge-only correction candidate to every actor's existing GLB clip library. It uses the existing general scene fitter with explicit native translation/rotation/scale tracks and world, object-local or partner-vertex contacts. Action names are not a whitelist. Original actors, clips, binary payloads, placements, rigid object trajectories, source annotations, gameplay markers and failed measurements remain retained. A numerical correction proposal does not establish a realistic action or make an infeasible contact solvable.

## Request and permissions

A `strep-native-transition-scene-fit-v1` recipe binds a completed shared scene-transition directory by its exact result SHA256. It supplies an explicit label, actor edit permissions, whole-scene geometry policy, 1ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“16 iterations and a complete pose/vertex query budget no larger than one million. Each edited actor supplies the existing scene-edit fields: `window_s`, `protected_s`, `knots_s`, `tracks` and `maximum_joint_displacement_m`. Every track names an existing unique node/path and its original cumulative change limit. Context actors remain unchanged but receive an appended copy so every selected variant stays on the shared timeline.

The edit window must equal the sealed bridge. Every selected track must have bridge endpoint keys, two tangent-guard keys and interior keys. The wrapper protects the first and last bridge key intervals in addition to the author's protected spans. It preserves the complete original clip library and raw binary prefix, restores the originally selected clip, and selects only an appended candidate in a separate scene. The original scene remains selected for acceptance purposes. Permissions apply to this explicit articulated-edit epoch; they do not claim compliance with a preceding root-only variant's restriction against articulation.

The exact source-rate/contact clock is previewed before allocating solver pose arrays. The final clock includes every source motion sample, geometry sample, inherited scene/root time and transition audit time. Budget cost is `times * (sum(2 * actor_node_count + actor_vertex_count) + 2 * object_count)`. The complete population rejects when over budget; no track, actor, mesh, clock or contact is silently dropped. Source reconstruction and asset validation still precede this solver-allocation check.

## Constraints and continuation

The existing fitter retains cumulative native-key change limits, joint displacement limits, independently decoded motion/contact rows and original source-rate caps. The proposal uses source-scale rotation storage, central finite differences, bounded trust/restoration and serialized ray probes. It is a bounded heuristic search, with no feasibility guarantee. All native transition support, root, acceleration, boundary and floor conditions are rechecked after appending and reading the actual GLBs.

An inherited world-floor limit is independently tested on full placed actor meshes over the complete clip. It remains binding even when the new geometry policy declares no planes. Missing/nonfinite actor poses, a truncated pose population or an incomplete clock reject rather than accidentally passing through a shortened loop. Source-phase floor failures remain failures even if the bridge itself passes.

`--resume-from` continues a completed underlying `fit/` directory. Its original contacts, edit permissions, geometry policy, source-rate caps, frame contract, controls and retained proposal evidence remain bound through the existing resume verifier. This is continuation of the same epoch, not a new seed or an independent result. The preceding fit and its old method snapshot remain immutable.

```powershell
python scripts/native_transition_scene_fit.py recipe.json reports/my-bridge-candidate
python scripts/native_transition_scene_fit.py recipe.json reports/my-continued-candidate --resume-from reports/my-bridge-candidate/fit
```

Both output directories must be fresh and separate from the sealed source. The CLI is offline; no live Studio operation is implied. Reproduction requires the explicitly bound scene/GLB inputs and installed dependencies. Generated study inputs and reports are local ignored artifacts, not a bundled public model or character distribution.

## Tracks, replay and decisions

Candidate root tracks use exact native matrices and initial-relative deltas on the full shared clock. They are marked **native-only**, with engine verification false. They cannot substitute for imported engine measurements. Original marker times survive, all transferred gameplay confirmations remain false, and contact records remain non-dispatchable. No grasp attachment, contact semantics, ownership, reaction or confirmed gameplay event is inferred.

Pure replay verifies the complete original scene snapshot, current/archived methods, original recipe/input bindings, fit epoch/caps, exact appended actor bytes, all contact observation bytes, scene geometry transport receipts and the complete artifact-hash population. Geometry and track regeneration occurs in temporary directories so replay does not overwrite sealed observations. Typed full-result comparison rejects rehashed approval flags, integer aliases, missing artifact entries and forged event dispatch. Failed numerical decisions can complete as retained negative results; exceptions preserve a failed pipeline. Quality, training, release and engine-approval flags remain false.

## Measured development evidence

The generated study uses two placed 19-joint closed cube skins and arbitrary gesture source clips. A single explicitly authored partner point meeting is limited to 20 micrometres. This is a micro contact-correction fixture, not a human high-five, physical interaction or held-out production action.

The initial 16-iteration epoch reduces the original 213.2149-micrometre contact error to 20.2577 micrometres but still fails the original 20-micrometre limit. Actor transition conditions pass; sampled scene geometry remains unresolved near coplanar cube faces. Ground-contact rows stay within their original limits. These failures remain retained, with no tolerance relaxation. The preliminary pre-hardening source suite passes 13 cases; later floor, complete-population and continuation changes receive separate final evidence below.

The final source checks cover 22 distinct passing cases: 21 pass in the full 849.32-second run, which retains one incorrect fixture-height assertion; that single corrected fixture then passes in 86.84 seconds. The only test change raises its deliberately intersecting floor from 0.036 m to 0.236 m; source methods and all 21 other passing cases are unchanged. The original failure is retained. These checks include appended context actors, unchanged clip/binary populations and source phases, exact complete clocks, rejection before solver pose allocation, full-clip floor preservation, invalid permissions, pure replay and rehashed artifacts/dispatch decisions.

A fresh current-method candidate continues the original underlying fit for one more iteration, retaining its source epoch and all 17 cumulative primary iterations. The native partner error stays at 20.2577 micrometres; the contact and whole-scene geometry checks remain failed. Pure replay leaves the complete output tree unchanged. All old study files remain unchanged and every current method matches its archived snapshot.

One serial actual Godot 4.7.2 process saves/reloads both appended actor Animation resources and checks all **1,707 shared times**. Actor pose-component error is `3.0303e-7`, full placed CPU-skin error is `2.3265e-7 m`, and root-reference component error is `9.5367e-8`. Actor/native-root fidelity and rigid object transform fidelity pass their original thresholds. Imported partner contact error is `20.322667` micrometres and remains failed against 20 micrometres; imported sampled geometry also remains failed. Near/coplanar cube-face outcomes are unresolved, not a measured penetration certificate. The owned engine process exits zero with a clean log and a stopped tree; the driver also exits zero after recording both passing fidelity and failed scene conditions. The worker lock is free.

Native track files remain native-only even after this separate imported readback, and all gameplay confirmations remain false. No live Studio/HTTP/browser/server restart, rendered/GPU, production anatomical query, new model sampling/training, runtime event dispatch or human review occurred. The prototype's 96-control/one-million-query caps can reject long or dense production assets; this study does not establish production-scale throughput.

Local ignored receipts: `reports/transition-scene-fit-source-check-v1/result.json`, `reports/transition-scene-fit-continuation-v1/result.json` and `reports/transition-scene-fit-workflow-v1.json`. Source receipt SHA256 `fc9001461d60b271db335831cfe66054ed1fbaf68f6b8dd79d5addc69144c5d3`; continuation/engine receipt SHA256 `89b69adf670aacbec3fcd0e39e1bdbb7d766cfd99b0388c517124570a3e8c573`; parsed workflow proof SHA256 `48c44ec7d03fa8175d5b9e2accb119f35adb27a22e84092b68d165382941c491`.

 All fourteen release evidence arrays remain empty. Production action/style/rig/object/partner coverage, reliable default import, Studio correction integration, confirmed gameplay playback and developer/independent animator cleanup review remain open. The full-project goal stays active.
