# Combined contact correction: import and developer review

The two-finger development candidate passes actual decoded motion and point-contact checks against the original source-derived caps. All 2,066 authored facing failures remain. The complete native mesh audit now passes all 2,552 samples, with 1,942 fresh measurements and 610 exact full-input reuses. Both exact original process exits are zero. The serial whole-scene engine job has started; final imported-surface results remain pending. This document records the validation contract, not a successful import or solved grasp.

The study concerns one humanoid and two spheres. The object named `box` is a sphere with radius .25 m; the second sphere has radius .20 m. It does not establish a box pickup or partner interaction. Contact references, object geometry and paths, placements, timing, limits and all unselected native controls remain unchanged. These existing APIs accept other supplied actions and world/object/partner contacts through their schemas; action names are not a whitelist.

## Serial execution contract

The private development supervisor acquires the exact existing mesh worker's Windows handles, including kernel creation FILETIMEs and image identity. It waits without owning the production lock. It cannot replace the mesh worker or start an engine until both original processes exit zero, the complete bound geometry result passes, all 2,552 original geometry samples are accounted for, and the independently decoded original-source and baseline contact guards pass. The retained development controls must identify the exact measured candidate.

The complete mesh archive, logical array receipts, runtime, methods and original input chain are checked after those exits under the single production lock. Fresh geometry and exact full-input reuse remain distinct. A failed mesh sample, incomplete population, changed source, changed method or premature approval stops the follow-up and preserves failure evidence. It does not reset source caps or widen a tolerance to make engine work eligible.

The existing public authoring and imported-surface APIs then run serially:

```powershell
python scripts/native_scene_authoring_job.py plan CONTACTS.json GEOMETRY_POLICY.json GODOT_CONSOLE.exe FRESH_RECIPE.json
python scripts/native_scene_authoring_job.py run FRESH_RECIPE.json FRESH_ENGINE_FOLDER
python scripts/native_imported_surface_contact.py audit CONTACTS.json SURFACE_POLICY.json FRESH_ENGINE_FOLDER/objects-common/common-policy.json FRESH_ENGINE_FOLDER/actors-engine FRESH_SURFACE_FOLDER --object-dir FRESH_ENGINE_FOLDER/objects-engine
python scripts/native_imported_surface_contact.py verify FRESH_SURFACE_FOLDER
```

These example commands concern a scene with objects and no further object fitting. All output paths must be fresh and the production worker idle at execution. Use the exact measured candidate contacts and a surface policy whose only changed field is its contact-file hash. The target normals, their coordinate systems and every facing/side limit remain the original authored intent. Planning a recipe does not satisfy the upstream motion/mesh prerequisites described above.

The authoring job preserves separate actual object import, actor import, complete imported geometry and saved-replay results. The subsequent surface audit uses those actual imported trajectories and reloaded object poses, preserving source-native, default-import and native-authoring observations. Every mode retains all 4,132 contact samples and 10,330 point/normal observations. Its replay recomputes the complete contact/normal decisions with the same surface kernel; it is not an independently implemented geometric or physical oracle.

The combined sampled decision requires both engine point/geometry conditions and native/imported facing conditions. Numeric failures remain measurable even when execution completes successfully. Original Studio selection stays in place. Engine sampling and cache integrity do not establish anatomical contact, force balance, continuous/self collision, real-time playback, GPU appearance, animation correctness or professional quality. Training admission and release approval remain false.

## Supervisor validation and current state

The corrected private supervisor passes **48 small gate/identity checks**, using counterfactual terminal records and test handles. Cases reject nonzero/live-sentinel exits, hidden facing failures, incomplete native/surface/geometry populations, changed permitted channels, recentered caps, regressed maximum error, nonfinite scores, changed images and changed kernel creation ticks. These are supervisor checks; no production geometry, engine or model executes in them.

Two earlier attachments are preserved as failures. Python 3.10 rejects the seven-digit fractional timestamp supplied by PowerShell's .NET formatter. After parsing that representation, a direct exact-tick comparison still rejects because CIM's creation-date conversion truncates the original FILETIME to microseconds: each observed kernel value has one additional 100 ns tick. The final supervisor pins a separate acquired kernel observation and compares every original tick exactly; the CIM timestamp is only an additional check at its actual precision. Both failed attachments close their handles and create no queue or engine output. No original worker is restarted.

The final supervisor acquired and consumed both original mesh handles with zero exits, verified the complete bound archive and retained development controls, and started the whole-scene engine job serially. Final engine/imported-surface results remain pending; original Studio selection is preserved. Gate-check receipt SHA256: `26fc4df4aeda94afd5eb2c2b3dfd4cd69cbd010d801710fa4741a7c9b24ccfac`.

## First developer inspection

A separate local review packet provides the original retained actor at **4.000 s**, with three orthographic hand crops and two body-context views. It is an unblinded contact-intent inspection, not a review of the new combined candidate or the complete animation. The body figure displays all 18,056 saved vertices and 36,108 triangles; the primary sphere is a projected outline and the second prop is omitted. Contact overlays and approximate depth ordering are display aids, not collision measurements.

Both figures derive from the same previously checked saved mesh snapshot. They generate no new pose, skinning or collision query and use the CPU Agg backend, without engine/GPU rendering. Request, snapshot, plotter and image hashes are recorded locally. Declared hand-subtree influence supplies the display crop; it does not identify an anatomical palm. Point 0 and neighbour points 1–4 remain the original references.

The developer is asked to clarify the intended grasp before replacement anatomical patches or target normals are authored. A response can establish that intent; it cannot silently rewrite prior benchmark evidence or count as a blind animation rating or timed cleanup test. Anatomical selection, full-motion review, held-out generalization and cleanup-time evidence remain outstanding. Review answers are empty, real human rating/cleanup counts remain zero, and all fourteen release evidence arrays remain empty.

Raw receipts, supervisor versions, failed attachments and figures remain under ignored local `reports/`. The public repository contains this reproducible API contract and concise evidence summaries; it does not bundle private studies, downloaded characters, models or local dependencies. The single full-project goal remains active.

Completed combined mesh result SHA256: `e31e362ff2b054623c6d143d9c53b1dad39cd6205e20e497105d8579cf8bd039`.
