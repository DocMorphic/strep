# Mesh checks before accepting a correction

The finger-proposal replay reduced a fixed-axis objective while increasing actual
mesh intersections. The iterative correction path now supports an additional
acceptance guard, enabled by the finger repair study. An improving step must
pass the existing motion/contact/witness checks before the guard runs. A failed
mesh comparison causes backtracking; it cannot become the next iteration's
starting point. Initial and final controls are checked too.

## Fixed comparison

The guard retains the original mesh topology, declared times and original
surface observations throughout optimization. It uses complete triangle audits
and signed vertex-depth queries in both directions. At each time it rejects:

- New proper crossing pairs, including a changed pair population with the same
  total crossing count.
- Newly uncertain triangle pairs or newly degenerate faces. A formerly proper
  crossing becoming boundary contact is not treated as a new uncertain pair.
- An increase in either directional maximum vertex depth beyond a fixed 1e-8 m
  roundoff allowance. The existing 5 mm reporting threshold does not excuse
  additional penetration.

Topology changes, missing times, changed collision tolerances, inconsistent
triangle records and incomplete vertex-depth populations fail validation. Cached
control evaluations avoid repeating identical expensive queries. The finger
study independently decodes its exports and queries their meshes again before
declaring the study complete. All original motion, palm and older signed-witness
limits remain in force.

This is deliberately conservative: it can reject an intersection that migrates
between triangle pairs even when aggregate metrics improve. It is a regression
guard, not a physical quality metric or proof of a feasible repair. Retained
crossings can remain poor, and directional maximum depths do not bound every
individual vertex's regression. Fourteen sampled times do not certify the
continuous trajectory. Self-collisions and human animation quality remain open.

## Executed evidence

`qualify_surface_guard.py` applied the new policy to the completed, hash-bound
donor/diagnostic observations from the preceding replay. It verified clip
topologies, every bound input, recorded output and archived replay method. It
reused saved complete mesh queries; it did not claim a new geometry run.

The quarter-step proposal fails at **six of fourteen times**, with **34 new proper
pair-time crossings** and no new uncertain pairs. Aggregate counts rose by only
two because other pairs disappeared. One failing time has unchanged directional
maximum depths and an unchanged crossing count, demonstrating why counts alone
are insufficient. The largest directional depth increase remains 0.035259 mm.
The candidate was already rejected by older witness ceilings and remains so.

The new guarded finger study has not been rerun: its preceding numerical
failure would occur before the newly added mesh gate. This change does not
produce an improved animation. The next correction experiment should include
surface witnesses across the editable window, rather than optimizing only
the protected-time pairs. Preserve the old limits and track whether the new
guard blocks useful intersection migration before adopting it more broadly.

Local qualification hashes (SHA-256):

- Result: `c90323e29181e15357e20e9e08d4fe37a9fe0b0b5502588944f6b0262ea60a91`.
- Request: `ccb1526ca59b2696c85e7f713c89b24ee3fda4375d3affe39445741ac8f61d53`.
- Decision: `7ff84432d4da661289f1ae2ec82044e52c8ed7bc5f8688daa936d5f4202bf190`.

```powershell
.venv/Scripts/python.exe scripts/qualify_surface_guard.py reports/finger-proposal-replay-v1 reports/<fresh-qualification-output>
```

All 888 minimal source tests pass. Focused tests exercise real crossed closed meshes with zero vertex containment,
complete containment without triangle crossings, changed pair identities,
uncertainty/degeneracy, missing evidence, original-baseline preservation, decoded
cache bypass and optimizer backtracking. Existing unguarded solver callers keep
their prior behavior. No training, held-out use, Studio replacement or release
approval occurred.
