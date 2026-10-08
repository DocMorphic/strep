# Opt-in Studio precision exports

Studio's **Characters → Godot export precision** panel builds a separate copy of
a completed native scene or game package. It uses the checked weight encoding
described in [Godot weight derivatives](godot-weight-derivative-v1.md). Originals
remain selected, and the complete original ZIP is included intact in the new
package. This is an export option, not a motion generator or quality approval.

1. Refresh, choose Scene or Game with root/events, and select a completed package.
2. Use selected package to bind its current receipt, assets, engine and clock.
3. Build precision copy, then refresh and show the measured results.
4. A separate checked ZIP appears only when every applicable measured stage
   passes. Failed jobs retain the original package, derivative actors and
   precision diagnostics; they cannot expose a checked ZIP.

The source must be an existing completed Studio native scene/game package.
Unsupported skin encodings reject explicitly. The option does not silently
replace existing export defaults or select its derivative as a new character.

## What is preserved and measured

The worker snapshots the original assets, source package, active contact intent,
geometry policy, source clock and implementation. Derivatives change only checked
joint/weight coefficient pairs. Selected animations, timing, actor placement,
object geometry/motion, targets and tolerances remain unchanged. Any inherited
normal intent must be resolvable; otherwise the request rejects before export.

Each proposal gets a fresh headless Godot import, simultaneous actor/object
playback, complete sampled triangle/volume/declared-plane evaluation and saved
resource replay. Every original skin vertex is compared at every original
sample to the **original** skin, with the unchanged 100 µm displacement screen.
The quantized derivative never becomes its own fidelity reference. Inherited
surface conditions are freshly checked when present. Game packages regenerate
the original root choices, contact tracks and explicit event markers, then run
the event helper through actual finite-clock dispatch scenarios. Root tracks are
references; motion remains embedded in the actor animation.

Terminal receipt readers check typed decisions, source/method archives, the
complete file population, numeric fidelity archives, original clock, measured
stage gates and ZIP payloads. Downloads are restricted to the fixed receipt
population. Stale source bindings, duplicate submissions and ambiguous read
queries reject. These protections do not make local editable receipts a signed
or adversarially secure attestation system.

## Development checks on 2026-10-08

Actual Godot 4.7.2 engine checks completed for three source-bound jobs:

| Development source | Actors / clock samples | Outcome |
| --- | --- | --- |
| Actor-only world contact | 1 / 969 | Original-skin fidelity passes; scene conditions fail; no checked ZIP |
| Procedural two-character/object scene | 2 / 1,101 each | Fresh scene geometry, saved replay and original-skin fidelity pass; checked scene ZIP |
| Same procedural game package | 2 / 1,101 each | Same scene checks plus regenerated roots and four actual event-dispatch scenarios pass; checked game ZIP |

The procedural actors are eight-vertex closed engineering fixtures. Their maximum
original-reference displacement is approximately 0.060 µm. These three checks
validate the workflow and failure gate, not humanoid motion quality. Full SOMA
precision measurements remain separately reported in the weight-derivative
study. The browser was checked against the actual local server for source
binding, terminal results and the fixed download list, with no console errors
observed during those interactions. A passing inherited-normal fixture uses
explicitly mocked engine observations and is labeled accordingly in its test.

The local canary preserves source/result, asset, implementation and output hashes
under ignored reports. It completed within the existing one-hour / 7 GiB process
tree / 600 MiB available-memory guard. Local integration checks cover 150 distinct
Python tests across the export, native scene, game and surface workflows, and all
38 registered browserless Node scripts pass. Hosted checks of the previously
published commit were still running when this work was validated; local results
are not a hosted CI success claim. All quality, release, training, physics,
GPU and continuous-collision approval flags remain false. No independent animator
review, held-out motion evidence, cleanup-time improvement, physical attachment
or comprehensive runtime collision proof is supplied by this export feature.
