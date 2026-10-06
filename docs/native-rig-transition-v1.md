# Native tangent-matched transitions

`scripts/native_rig_transition.py` appends a transition between two explicitly selected clips in the **same rigged GLB**. It preserves every original animation and raw binary prefix, keeps the first clip before its selected cut and the second after its selected cut, and replaces the interval between them with a new bridge. It accepts arbitrary source motions rather than an action whitelist. Source clips remain separately editable and selected by default.

The existing `rig_transition.py` remains unchanged for historical studies. This workflow uses actual native key clocks rather than its fixed 30 FPS frame convention. It is an offline CLI feature; Studio integration remains open.

## Construction

Local translation uses a cubic Hermite curve with endpoint positions and velocities. Hermite interpolation matches specified values and first derivatives ([SciPy 1.15.3 documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.interpolate.CubicHermiteSpline.html)). Local rotations use spherical de Casteljau evaluation, following the spherical Bezier construction in [Shoemake's original quaternion-curve paper](https://doi.org/10.1145/325334.325242).

For bridge duration `D`, rotation controls are `R0`, `Exp(w0 D/3) R0`, `Exp(-w1 D/3) R1`, `R1`. The endpoint angular rates are expressed in the local parent frame, using `R_next @ R_previous.T` from neighboring source keys. Endpoint translation and rotation rates are matched by the construction; this is independently tested with noncommuting rotations. Raw tangent magnitudes and adjacent controls must stay inside the authored shortest-arc budget, at most 170 degrees. Multiple-turn tangents cannot alias into apparently small control rotations.

Only transform paths animated in either selected source are authored. Unanimated paths retain their defaults. This matters in practice: redundant root quaternion tracks introduced imported interpolation jitter in the first study and failed the original strict support-slip screen.

The curve is sampled at 60/120/240 Hz onto a Float32 clock with all retained source keys. Bridge endpoints and shifted second-clip times are explicitly serialized; collisions reject rather than dropping keys. The source cut values must be **exact interior native key times**, not rounded decimal approximations. Original clips, including trimmed portions, stay in the file. Root alignment, retiming, object/partner tracks, contact annotations and gameplay events are not inferred or remapped.

## Recipe and use

Run `python scripts/native_rig_transition.py transition-recipe.json reports/my-transition` from the repository root, using the existing NumPy/SciPy environment and a fresh output directory. Replace the illustrative file hash, indices, root node and support references below with actual asset values:

```json
{
  "schema": "strep-native-rig-transition-v1",
  "source": {"path": "character-library.glb", "sha256": "<SHA256>"},
  "animation_indices": [1, 2],
  "cuts_s": [0.4000000059604645, 0.20000000298023224],
  "root_node": 0,
  "bridge_duration_s": 0.2,
  "rate": 240,
  "label": "my transition",
  "maximum_pose_vertex_queries": 1000000,
  "limits": {
    "curve_control_rotation_degrees": 170,
    "bridge_root_excursion_m": 0.1,
    "linear_boundary_jump_m_s": 0.1,
    "angular_boundary_jump_degrees_s": 2,
    "root_acceleration_m_s2": 20
  },
  "floor": {"height_m": 0, "maximum_penetration_m": 0.005},
  "supports": [
    {
      "id": "authored support patch",
      "vertices": [[20, 0, 10]],
      "points_m": [[0.1, 0, 0.2]],
      "interval_u": [0, 1],
      "limits": {"position_m": 0.002, "relative_speed_m_s": 0.02}
    }
  ]
}
```

Support references identify `[mesh node, primitive, vertex]` and have one explicit world target per vertex. `interval_u` names fractions of the serialized bridge, avoiding ambiguous nominal-vs-Float32 endpoint seconds. Up to eight distinct patches are supported; holds need positive-width intervals. An empty support list and `floor: null` explicitly mean those conditions are unavailable, not verified. Floor checks cover the complete decoded mesh within the bridge against the declared horizontal plane. Support checks use exported skin positions and finite differences; they do not infer anatomical soles or grasp patches.

Source clips must have supported LINEAR skin-joint TRS tracks and rigid reference transforms. Only the declared root may have nonconstant local translations; animated scale and morph tracks are unsupported. At most 512 nodes, 8,192 output keys and 30 output seconds are supported. The existing native-clock helper also bounds each input's complete dense clock. No fixed target skeleton or particular action name is required.

The complete readback population is `queries * (2 * node_count + vertex_count)`, including expected and observed poses and every mesh vertex. Queries include all stored keys, quarter/mid/three-quarter points and exact authored support boundaries. The explicit 1–1,000,000 population cap rejects before output without truncation. Construction and verification replay add work; this cap is not a wall-time or total repeated-work guarantee.

## Audit and failure handling

`result.json` reports the appended index, exact duration/cuts, full readback fidelity, endpoint rate jumps, root excursion from the bridge endpoint chord, root acceleration, support errors/slip and floor depth. Boundary rates include every skin joint and are neighboring native-key finite differences. Root acceleration covers the bridge and its adjacent native-key intervals; it does not approve other source discontinuities. Root excursion is relative to the endpoint chord, not an absolute motion or joint-displacement permission.

Fixed fidelity limits remain `1e-5` for key matrix components, `1e-4 m` for queried joint positions and `1e-4 rad` for queried orientations. Authored support/floor/rate limits are independent. Failed samples retain `character.glb`, the complete failed report and original selection. Execution failures retain a failed pipeline. Mathematical passes cannot set physics, human, engine or release approval flags.

Replay checks complete original file bindings, recipe/source snapshots and archived/current methods; reconstructs the deterministic GLB byte for byte; and recomputes every measurement and typed decision. Rehashed labels, summaries, quality flags, snapshots, missing original inputs and methods reject. Input assets and existing animation metadata/accessor/buffer-view/default-transform identity remain bound.

These are sampled screens. The method does not solve contacts, infer supports, correct geometry, certify continuous angular rates/contact/collision, check self-intersection, or establish realistic dynamics. Explicit leg/contact correction and synchronized scene/partner/event timelines remain required for more difficult transitions.

## Completed software study

Final frozen source checks pass **34 cases, zero skips**, including noncommuting endpoint tangent checks, old clip/payload preservation, protected source-key poses, omitted static paths, passing support, failed moving support/floor, missing-condition uncertainty, complete budgets, typed schemas, branch aliasing and rehashed artifact mutations. The initial smoke passed 31 cases and exposed an invalid-NaN test-writer issue, which was corrected. The earlier complete 34-pass receipt remains saved alongside the final receipt. CI adds only this Python suite; all other parsed workflow fields, pins and dependencies remain unchanged.

A serial real Godot study reuses a previously generated 19-joint closed cube skin, with 152 vertices and 228 faces, and adds two arbitrary arm gesture clips. It compares a pose-only smoothstep bridge with the tangent bridge under the same cuts, duration and key clock. The final transition appends at index 3, preserves three old clips, and has 290 keys, 1,157 native readback queries and a complete population of 224,458 pose/vertex observations.

| Largest boundary jump | Pose-only bridge | Tangent bridge |
| --- | ---: | ---: |
| Angular, degrees/second | 49.3961 | 0.91644 |
| Linear, m/second | 0.45955 | 0.0086831 |

The angular jump decreases 98.14% in this fixture. It is a comparison of deterministic interpolation methods, not a general model quality result. Native support and floor pass; maximum queried interpolation errors are `8.689e-6 m` and `1.631e-5 rad`. A moving-root negative retains **52.191 mm** support-position error, **0.49990 m/s** slip and **8.042 mm** floor penetration. A separately raised floor retains a 10 mm failure. None is hidden or relaxed.

The first actual saved-resource run passes pose, skin and floor fidelity but fails support slip: **1.47482e-5 m/s** exceeds the original `1e-5 m/s` limit. After omitting unanimated paths, the new run preserves that limit and passes imported support with zero measured slip and `1.299e-7 m` position error. Actual Godot saves/reloads the native animation and checks **1,252 times**. Maximum pose component error is `4.262e-7`; raw CPU-skin error is `2.890e-7 m`. Both owned engine processes, including the failed study, exit zero with clean logs. Original studies and the earlier failure remain unchanged; checked current/archived methods match and the worker lock is free.

No live Studio/HTTP/browser/server restart, rendering/GPU, production anatomical query, new model sampling/training or human review occurred. Closed cube skins provide numerical software evidence. Production action naturalness, moving contact correction, object/partner timing, root/event sidecar integration, Studio previews and independent animator cleanup remain open. All fourteen release evidence arrays remain empty and the full-project goal remains active.

Local ignored receipts: final source `reports/native-rig-transition-source-check-v2/result.json`, SHA256 `6fa855fe333c3fced9e59411d88ea464991e494f8a5f0ed9c0ae6e140df04106`; final actual study `reports/native-rig-transition-engine-v2/result.json`, SHA256 `2407e919fdf67752b8692cf5a588c370c6dd46a6472e43184d842390e4a28343`; retained failed actual study `reports/native-rig-transition-engine-v1/failure.json`, SHA256 `fecf1a672a03d743be364362eca2e0404a6dbf5cbb34531dc3df8c8a998af9d4`; parsed workflow proof `reports/native-rig-transition-workflow-v1/proof.json`, SHA256 `e9c1922758cdf343e48922d9efaaddd174b2cd616c66cde0a4676f238bf40551`. Generated assets, raw resources and bulky observations remain local. Hosted CI success is not inferred.
