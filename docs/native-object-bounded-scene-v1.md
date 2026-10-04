# Bounded object motion with complete imported character checks

The experimental bounded-scene CLI joins [bounded fitting and rigid-object
export](native-object-bounded-fit-v1.md) with the existing [imported scene
checks](native-object-scene-engine-v1.md). A passing rigid object handoff is
only an input requirement; the character's imported motion and complete
declared scene still have to pass their own conditions.

```text
python scripts/native_object_bounded_scene.py passing-fit passing-object-handoff fresh-output --engine path/to/godot
```

The fit and object handoff must be complete and bound to the same checkpointed
proposal and engine executable, with unchanged recorded implementations,
source actors, contact intent, saved observations and geometry. Preflight
checks the original author scene, allows only byte-identical actor path
rebasing, and reconstructs all three saved object-epoch reports and actual
object pose/contact decisions. Altered summaries cannot substitute for their raw
observations. Original-relative movement limits and protected original poses
are preserved; initialization cannot reset the original epoch.

The command imports the unchanged character animation through headless native
Godot authoring on the complete object handoff clock. It archives imported
skin functions, triangle topology, weights, bone observations and Animation
resources. Raw imported weights are not renormalized. The actor producer has
its own contact, pose, full-skin and geometry report; its observations are
then combined with the **actual** object-resource transforms from the bound
handoff. Complete scene geometry is queried again for those combined
observations, rather than copied from the source fit or actor producer.

Read-only scene verification reconstructs all imported skin/contact/object
pose observations and checks every saved triangle-array reduction. It does
not repeat the expensive geometry queries. Producer receipt binding,
containment observations and shared imported-skin reconstruction remain
explicit dependencies. Both default-import and native-authoring object
comparisons are retained.

Object contact and pose fidelity remain separate conditions. For example,
default import may still reach a grip within its 5 mm contact limit while
exceeding the 1 micrometre object-transform fidelity limit. The combined
pose/contact decision retains that failure without rejecting an otherwise
valid native-authoring handoff.

The final decision requires the original bounded object handoff, the complete
combined scene conditions and the saved-result replay to pass together. A
terminal run can report a numerical failure; it preserves all outputs and
keeps the original selected. An execution error leaves a failed pipeline with
its stage outputs intact. Each child stage uses the existing single-worker
lock, and preflight/final handoff checks use that same lock. All output paths
must be fresh.

This remains a CPU/headless authoring operation. It does not certify continuous
collision, self/object-object collision, dynamics, normal-force/grasp stability,
GPU appearance, real-time playback, gameplay-event dispatch or human action
quality. No passing decision changes Studio selection, admits training data,
adds release evidence or marks the full project goal complete.

## Validation

All 11 focused workflow tests pass. Small procedural fixtures exercise the entire workflow with explicitly mocked
engine observations. They check passing full-scene composition and replay,
retained default-import failure, and rejection when actor motion drifts despite
a passing rigid-object handoff. Preflight rejects pending/failed jobs, another
engine, changed original motion, forged epoch summaries, changed raw clocks
and archived-method drift before starting actor import. These fixtures are
orchestration checks, not actual Godot execution or realistic-motion evidence.

The passing fixture uses a constant original object/actor path and binary
edit endpoints so its exterior values remain exactly representable. The
earlier moving-path fixture exposes `6.780e-11` exterior component drift after
export and is explicitly tested as a rejected input. That fixture change
does not loosen the production exterior-preservation gate.

The retained humanoid follow-up uses the existing ten-point sphere fit and
2,201-time object handoff. Actual imported character/scene results will be
reported only after those workers finish and the full saved-result replay
completes. Earlier fit/import failures and all release requirements remain
unchanged.
