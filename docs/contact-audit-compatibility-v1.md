# Contact-edit audit compatibility

The earlier public [source-check run](https://github.com/DocMorphic/strep/actions/runs/38140729814)
fails on both operating systems. Its logs identify two interface mismatches:

- `BoundarySceneEdits` initializes its own actor state but omitted
  `editable_clip_boundaries`, now required by the inherited audit. Actor state
  now records exactly the start/end choices already authorized by that editor.
  Preserved endpoints report no edits; opted endpoints report their actual
  changed native keys. Track budgets, frozen keys and static payload checks
  remain in force.
- Compact surface guidance omitted the expanded path's plane diagnostics and
  used only triangle-referenced vertices. It now queries every target vertex
  against each declared plane and retains the same row metadata, population
  counts and per-time summaries. Triangle-pair compaction is unchanged. A
  regression checks a penetrating vertex outside the indexed triangle population.

The new focused CPU workflow runs the affected exports/audits, complete surface
comparison, pose-proportion proposal and bounded-pose regressions on Windows and
Linux. It uses synthetic source fixtures, without model weights or downloaded
character/capture payloads. It supplements the existing broad workflows.

Validation of these changes is pending. Local execution remains below the
unchanged RAM admission requirement. A green source workflow would not validate
the complete captured study, actual animation realism, contacts, engine import,
forces, cleanup time or release readiness. All release criteria remain unchanged.
