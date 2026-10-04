# Actor-only contact scenes

Ground contacts and character interactions can now use the same authoring,
game-track and Godot runtime workflow as object actions, without creating a prop.
This accepts supplied rigged clips and explicitly authored contacts. It does not
generate new motion, repair an interaction or establish animation quality.

## Authoring and exports

Use the existing `strep-native-scene-contacts-v1` contract with `objects: {}`.
Choose 1–8 actors, 1–64 explicit world/partner contact conditions, a shared exact
clip duration and a geometry policy. World planes remain explicit. Action names
are unrestricted; numerical contact and rig requirements still apply.

The existing CLI accepts either population:

```powershell
python scripts/native_scene_authoring_job.py plan contacts.json geometry-policy.json path/to/godot.exe recipe.json
python scripts/native_scene_authoring_job.py run recipe.json fresh-job-folder
```

An actor-only job completes `source-contacts`, `actors-engine`, then `replay`.
The saved native Godot actor resources already contain complete imported skin,
contact and geometry observations, so a second combined-object producer is not
needed. No object asset, object resource, empty object AnimationPlayer or fake
object audit is supplied. An object-edit request without a declared object is
rejected. Object-containing jobs keep their existing ordered stages and common
actor/object clock preparation.

Studio drafts use the same contract. Objects are optional in the authoring
panel. Explicit contact revisions retain their complete original draft and
portable intent sidecar in either workflow. The actor-only ZIP contains the
relative character paths, native actor resources, original contacts, geometry
policy and package receipt; it omits `objects.glb` and `animations/objects.res`.
The character GLBs remain byte-for-byte unchanged.

Game packages add the existing root-motion, contact and explicit gameplay event
tracks. For actor-only jobs, their contact measurements come from the actual
actor engine result rather than an invented combined-object report. Contact
boundaries remain non-dispatchable intent; a passing contact never silently
confirms a gameplay marker.

## Evidence and runtime contract

`verify_native_actor_scene_engine.py` binds the producer inputs, archive,
executed engine scripts, raw engine output/log, snapshots, native resources,
contact arrays and complete geometry transport. It reconstructs every imported
skin at every engine clock time and rederives contact reports, skin errors and
sampled decisions. NPZ contact/native arrays require exact dtype, shape and
bytes. Posed triangle degeneracy and every world-plane depth/peak are recomputed
from the complete imported skin. Saved geometry populations and other reductions
are checked; partner surface/containment queries remain retained producer
measurements, not independently rerun. This is evidence replay, not an
independent animator review.

The clock preserves the declared geometry policy, original native keys and all
original contact times. The validation study uses the existing full native and
phase-offset frame-population policy, with no selected-frame subset. Explicit
policies remain supported and retain their explicitly narrower scope.

Runtime configuration uses `objects: null` only for a genuinely object-free
scene. A bound `scene.json` receipt checks the exact declared actor/object
population before scene creation. Missing object configuration, empty prop
dictionaries, invented prop names, omitted real props and a changed scene hash
are rejected. The Python packager also rejects synthetic prop resources in an
actor-only game ZIP.

All actors advance on one finite absolute clock in embedded, extracted and mixed
root modes. Marker callbacks observe every actor at the marker's actual time,
even during skipped frame advances. Repeated advances, silent preview,
explicit restart, invalid times, reentrant callbacks and late participant
failure retain the existing behavior. Full participant populations are required
in saved frames, preview and callbacks. Eleven malformed configuration cases
are exercised in each actual runtime audit.

Older ordinary object job/game archives remain readable using their archived
method hashes. Only the specifically absent pre-revision method is optional for
an ordinary historical game archive; current jobs and every other method remain
required. Old outputs are never rewritten.

## Development validation

Actual CPU Godot 4.7.2 jobs complete authoring, game tracks and runtime with all
original native keys, contact times and full declared frame populations:

| Development scene | Actors / joints / vertices | Complete clock | Geometry | Contacts / scene conditions | Runtime |
| --- | --- | ---: | --- | --- | --- |
| World touch fixture | 1 / 6 / 8 | 969 | Pass | Fail | Pass in all 3 root modes |
| Partner touch fixture | 2 / 6 each / 8 each | 969 | Pass | Fail | Pass in all 3 root modes |
| Existing humanoid crawl | 1 / 19 / 3273 | 2017 | Pass | Fail | Pass in all 3 root modes |
| Existing object package regression | Original actors/prop retained | 1101 | Original evidence retained | Original decisions retained | Pass in all 3 root modes |

The procedural fixtures select the existing world/partner conditions and omit
their unrelated object grips. Every remaining contact retains its exact bounds,
timing and original intent in the revision sidecar. Their explicit development
patch changes are not anatomical labels. The paired fixture uses the same
procedural source clip on two placed actors; it tests concurrency, not natural
two-person action quality. No real humanoid high-five trial is claimed here.

The crawl keeps all four original hand/shin hold conditions. Imported position
errors are about 19.0, 71.2, 78.5 and 78.1 mm against the original 20 mm limit;
maximum relative speeds are 0.191, 0.541, 0.273 and 0.276 m/s against 0.005 m/s.
Its maximum imported full-skin position error is 0.08964 mm against 0.1 mm.
Geometry and skin fidelity pass, while the contact/whole-scene decision remains
false. Correct finite playback preserves those defects; it does not repair them.

Each actor-only runtime traverses every frame in embedded, extracted and mixed
root modes, retains original bytes, rejects all eleven malformed configurations
and checks initial, midpoint and terminal development marker callbacks across
four traversal scenarios. Marker-time pose differences are zero. These three
confirmed markers test the dispatcher, not the semantics of a grasp or impact.
The existing object regression retains its five original dispatchable markers.

Bound local evidence is in `reports/native-actor-scene-validation-v1/`.
Its three scene jobs and corresponding game jobs are named
`actor-only-world-v1`, `actor-only-partner-v1` and `actor-only-crawl-v1` under the
existing ignored namespaces. The original actual jobs keep their archived
verifier. The current strengthened verifier separately replays those same raw
producers under `reports/native-actor-plane-replay-v1/`; it does not rerun the
model, engine or expensive geometry producer. Final receipts bind both stages
and make that implementation distinction explicit.

The strengthened replay checks all 4,924 actor/plane observations across the
three retained producers and rederives every posed triangle degeneracy list.
All contact/native arrays remain exact and all three failed scene decisions
remain false. A model-free test rejects a changed plane depth even when the
report's hash is updated. Related Python verification covers 234 unique cases,
with three offline Node editor workflows and four desktop-build checks. Initial
runtime-fixture failures and the obsolete test requiring an artificial prop are
retained in local logs; corrected tests pass. All fourteen release capability
evidence lists and acceptance fields remain unchanged; proposed release gates
still require calibration and approval.

All raw source payloads, engine outputs, numeric arrays and ZIP files remain
under ignored `reports/`. These are development trials, not reserved held-out
release evidence. Existing ordinary object packages remain unchanged and
readable. No model, animation, new seed or trained update is produced. No live
Studio restart/HTTP, GPU rendering or submitted human review is claimed.

Physics, continuous collision, independent two-person motion quality, looping,
transition playback, frame-rate performance, GPU rendering and human cleanup
tests remain separate requirements. The full project goal remains active.
