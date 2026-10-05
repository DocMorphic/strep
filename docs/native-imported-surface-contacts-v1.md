# Surface contacts after game-engine import

`scripts/native_imported_surface_contact.py` adds the authored normal-opposition and side conditions to imported skin observations. Point distances and surface normals use the same imported trajectory. This preserves failures that an engine position-only contact pass cannot resolve. It changes no animation, scene selection, contact schedule or acceptance limit.

## Reproducible commands

First complete the existing actor and, when declared, object engine producers with the exact source contacts and common geometry policy. Their receipts must bind raw engine output, saved Animation resources, complete clocks, source snapshots, imported topology/skinning and methods. The new audit rejects incomplete or mixed producers.

```powershell
python scripts/native_imported_surface_contact.py audit CONTACTS.json SURFACE_POLICY.json COMMON_GEOMETRY_POLICY.json ACTOR_ENGINE_OUTPUT FRESH_OUTPUT --object-dir OBJECT_ENGINE_OUTPUT
python scripts/native_imported_surface_contact.py verify FRESH_OUTPUT
```

For a scene with no declared objects, omit `--object-dir`; the complete actor-only producer is required, including every partner actor. A scene with objects must supply the actual object producer. There is no fabricated object fallback.

The surface policy is the existing `strep-native-surface-contact-v1` contract. It binds the exact contacts file, explicitly declares target normals for world/object contacts, derives partner normals from the exact target skin references, covers every contact and sets the complete pose-query budget. If animation edits change the contacts binding, create a separate derived policy changing only `contacts_sha256`; preserve the original normals, limits, budget and original receipt.

## What the audit measures

The original native orientation/side result remains a separate report. The imported report uses raw imported skin weights and the saved actor animation poses. For object scenes, both the default object import and native object authoring resource are evaluated separately with the same imported actor trajectory. The default comparison is not a default-import actor test. Source and partner placements are applied after skin reconstruction.

Normals follow the complete original incident-triangle population and canonical source winding. The producer checks correspondence through vertex, joint-slot and globally reversed winding reorderings before those imported positions are used. This yields an orientation comparison in the original authored convention; it does not claim that mesh winding identifies an anatomical palm or outward solid-volume normal.

All original contact times and point-contact semantics remain in force, including relative-speed populations for holds. Point observations, normals and side projections share the imported trajectory. Target object normals use the actual object's rotation at that time, so matching a grip position cannot hide an incorrect object orientation. Missing clock samples, missing vertices, unreliable normals and excessive budgets fail rather than silently substituting native observations or partial results. Counts distinguish unavailable normals, orientation/side failures and the point-contact result. The combined surface decision requires both source-native and imported native-authoring conditions; failed default comparisons remain visible.

The saved output includes all mode reports, normal/time arrays, source snapshots, archived methods and bindings. Verification rederives every normal, point-contact decision and reduction from the bound producers, checks exact array bytes and JSON types, and detects changes during replay. It shares the original surface/skin kernels and does not independently reimplement them. Verification currently requires the original producer paths and matching current methods; it is not a standalone portable engine bundle.

No engine is launched by this command. It reads completed headless observations and saved resources, computes CPU skin and surface normals, and performs no new collision query. Complete geometry, native dynamics, runtime events, physics, GPU appearance, real-time playback, anatomical review and human cleanup remain separate checks. Every quality, training-admission and release flag remains false.

## Development study in progress

**Update at 2026-10-05 06:33 UTC:** The actual actor stage has completed all 2,552 samples. Selected native animation poses, imported point contacts, complete raw-weight skin correspondence and declared sampled geometry pass their original limits. The maximum imported/native vertex position error is **9.515027686229957e-5 m**, below the unchanged **1e-4 m** tolerance; maximum pose-element error is **7.336078075015351e-7**. The producer checks all **18,056 vertices and 36,108 triangles**, reporting the engine's global winding reversal. Actor-stage receipt SHA256: `ea1eb56ba98a7147aafb86d8edc412e754309fe1f1b1912dba2414ff730fa1eb`. Combined actual actor/object geometry, saved-data replay and the exact-exit-gated surface follow-up remain pending. This stage does not measure the separate authored surface-orientation policy and grants no quality approval.

The retained seeded correction has passed its full independent native/contact/geometry replay. Its separate actual Godot job started at **2026-10-05 05:50:34 UTC**, using the exact retained actor bytes and original contact/geometry limits. The native point audit, object export, common-clock preparation, actual object resource import and actor full-skin/sampled geometry have completed; combined imported actor/object geometry and saved-data replay form the remaining serial stages. The original engine-job handles and a separate owning observer remain active. The surface follow-up is now queued on the exact live owning-observer handles. It runs the complete surface audit and replay only after exact successful original engine-job exits and complete bound receipts are available; the existence of a lock or stale state file cannot trigger a replacement job. The queued policy changes only the contact-file hash, preserving all original normals, limits and budgets.

This is one humanoid with two spheres. The source correction still has 2,066 orientation failures, and the earlier source geometry pass is not an imported geometry result. No new complete engine, imported surface, partner, box-pickup, rendering or human result is claimed while these stages remain pending. All fourteen release evidence arrays remain empty; real human ratings and cleanup records remain zero.

The completed object-resource producer records **2,552 samples** and passes its original **1e-6 m position / 1e-6 basis-component limits**. The largest position error is **4.202302900213686e-7 m** on `moving-prop`; the largest basis error is **1.3744180316077603e-7** on the sphere named `box`. These are actual reloaded native object-resource authoring seeks against the native actor snapshot, not imported actor contact or full scene geometry results. Receipt: `reports/seeded-fraction-scene-engine-v1/objects-engine/result.json`, SHA256 `46b41b928bdcb97744894c995c7f6d6eec11e8c0cd248e9af8ccb5f91356690f`. Raw execution receipts pin Godot 4.7.2 and all executed scripts. The default import comparison remains separately recorded.

## Source validation

All **31 new checks pass in 72.89 seconds** in an isolated public-source copy, without models, vendor or downloaded character payloads. They cover actual tiny GLB decoding, canonical winding, world/partner contacts, full hold clocks, imported point/normal consistency, object rotations, missing clocks/vertices/modes, resource bindings, complete replay, JSON type changes and mutations during verification. Engine execution in these fixtures is explicitly mocked; they are not the actual Godot study above.

An earlier combined run passed **105 existing surface/engine/combined-replay regressions** and 30 new checks. Its one failure was a new assertion expecting an error containing `changed`, while the correct rejection said `differs`. The failed trace is preserved. Only that assertion's exact bytes were widened; the fresh 31-check pass and byte-verified unchanged older sources establish **136 covered checks across the two runs**, not one green 136-test invocation. Original and copied source hashes remain unchanged. Both the new tests and existing regressions are included in Windows/Linux CI; the new revision's CI result remains pending.

Corrected source receipt: `reports/imported-surface-source-check-v2/result.json`, SHA256 `3b7f6dcd9de70a303462465c73a59ff5319500baa2234d45e39c3a1e0ce949d6`. Earlier trace: `reports/imported-surface-source-check-v1/pytest.log`. Private evidence stays excluded from Git. The public code is frozen while the queued production study waits or runs.
