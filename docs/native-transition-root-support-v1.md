# Native transition root support correction

`scripts/native_transition_root_support.py` appends a root-translation-only variant of a completed native transition. The source transition may have failed support or floor screens. Every original animation, including that failed transition, stays intact and selected by default. This is an offline CLI proposal with bounded edits and deterministic replay; it is not leg IK or a general scene feasibility solver.

## Construction and permissions

The recipe binds a completed `native_rig_transition.py` folder by its exact `result.json` SHA256. Verification replays that source before reading its selected animation. The root must already have one LINEAR translation channel using the complete transition clock. No skeleton, action name or anatomical support is assumed. Explicit mesh-vertex patches and world target positions come from the source recipe; their timing and position/slip limits stay unchanged.

glTF skinning combines joint transforms using stored vertex weights and inverse bind matrices ([Khronos skinning tutorial](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html)). For this implementation, the root response is derived from that weighted transform: changing the root's local translation by `delta` displaces vertex `v` by `f_v * P(t) * delta`, where `f_v` is the sum of its raw weights whose joints descend from that root and `P(t)` is the root parent's world linear transform. We do not normalize the stored weights. Accumulation uses Float64 to agree with the CPU skin evaluator. An independent forward-kinematics/skin test checks this derivation with eight influence slots, mixed root/non-root weights and an animated parent at three arbitrary clocks.

Each native key bracketing an authored hold is projected by least squares onto all active patch targets. Guard keys may extend the proposed hold to adjacent native keys; the acceptance audit still uses the exact original contact interval. Contiguous groups need neighboring keys for rates. Cubic Hermite ramps connect those groups to the unchanged edit-window endpoints using neighboring source and projected-key rates. Hermite interpolation matches specified positions and first derivatives ([SciPy 1.15.3 documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.interpolate.CubicHermiteSpline.html)).

Only root keys strictly inside the declared window can change. All rotations and other animation paths remain exact; source poses and interpolation outside the window remain intact. A four-ULP vector reserve leaves room for Float32 encoding before clipping translation deltas to the authored radius. Exported readback independently checks the actual local root change and world displacement of every skin joint. Quantization, insufficient freedom or an incompatible ramp may still fail the original conditions. Limits are never widened to make a result pass.

## Recipe and use

Run `python scripts/native_transition_root_support.py root-recipe.json reports/my-root-correction` using the existing NumPy/SciPy environment and a fresh output directory. Replace the illustrative binding and exact key times with your source values:

```json
{
  "schema": "strep-native-transition-root-support-v1",
  "source": {
    "folder": "reports/my-native-transition",
    "result_sha256": "<SHA256 of source result.json>"
  },
  "label": "authored support correction",
  "window_s": [0.25, 0.9000000357627869],
  "maximum_root_translation_change_m": 0.08,
  "maximum_joint_displacement_m": 0.08,
  "maximum_pose_vertex_queries": 1000000
}
```

The source folder is relative to the recipe directory. Window endpoints must be distinct, exact existing native keys; rounded decimal approximations can reject. Root and joint budgets accept `1e-6` through `0.22 m`. The complete population cap accepts integers from 1 through 1,000,000 and rejects before output without truncation. It counts `queries * (2 * node_count + vertex_count)`, including complete expected/observed poses and mesh vertices. The query clock includes all native keys, quarter/mid/three-quarter points, support boundaries and window endpoints. Repeated construction/replay adds work; the cap is not a wall-time bound.

Necessary reach checks bound each patch vertex's possible displacement under the root and joint permissions. Protected endpoints/outside poses have zero reach. Equivalent checks bound possible correction of bridge floor depth. Violations record necessary conflicts and produce no candidate or root sidecar. Passing these checks does not establish feasibility: incompatible patch targets may instead produce a retained, failed least-squares candidate. The solver does not automatically expand the edit window or request more permissions.

## Export and audit

An attempted candidate is an additional animation in `character.glb`; all old animation metadata, default transforms, accessors, buffer views and the raw binary prefix remain intact. Only the appended animation's root translation accessor differs from its raw source. `root-motion.json` records the declared root world position and quaternion at every stored key, with the exact animation index and native clock. Extraction is not applied to the GLB. This file is a root track, not a transferred contact/event or gameplay timeline.

The audit checks complete decoded joint/skin poses, unchanged rotations, root/joint budgets, every support position and finite-difference slip sample, complete mesh floor depth **within the bridge**, joint linear/angular jumps at bridge and correction-window boundaries, root acceleration over that combined interval and bridge root excursion from the endpoint chord. Source support, floor and transition-rate thresholds are inherited exactly. Source corners elsewhere in the clip are not thereby approved.

Replay binds original recipes/inputs, source snapshots, current and archived methods, exact deterministic candidate bytes, all typed measurements/decisions and the root sidecar. Rehashed labels, summaries, approvals, sidecars, source snapshots and method mutations reject. Failed candidates remain available with original selection; necessary conflicts have a completed negative receipt without a candidate. Runtime errors retain a failed pipeline. Quality, release, training, physics, human, engine and continuous-collision approval flags remain false in this backend.

These are sampled numerical checks. Root-only correction cannot generally satisfy articulated foot/hand contact, simultaneous incompatible supports, moving objects/partners, body self-collision or realistic dynamics. All such limitations remain part of the full-project goal.

## Validation

The final frozen source run passes **26 cases, zero skips**, including successful repair with original clips/protected interpolation preserved, independent mixed-weight affine response, frozen/insufficient permissions, retained angular corners, bounded/typed requests, contradictory targets and rehashed artifact mutations. The first run passed 25 cases and exposed Float32 accumulation in the mixed-weight response; the corrected full run uses Float64 accumulation and passes all 26. CI adds only this suite; all other parsed workflow fields and dependencies are unchanged.

The actual engine study reuses the sealed moving-root failure from the preceding tangent-transition study. It does not regenerate the source or sample a model. Its original bridge has **52.191 mm** support-position error, **0.49990 m/s** slip and **8.042 mm** floor penetration. The new candidate changes root translation by at most **52.191 mm**, retains four original clips and appends at index 4. Native support error/slip and bridge penetration become zero under the unchanged `1e-5 m` position/floor and `1e-5 m/s` slip limits. Its maximum root acceleration is **6.3858 m/s²** under the original 20 m/s² limit; all declared native correction screens pass.

The recorded initial window starts at the existing `0.20000000298023224 s` angular corner. That candidate repairs contact/floor but retains a **25.0001 degrees/s** seam failure. A separately recorded request starts at the exact `0.25 s` key and passes the declared window/bridge seam checks; it leaves the old angular corner elsewhere in the source unchanged. Frozen bridge-only endpoints and a 1 mm root budget produce necessary conflicts with no candidate. These failures remain separate immutable receipts.

Actual headless Godot saves/reloads the native Animation resource and checks **1,252 times**, including the complete 1,157-query native audit clock. Imported support passes the same strict limits with zero measured slip and `1.455e-7 m` position error; imported bridge floor penetration is zero. Maximum pose component error is `4.262e-7`, CPU skin-position error is `3.600e-7 m`, and world root positions from the sidecar agree with imported native-key poses within `1.755e-7 m`.

The complete engine floor report remains **failed**: it measures **15.409 mm** penetration at time zero, outside the correction window and bridge. The unchanged protected source measures the same depth within engine precision. The complete clock, plane and original penetration limit remain in that failed report; the bridge-only pass does not overwrite it. The owned process exits zero with a clean log and stopped process tree. Current/archived method hashes agree, all previous sealed studies remain unchanged and the worker lock is free.

No live Studio/HTTP/browser/server restart, rendering/GPU check, production anatomical query, new model sampling/training or human review occurred. Closed cube skins supply software evidence. Production naturalness, articulated contact correction, scene/partner/event synchronization, Studio integration and developer/independent animator cleanup remain open. All fourteen release evidence arrays remain empty and the full-project goal stays active.

Final source receipt: `reports/native-transition-root-source-check-v1/result.json`, SHA256 `cdb00c11596877f82413a43d27e524e12c2377788c544c20a502594e5b48ef38`. Actual engine study: `reports/native-transition-root-engine-v1/result.json`, SHA256 `f45df33bf23ae3a2fe21664c7b1672ca0fb759231cfc3ede00ee78a54b8547da`. Parsed workflow proof: `reports/native-transition-root-workflow-v1/proof.json`, SHA256 `b6b8795a9d4fb06503383bfd935bbd1a216e4907ee832175932482b44efccbaa`. Generated character payloads, engine resources and bulky observations remain ignored locally; hosted CI completion is not inferred.
