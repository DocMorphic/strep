# Complete surface geometry for native support audits

The native support engine and imported-skin auditors now preserve every skinned
primitive in the validated single-skin character. Four/eight influence slots
can coexist: smaller layouts receive zero-weight padding, without changing
weights or dropping vertices. Surface offsets and original node/primitive/vertex
references remain explicit. Single-primitive arrays equal the legacy arrays.
The subsequent [rig fitting study](native-support-rigs-v1.md) connects this
representation to native fitting and tests actual multi-surface Godot imports.

Imported surfaces must have one unique complete correspondence to all source
primitives, based on positions, effective weights and inverse binds. Surface,
vertex and bind reordering are allowed. Missing, duplicated, ambiguous or
incompatible surfaces reject reconstruction. Existing rest/bind/weight limits
stay unchanged. Actual imported weights remain unrenormalized. Each matched
surface receives its own diagnostic and contributes to reconstructed vertices
and fully foot-owned support regions.

Twenty new CPU tests exercise mixed influence layouts, exact legacy parity,
independent skinning/projection/derivatives, positive influence ownership,
unique matching with locally ambiguous choices, bad/missing surfaces and both
auditors' full-region height measurements. The multi-surface test geometry is
an in-memory extension of a loaded fixture, not an actual Godot import result.
All 1,363 preceding Python checks and 14 JavaScript suites pass on the updated
auditors; the 20 additional tests pass separately, for 1,383 Python checks in
total. Both new suites are included in the public Windows/Linux CI workflow.
Preceding commit `ab0c8c9` passed both hosted platforms (run 36956569989).

## Existing development geometry

The model-free audit reuses 21 previously examined clips: seven actions across
CesiumMan and Quaternius female/male characters. These are three assets across
two rig families, not three independently designed rigs. The actions are
jump/land, crawl, dance, wave, kick, get-up and run/roll/stand. They are examples
for this measurement, not a supported-action whitelist. No new model seeds or
held-out clips are generated or consumed.

CesiumMan has one primitive, 19 bones and 3,273 vertices; the Quaternius assets
have three primitives and 65 bones, with 8,844/8,483 vertices. At every original
key and midpoint, 6,099 poses and 41,879,800 vertex observations agree with
independent `RigAsset.vertices` skinning. Maximum vertex component and arbitrary
axis projection errors are 7.106e-15 m. These numerical comparisons establish
geometry preservation, not a motion-quality threshold.

The initial regional diagnostic incorrectly supplied Cesium's saved foot names
where integer indices were required. That instrument error remains archived.
A separate follow-up resolves the explicit saved mappings by unique name or
validated index. Fully foot-owned populations are 52/53, 275/275 and 250/250
vertices respectively. All 6,099 corrected regional poses agree with independent
foot projection within 6.662e-16 m. No anatomical mapping is inferred, stance
annotation added or support correction performed by these geometry audits.

All 109 bound geometry/profile/method/diagnostic files rehash without mismatch.
Result hashes:

- Geometry: `937c998502642442385089d5e06f47be7ed76916fe64bbc3471018726bdd4d36`.
- Regional follow-up: `369b84f803c34b5e02b4b067cfc28d74d7507278d238fea63e0282a1c8b3e8ef`.
- Rehash: `a42f41844d7fef1fb15e669a2eb24675c1b2eb3a50314ab2a51e672b33677f96`.

## Completed strict coordinate repair

The previously running strict coordinate study completed before solver methods
were changed. It uses four optimizer variants on one development clip/rig,
warm-started from the strict minimax study, eight iterations and a 2e-7-radian
coordinate trust radius. It executes 108,822 numerical screens and preserves
36 independently decoded GLB probes. All four proposals pass sampled support
and preservation screens across 701 times and 142 stance samples per foot.
Every final bin/absolute-peak selection still fails; the exact input is retained.

| Trial | Failed rate bins: speed/acceleration/angular speed/angular acceleration | Peak-regressing joints in the same order | Final worst normalized excess |
| --- | --- | --- | --- |
| 0 | 67 / 13 / 25 / 14 | 1 / 1 / 5 / 2 | .0036939692 |
| 1 | 2 / 0 / 0 / 0 | 0 / 0 / 2 / 1 | .0000010472 |
| 2 | 76 / 9 / 19 / 14 | 1 / 0 / 3 / 4 | .0109437229 |
| 3 | 59 / 14 / 14 / 11 | 0 / 1 / 3 / 1 | .0010338083 |

All four saved final controls replay their GLBs byte-for-byte. Rounded-proxy
versus decoded pose component error stays below 9.993e-16; normalized constraint
error stays below 1.226e-11. Every independent bin and peak decision reproduces.
All 1,791 bound ancestor, study and replay files rehash without mismatch.

- Fit: `3f4d0941aed25509d487d92ee12e5889060a17236f669c8daefb6672788c913a`.
- Replay: `8e815e96398c96aae82c3b90028ad43646179f67af04c277bd5d8761fda23e5c`.
- Rehash: `caebc669a654b12c3713aa598abc7fe3560498c7c6fa5d80bb59a63c219ef371`.

This initial surface audit did not execute multi-surface support fitting or
Godot imports. Subsequent results are recorded separately in the rig study.
Existing single-surface engine evidence remains separate. Ground-zero
support bounds, continuous contact, collision/balance, broader action/scene
quality and timed human cleanup remain unresolved. No model training or release
approval occurred; all 14 capabilities remain unapproved under the active
full-project goal. Generated studies and third-party payloads remain local and
ignored by the public source repository.
