# Shared-reference native clip libraries

`scripts/native_transfer_library.py` transfers several explicitly selected native clips onto one target character using one fixed target reference profile. Each clip is appended to the progressively extended GLB. Original target animations, accessor/buffer-view metadata, raw binary prefix and default reference transforms are preserved by the existing native transfer contract. Distinct source motions retain distinct output indices and their original durations and keys. Clip IDs organize outputs; they do not restrict action prompts.

This is an offline CLI workflow. Studio integration, blending and synchronized object/partner timeline transfer remain open. A shared reference calibration prevents per-clip reference changes; it does not make different boundary poses or velocities agree automatically.

## Recipe and execution

Use a source-controlled environment with the existing NumPy/SciPy dependencies and native transfer support. No new dependency, checkpoint, sampling or training is required. Run from the repository root:

```powershell
python scripts/native_transfer_library.py library-recipe.json reports/my-native-library
```

The output directory must be fresh. Bind every file with its actual SHA256. Paths below are examples, resolved relative to the recipe:

```json
{
  "schema": "strep-native-transfer-library-v1",
  "target": {
    "glb": {"path": "character.glb", "sha256": "<SHA256>"},
    "profile": {"path": "shared-target-profile.json", "sha256": "<SHA256>"}
  },
  "clips": [
    {
      "id": "first-action",
      "glb": {"path": "source.glb", "sha256": "<SHA256>"},
      "profile": {"path": "source-profile.json", "sha256": "<SHA256>"},
      "animation_index": 1
    },
    {
      "id": "next-action",
      "glb": {"path": "source.glb", "sha256": "<SHA256>"},
      "profile": {"path": "source-profile.json", "sha256": "<SHA256>"},
      "animation_index": 2
    }
  ],
  "rate": 60,
  "maximum_planned_pose_transforms": 1000000,
  "boundaries": [
    {
      "from": "first-action",
      "to": "next-action",
      "limits": {
        "position_m": 0.0001,
        "rotation_degrees": 0.001,
        "linear_speed_jump_m_s": 0.01,
        "angular_speed_jump_degrees_s": 0.1
      }
    }
  ]
}
```

Choose 1–16 unique safe IDs, 60/120/240 Hz, and a complete population budget of 1–1,000,000 transforms. Existing per-clip native transfer restrictions remain: supported rigid mapped hierarchies, LINEAR tracks, no animated non-root translations/scales/morphs or unsupported accessories, at most 512 nodes and 8,192 dense keys per clip. Source profiles must have no axis corrections or world placement. Every target-mapped role must exist in each source. Mapped source world reference matrices must agree to absolute tolerance `1e-12`; different neutral references require a separately calibrated library.

The budget counts dense export and native-key/quarter/mid/three-quarter fidelity populations across every clip, using complete source/target node counts. It is a per-complete-pass population limit, not a total CPU-work or wall-time guarantee. Replays repeat those complete passes. Excessive populations reject before creating output; no samples are dropped.

## Files and profile roles

The final `character.glb` retains existing clips and appends the chosen clips. `catalog.json` records each exact source/output index, duration, dense key count and declared boundary result. Per-clip stages retain source/target/profile snapshots, editable output, raw pose arrays, root/contact files and fidelity reports. The recipe, original file bindings and current/archived implementation hashes bind the complete library.

Two profiles accompany the final character:

- `target-profile.json` retains the original shared axes and world offset, rebinding only the progressively extended character checksum. Use it as the target profile when appending further motions from the same source reference basis.
- `edit-profile.json` binds the final character with empty axis corrections and zero world offset. Use it when the baked clip is an editing/transfer source, avoiding a second application of corrections already in the animation.

`verify(folder)` checks every original binding, snapshot, method, stage and final file. It replays native fidelity, compares every dense transform against the transfer calculation, and recomputes catalog indices and boundary metrics. Rehashing altered summaries, profiles, arrays or GLB bytes does not bypass semantic replay. Failed stages retain previous stage outputs and a failed pipeline; they do not publish a complete library result.

## Boundary interpretation

Requested checks apply only to adjacent selected clips. They compare all target skin-joint endpoint positions and orientations, then world linear/angular velocity vectors computed from the neighboring dense native keys. Angular velocity uses the world rotation increment `R_next @ R_previous.T`. Each authored limit is checked independently. These finite differences are sensitive to sampling rate; they are not continuous interpolation derivatives, acceleration limits or naturalness ratings.

Empty boundary declarations yield `null`, not a pass. A failed boundary remains recorded while individual clips remain usable. The tool does not concatenate clips, align roots, crossfade, correct contacts, transfer object/event timelines, or approve quality. Library engine/contact/geometry/physics/human/release flags remain false; any separately executed engine study has its own narrower evidence.

## Validation and retained failures

Frozen model-free source checks pass **26 tests, zero skips**: old payload/clip preservation, distinct clip selection, stationary passing boundaries, matching poses with failed velocities, missing-check uncertainty, incompatible source references, typed/bounded recipes, rehashed mutations, baked edit-profile misuse and partial-stage failure. Checked current and archived source hashes match. CI adds only this Python suite; other workflow fields, pins, dependencies and jobs are unchanged.

A separate serial headless Godot study reuses previously generated closed cube skins and an existing derived target profile, then adds two arbitrary software-fixture motions. It does not rerun model generation or anatomical calibration. Both appended indices, 1 and 2, are selected from the same final GLB, saved/reloaded as native animation resources, and checked at all **16 dense key times**. Maximum imported pose component error is **3.7224e-7** and raw CPU-skin position error **3.9629e-7 m**. One pinned, owned engine process exits zero with a clean log. Original study files and current/archived methods remain unchanged; the worker lock is free.

The shared-profile boundary has zero endpoint position/orientation error but a **0.6713063 m/s** maximum linear velocity jump and **63.620733 degrees/s** angular velocity jump. Both rate limits fail and remain failed. A matched negative changes only the second clip's wrist reference by 10 degrees and records a 10-degree pose jump. This demonstrates the effect of changing reference calibration; it is not a comparison of learned calibration methods. Stationary unit fixtures separately pass both pose and rate checks.

Generated start-point touches and spatially separated mesh checks are software evidence only. These clips are not realistic action examples or held-out quality evidence. No live Studio/HTTP/browser/server restart, rendered/GPU check, production anatomical query, new sampling/training or human review occurred. Support-aware transition correction, continuous/self-collision, dynamics, production rigs, object/partner timing, Studio integration and developer/independent animator cleanup remain open. All fourteen release evidence arrays remain empty.

Local ignored receipts:

- `reports/native-transfer-library-source-check-v2/result.json`: SHA256 `7a33218752e57b85c9b5ff5f07c644266d013672df6ffab0d69e46008936da02`.
- `reports/native-transfer-library-engine-v1/result.json`: SHA256 `4d8a272df7cc36906151b0f0f89625a7906a22b6311c823f14bd5ff83424d353`.
- `reports/native-transfer-library-workflow-v1/proof.json`: SHA256 `f6251a24fab9977f55e444fb65b96b933935b98348b5087fa7e548aa9636d546`.

The earlier 25-pass receipt remains preserved; the final receipt includes separate edit-profile output and misuse rejection. Receipt payloads, generated characters and saved study resources remain local and are not redistributed with this source snapshot. Hosted CI success is not inferred from local checks.
