# Preserve scene contact intent across rig transfer

`native_transfer_scene.py` bridges a supplied character's explicit scene contacts to one or more completed native rig transfers. It produces a separate portable contact scene and measures what survives. It accepts arbitrary action clips under the existing rig/scene contracts; it does not select motions from an action list or infer palms, soles or vertex correspondence from bone names.

The [native transfer](native-rig-transfer-v1.md) preserves motion and original target assets, but its contact file intentionally contains no inferred annotations. This bridge retains authored world, moving-object and partner targets, including contacts where the replaced actor is the partner target rather than the initiating actor. Every affected used skin vertex must have a distinct explicitly supplied target vertex. The source rig and selected clip must match each transfer's immutable provenance.

## Use

Create a recipe binding an existing `strep-native-scene-contacts-v1` JSON file and completed transfer folders:

```json
{
  "schema": "strep-native-transfer-scene-v1",
  "contacts": {"path": "scene.json", "sha256": "SHA256_OF_SCENE_JSON"},
  "transfers": {
    "A": {
      "candidate": {"path": "my-transfer", "sha256": "SHA256_OF_TRANSFER_REPORT_JSON"},
      "vertex_map": [
        {"source": [22, 0, 100], "target": [5, 0, 82]}
      ]
    }
  }
}
```

The paths resolve relative to the recipe. `A` must name an actor already in the source scene. Replace the example digests and vertices with actual bindings and complete reviewed correspondence; one row above is illustrative. One to eight actors that participate in contacts can be replaced together; other actors remain unchanged. Source and target references use `[mesh node, primitive, vertex]`; a map must cover exactly every vertex used on either side of a contact involving that actor. Missing, extra, duplicated, collapsed or nonexistent correspondence rejects before writing a result. Different source/target vertex populations are supported through explicit correspondence. Actor duration must match the exact shared scene duration.

```powershell
python scripts/native_transfer_scene.py recipe.json reports/my-transfer-scene
```

The resulting `contacts.json` can be loaded directly by the existing native scene measurement, bounded editing and engine tools. Its actor paths are relative to the new folder and point to copied candidate/unchanged partner GLBs. The selected transfer animation index remains explicit, including when the target still contains older animations. This command does not import or select a new Studio character. The [Studio transfer workflow](studio-native-rig-transfer-v1.md) handles separate candidate library import.

## Invariants and measurements

Only the bound actor file/checksum/selected animation and corresponding skin references change. Actor placement, contact IDs, initiating actors, reductions, touch/hold modes, exact times, limits, world points, object geometry/pose tracks, partner identity and unaffected vertices remain unchanged. A larger target cannot gain approval by moving its box, partner or ground target, widening limits or dropping a failed condition.

Both original and candidate receive the existing complete frame-relative speed audit, including unavailable short-hold populations. A second measurement uses the union of both contact clocks plus quarter/midpoint/three-quarter positions in every interval, so both sides are checked at identical times. The common Float64 clock and every corresponding source/candidate effector, target and error point are retained exactly in `observations.npz`.

The whole comparison is planned before querying animated skin. Fixed limits are 262,144 common position times across all contacts and 1,000,000 corresponding point observations. An oversized request rejects before writing a comparison; no times, contacts or vertices are dropped to fit the budget.

Results distinguish preserved contacts, transfer regressions, and existing source failures. `retention_samples_pass` requires every source and candidate condition to pass. `status: complete` means the comparison finished; it may contain failed contacts. Touch checks retain the exact event time. These finite probes do not establish continuous contact, surface normal opposition, anatomy, collision, physical grip forces or motion quality.

Output includes original/candidate scene specifications, both complete frame audits, common observations, input/transfer snapshots, method archives and checksummed result. `native_transfer_scene.verify(folder, expected_result_sha256)` replays from snapshots, checks complete payloads and reconstructs the exact protected contact intent. Verification also works after relocation; saved absolute audit paths are compared through their bound relative actor identities. Rehashed target, placement, limit, observation, method, scope and file changes must still satisfy semantic replay. Raw failures remain intact. Third-party asset/motion terms still apply to copied and derived files.

After a regression, use explicit bounded scene-edit permissions and geometry/surface constraints, then remeasure the exported clip. This bridge measures the problem and supplies the preserved scene to the existing solver; it does not claim to correct contacts itself. Source-relative rate limits and protected keys remain separate gates during editing.

## Development evidence

The generated tests use independent humanoid hierarchies with different reference axes, reversed node order, optional/helper differences, explicit skin correspondence, primitive box grip points and partner placement. The skins are trivial weighted triangles. Matched proportions preserve the four authored point contacts; a larger target loses them while preserving the exact targets and tolerances. Existing source failures remain separate. Both partner sides can be replaced, the package relocates without losing its replay binding, and the existing bounded scene editor changes the selected appended clip while preserving the older animation and static payload.

The final frozen CPU-only source check passes **137 tests with zero skips**, including 29 new transfer-scene contracts. It also runs the existing scene contact, bounded scene editor/solver and native transfer/audit suites. All copied/current checked source hashes agree after the run. Result SHA256: `9f355833d9d8786a3aa554300884c4c8852107237e3e050131e5424fd3ec6db0`. A parsed CI proof adds only the new Python suite while retaining dependency versions, action pins, permissions, matrices, environment, Node suites and time budgets. Workflow proof SHA256: `877f44a6a97f020432d2c67131c1196246df846327dbff27788b8767b026275b`. No subsequent hosted CI completion is inferred from these local checks.

This is software/file/contact-point evidence, not realistic running, lifting or high-five quality, production character coverage or anatomical review. Human ratings and cleanup time remain missing. No release gate is approved by this bridge.

The final actual CPU/headless study adds moving root trajectories, a moving box and partner, and an exact world-patch touch at `0.0853725 s`. It saves/reloads native animation resources for both actors and checks imported bones and complete raw skin on every common position time:

| Case | Source / target skin joints | Times per source and candidate engine run | Contact result |
| --- | --- | --- | --- |
| Matched proportions, different reference axes and node order | 19 / 19 | 392 | All four conditions retained |
| Larger target with optional/helper differences | 19 / 17 | 392 | All four conditions regress |

The larger target reaches **0.4833 m** point error and **0.0645 m/s** relative slip against unchanged targets, versus the fixture's **0.002 m** position and **0.002 m/s** hold limits. The exact touch retains its time and has no hold-speed population. Source conditions pass in both cases. The matched target stays below `1.94e-7 m` common position error; its largest relative slip is `1.12e-5 m/s`. Imported pose component error stays below `5.33e-7`, and maximum engine/native raw-skin error below `6.01e-7 m`, within the existing `1e-4` import limits.

All four final owned engine processes terminate with zero exits and clean logs. Original inputs remain unchanged; final method archives match current source. The driver uses the existing owned process-tree supervisor and expands the engine request to the complete common query clock; Godot scripts/resources and imported observations are actual, without engine output doubles. Final study receipt SHA256: `7f9620fb9347f9c4d48e00fa954daf2fe8911f5efab5328c7fc89225a66946ec`. Complete evidence stays locally under ignored `reports/native-transfer-scene-engine-v3`; earlier static/moving development studies remain retained.

No live Studio HTTP/browser, server restart, rendered/GPU check, production anatomical query, model sampling/training, human rating or cleanup test was performed. Matching synthetic vertices does not establish opposing palm surfaces or realistic grip behavior. Scene geometry/surface orientation and subsequent contact correction remain separate requirements.
