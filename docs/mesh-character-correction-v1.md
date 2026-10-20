# Character correction against moving mesh grips

The native correction backend can now move explicitly permitted character tracks toward grips on imported static meshes, including objects with animated rigid placement. It consumes the saved scene packages produced by the Studio mesh-contact editor. The initial guarded command-line path described here is now also connected to [Studio correction and candidate comparison](studio-mesh-character-correction-v1.md).

This follows the saved-scene preview, not a new generation checkpoint. It applies to supplied clips and rigs rather than an action whitelist. It does not reposition the props, alter contact targets, change timing, or grant additional joint permissions to make a request pass.

## Inputs and use

Create an explicit `strep-native-mesh-character-edit-v1` JSON record containing `schema`, `mesh_scene`, `mesh_scene_sha256` and `actors`. `mesh_scene` identifies the exact saved `package/mesh-scene.json`; its SHA-256 binds all imported-object and character intent. Paths resolve relative to the permission file.

Each named actor permission contains the existing native editor's `window_s`, `protected_s`, `knots_s`, `tracks` and `maximum_joint_displacement_m`, plus an explicit `editable_clip_boundaries` list. A track names a skin-joint node, `rotation` or `translation`, and `maximum_change` in degrees or metres respectively. Use an empty boundary list to preserve both clip ends. Choosing `start` or `end` changes transition compatibility and requires subsequent review. The implementation accepts only existing eligible LINEAR tracks and the original native permission limits; it does not infer anatomy or editable joints.

Run in the configured model-free environment with the pinned CI dependencies:

```powershell
python scripts/native_mesh_character_fit.py path/to/permissions.json path/to/package/geometry-policy.json reports/my-fresh-correction --iterations 4 --trust 0.02 --backtracks 8
```

Use a fresh output path for every run. The outer process checks memory, owns the worker and saves a resource replay. It reserves 600 MiB of available memory, admits a 512-MiB worker only after 15 stable seconds, and limits execution to 900 seconds. `--trust` controls proposal step size, not permission or contact limits. Iterations are limited to 1–16, backtracks to 1–12 and the trust fraction to `(0, 0.25]`.

The saved source mesh scene, geometry policy and permission files must remain unchanged during execution. Files in a completed Studio package should never be edited in place.

## Correction and acceptance

- Moving targets are the actual imported surface grips transformed by their saved rigid paths. A private pose-only view feeds the existing character/contact norm model; no box or other substitute geometry is created for an imported mesh.
- The solver retains original native control bounds, sampled joint-displacement and source-rate caps. Passing point-contact rows must stay passing; failed rows cannot gain excess. Every character uses its saved animation index, source clock and placement.
- Geometry times are added to the proposal pose clock without rebuilding source-rate caps. At every declared geometry time, the current worst character vertex for each authored world plane supplies a floor constraint. Its depth cap comes from the current fully measured candidate. These witnesses are rebuilt after acceptance; rejected proposals cannot become a new reference.
- A proposal is written as a separate GLB and decoded again. Static meshes, inverse binds, unpermitted channels, native key times and frozen keys are checked. Actual native edit changes must stay within the authored limits, without using the legacy serialization allowance as extra edit freedom.
- Complete point-contact observations are saved for every probe. Candidates that pass native bounds and improve contacts undergo the entire declared geometry audit, using the original character and prop triangles. No previously passing geometry condition may fail, and no aggregate collision metric may worsen.
- Only a decoded, nonregressing proposal advances the search. Even a candidate passing all declared sampled conditions remains a diagnostic artifact: the original stays selected, and engine, semantic and animator approval remain false.

`original/` retains the source contact and geometry observations. Each `probe-*` directory retains GLBs, the candidate scene, edit audit, decoded constraints, complete contacts, decision and any executed geometry checks. `history.json` records solver and floor-witness evidence; `result.json` distinguishes a partial candidate from a candidate passing all sampled conditions. A skipped geometry audit is explicitly marked when native/contact acceptance already fails. The implementation and solver identities are archived alongside the original input hashes.

## Evidence and limits

Generated closed-mesh fixtures test moving/rotating grip clocks, exact saved-clip decoding, unchanged props and source files, frozen permissions, incompatible contacts and rejection of a closer reach that creates another mesh collision. The full-clock integration initially rejected a candidate whose floor depth worsened by about 0.0393 mm between the three test times. That run remains archived. Floor witnesses were added to guide the solver; the geometry limits and no-worsening rule were not relaxed.

All 85 focused Python tests pass, including the new full-clock regression. In `reports/mesh-character-fit-integration-v2`, two real guarded command-line jobs complete. The reachable fixture accepts three of five proposals and reduces a 10-mm gap to 1.981407 mm against the unchanged 2-mm limit. Native bounds and contacts pass; all 969 declared geometry times pass, with zero maximum penetration and no failed conditions or crossing records. This is a generated weighted closed-mesh fixture, not evidence of a professional-looking human reach.

The retained Studio scene with a roughly three-metre missed hold accepts no proposal and remains a failure. Both cases retain original selection and false engine/quality/release approval. Earlier harness import/lock failures, the contact-only full-clock rejection, and the implementation epochs remain available locally; no failed run was overwritten or represented as current evidence.

This is not a complete grasp or physical interaction solver. Imported-object collisions are verified after a proposed character change; they do not yet supply search directions. There is no prop/character joint optimization, continuous collision proof, self-collision proof, dynamics, semantic validation, engine import or animator cleanup evidence in this experiment. Arbitrary rigs and action families still need end-to-end evaluation. The whole-project release goal and all its original gates remain active.
