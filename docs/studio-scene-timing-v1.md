# Studio scene timing edits

Saved scenes now expose **Trim and timing** with a range trim or a speed multiplier. The duration display reports the actual speed after rounding to native frames. All participants, props and event clocks change together. Immutable source snapshots, revision checks, job recovery, contact measurements and downloadable engine packages use the existing scene-edit worker. Retiming supports 3–901 native frames; it changes recorded paths in time without re-simulating forces or gravity.

Retimed LINEAR/STEP exports can be trimmed without replacing the source mesh, rig or interior curve keys. Cut boundaries are sampled explicitly. Fractional events and terminal-hold events retain their timing. Precise contact windows survive retime → trim → retime without accumulating integer enclosure error; excluded contacts remain provenance.

Nonuniform export clocks use runtime schema v3 with hashed, GLB-bound authored TRS curves. Godot restores those keys on unambiguously matched imported tracks before exposing participants. Wrong hashes, wrong source bindings, duplicate tracks and keys collapsed by engine precision are rejected. Uniform clocks retain the existing v1/v2 import path. Native arrays still use 30 fps.

## Retained validation

| Study | Scope | Passing Godot pose observations |
| --- | --- | ---: |
| `scene-trim-retimed-v1` | Retimed pair, release, moving platform, plus native-clock control | 1,140 |
| `studio-scene-timing-v1` | Real saved-scene workers: paired 120 → 223 frames, trim 20–190, retime 171 → 137 | 1,228 |
| `scene-trim-precision-v1` | Actor/box regression after float64 cut-boundary correction | 205 |
| `scene-trim-precision-guard-v1` | Same regression after rejecting engine-collapsed keys | 205 |

The four-scene study checks 3,848 decoded curve samples with maximum matrix component discrepancy below 9.64e-7. The Studio chain verifies snapshots, download paths, exact contact provenance and refreshed measurements; its maximum engine actor discrepancy is below 1.13e-6. The final actor/box regression is below 6.32e-7 / 1.88e-7. Shared transport, marker ordering, exact callback clocks, callback mutation rejection and unload pass. These studies retain distinct implementation hashes; earlier reports are not overwritten when code changes.

A synthetic STEP edge case exposed a real failure: a key 1.74 nanoseconds after the cut survived glTF export but Godot merged it into the initial key. The original failed probe remains recorded. The final runtime rejects that collapse; a normally spaced STEP curve passes before/after-jump sampling. This is a supported-limit rejection, not a claim that Godot preserves arbitrarily close discontinuities.

Sixty-four focused Python tests and the offline Node editor check pass. No HTTP, browser rendering, animator approval or new motion generation is claimed. CUBICSPLINE trimming, generic imported rigs, variable tempo and physically re-simulated timing remain open. Existing contact/collision failures and all fourteen unapproved release capabilities remain visible.
