# Supplied-rig body, object and partner contact measurements

`native_scene_contacts.py` measures explicit points on existing animated GLB
skins against world targets, moving primitive surfaces or another actor's skin.
It accepts arbitrary body vertex references without requiring SOMA joint names
or a leg mapping. This read-only path makes contact conditions measurable after
rig transfer; it does not generate or correct an interaction.

## Authoring and execution

```powershell
.venv\Scripts\python.exe scripts/native_scene_contacts.py path/to/contacts.json reports/new-native-scene-audit
```

Use a fresh output directory. The request schema is
`strep-native-scene-contacts-v1`, with exactly `schema`, `duration_s`, `actors`,
`objects` and `contacts`. All actors must share the exact selected animation
duration, at most 30 seconds. Retiming remains an explicit prior operation.

Each actor has `glb` (relative to the request or absolute), its exact `sha256`,
`animation_index`, and a rigid `placement` containing `translation_m` and a
unit `rotation_xyzw`. One validated embedded skin and the existing rig-reader
restrictions apply to each actor. No name-based anatomy inference is performed.

Each contact declares:

| Field | Required meaning |
| --- | --- |
| `id`, `actor` | Distinct condition ID and existing effector actor. |
| `vertices` | Distinct `[mesh node, primitive, vertex]` references in the bound GLB. |
| `reduction` | `individual` for separate corresponding points, or `centroid` for the explicit arithmetic mean of the selected vertices. |
| `target` | A world, object or partner correspondence as described below. |
| `mode`, `interval_s` | `touch` at one exact time `[t,t]`, or `hold` across a positive closed interval `[start,end]`. |
| `limits` | Nonnegative `position_m`; holds additionally require `relative_speed_m_s`. |

World targets contain `space: "world"` and `points_m`, one point per measured
effector point. Object targets additionally name `object`; their `points_m`
are object-local and must lie on its declared primitive surface within the
existing one-micrometre surface representation tolerance. Partner targets use
`space: "actor"`, another `actor`, its explicit `vertices` and `reduction`.
The resulting point counts must match. Ordering defines correspondence;
nearest-vertex changes cannot hide failed contact.

Objects have explicit versioned `geometry` descriptors (box, sphere or cylinder)
and `keyframes`. Each key has `time_s`, `translation_m` and `rotation_xyzw`.
One key at zero denotes a static object; a moving track must cover the whole
clip. Translation is linear and rotation uses SLERP. Geometry is required to
validate the authored surface points, but whole-body collision is not measured.

For example, an exact partner touch contact is:

```json
{
  "id": "hand-meeting",
  "actor": "A",
  "vertices": [[12, 0, 31]],
  "reduction": "individual",
  "target": {
    "space": "actor",
    "actor": "B",
    "vertices": [[18, 0, 42]],
    "reduction": "individual"
  },
  "mode": "touch",
  "interval_s": [2.5, 2.5],
  "limits": {"position_m": 0.005}
}
```

The example requires those references to exist in the separately declared,
hash-bound actor files; it is not an anatomical label or a complete request.
Up to eight actors, 32 objects, 64 conditions and 256 vertices per patch are
supported. Unknown fields, changed sources, unmatched correspondences, malformed
poses, boolean numeric fields and invalid clocks reject.

## Measurement contract

Holds measure position error at exact boundaries, actor native keys, object
pose keys and every predeclared 30/60/120 Hz population with phases
0, 0.25, 0.5 and 0.75 frames. Relative speed uses consecutive ticks separately
within each of those twelve clocks; it never differentiates the union of keys
and frame clocks. A clock with fewer than two ticks remains unavailable and
fails a held condition. A touch measures position at its exact time and does
not request a hold-speed check.

The shared sampling contract identifies the frame populations. This scene audit
does not execute the existing foot-specific legacy velocity, motion-rate or
edit-permission audits; its `passed` result cannot override those separate gates.

Object error vectors are expressed in the object's moving local frame before
speed is calculated. A constant local grip offset must not appear to slide
merely because the object rotates. World and partner conditions measure the
world difference of corresponding point tracks. Nonzero partner offsets can
therefore change speed when rotating; no hidden partner-local frame is inferred.

Every declared correspondence and condition must pass. Centroid contact is
explicitly separate from individual vertex contact: a stationary mean can hide
movement of individual vertices. Neither establishes distributed contact area,
palm orientation, anatomical correctness, support, forces or balance.

The output snapshots the request, source GLBs and implementation files, hashes
the numerical observations and records runtime versions. Saved arrays include
sample times, effector and target world positions, and error vectors. Skinning
retains all loaded positive/repeated influences and primitives, including eight
slots; the existing loader's weight normalization is explicitly recorded.
Original GLBs are unchanged. No corrected candidate is selected and all quality,
training and release approvals remain false. Actual engine or GPU skin playback,
continuous contact and collision remain separate evidence requirements.

## Development observations

Fourteen retained development scenes were audited: five high-five touches,
five handshake holds, original/candidate crawl proxies and baseline/candidate
sphere grips. These are existing generated or corrected clips, not new inference,
new seeds, formal held-out coverage or human review. Their original authored
position limits are retained. A new, explicitly declared 5 mm/s relative-speed
limit applies to holds; it does not retroactively replace an earlier protocol.

The high-five errors range from 206.23 to 1175.13 mm against 30 mm. Handshake
maximum errors range from 1022.40 to 1136.64 mm; relative speeds range from
2268.62 to 3007.27 mm/s. Every condition fails. These unchanged baseline failures
cannot be presented as solved partner interactions.

Crawl uses the existing geometric shin/hand proxy centroids and 20 mm position
limit across inclusive native keys 54–56. This is not the earlier half-open
full-frame hold. The left shin meets the position limit in both versions, but
all four held conditions fail the additional speed limit. The candidate's
left-shin speed is 191.38 mm/s; other candidate peaks are 541.48, 272.88 and
275.88 mm/s. No claim is made that these proxy labels or simultaneous stationary
supports are anatomically appropriate.

The sphere baseline fails both anchors and speed. Its existing corrected clip
meets both 5 mm position limits, at 2.2193 and 2.2468 mm. Left relative speed is
3.7562 mm/s and passes; right is 10.1976 mm/s and fails. Position success alone
therefore does not establish a stable two-hand hold. The earlier distributed
region, normal and clearance checks are not rerun by this point audit.

The first study wrapper incorrectly assumed a handshake was a single-time
touch and stopped after five high-five audits. That failed attempt remains in
`reports/native-scene-contact-development-v1`. The corrected wrapper preserves
the actual handshake interval in fresh `reports/native-scene-contact-development-v2`.
No inputs or acceptance limits were changed to turn a failed contact into a pass.

Portable tests and an independent full-skin replay validate these measurements.
All 115 focused checks pass in the project environment; the 37 new scene-contact
checks also pass separately in the model-free environment. An initial broader
model-free run passed 114 checks but failed one existing asset-export test because
that export lazily imports Torch. The same complete 115-test population was
then rerun successfully with the installed project dependencies; no check was
removed or acceptance threshold changed.

The independent decoder reproduces all 9,425 sampled contact points across
22 conditions, with a maximum coordinate difference of 6.66e-16 metres, and
replays all 204 frame-clock populations exactly. It checks all 234 saved audit
files and original source hashes. Evidence is in
`reports/native-scene-contact-development-v2/verification.json` and
`reports/native-scene-contact-validation-v2/checks.json`. These counts are CPU
point measurements, not engine observations or additional generated animations.

Source snapshots, exported observations, per-clock numeric reductions and
method archives remain available locally. After measurement, three validation
guards were hardened to reject list-valued actor/object identities cleanly;
the verifier checks that these are the only source differences from the archived
measurement revision. No computational method or result was changed.

The next integration is an executable body/scene constraint and correction path
for supplied rigs using explicit edit permissions and existing motion bounds,
followed by actual imported-skin contact checks and developer/animator review.
This audit supplies measurements for that work. All fourteen release capabilities
and the original full-project goal remain open.
