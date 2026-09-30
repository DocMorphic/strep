# Hand-aware terminal approach search

The six forearm-ranked routes all failed the final hand approach. This search
expands the candidate population and makes hand geometry a rejection condition
inside candidate selection. It retains the existing native pose, guide-speed,
joint-motion and protected-contact constraints.

## Population and checks

The last native interval is [2.041610718, 2.091722488) seconds. Its end state is
fixed to the original source. The preceding state ranges over 26 normalized
directions (axes, face diagonals and body diagonals), wrist offsets of 0, 5, 10,
20, 30 and 40 mm, and independent elbow swivels of -15, -7.5, 0, 7.5 and 15
degrees. Zero-displacement states shared by all directions are deduplicated.
This produces 3,275 distinct physical control states.

Each candidate must meet the original 0.8 m/s displacement and 300 degrees/s
swivel guide limits. The displacement limit applies to Euclidean speed, so a
diagonal cannot move faster by satisfying three separate component limits.
The original 60 mm / 30-degree planning domain and 45-degree native joint-edit
budget remain in force; the final interval's rate limits narrow the reachable
part of that domain.

`DecodedEdges.decode` exposes the same float32 native quaternion replay already
used by the motion-bounded path search. Its existing callable interface still
enforces motion checks. Tests compare every exposed world transform exactly
with independently baked GLBs, including shared samplers and one-actor edits.

For a candidate, both actors' 77 joints must pass original-bin positional speed
and acceleration and world-angular speed and acceleration at all seven original
120 Hz samples inside the edge. Two frozen samples after the edge enforce the
return junction. The existing 1e-5 numerical tolerance is unchanged.

Only candidates passing those gates reach the hand-surface test. Each actor's
2,933 hand-influenced vertices is queried against the full opposite mesh in both
directions. The center sample is queried first to reject obvious collisions
cheaply. A single depth over 5 mm rejects the candidate. Passing requires all
seven samples; an early rejection records an observed lower bound on peak depth,
never a fabricated complete peak.

These are necessary terminal-edge conditions. The incoming edge, earlier
approach, other body surfaces, full timeline and continuous-time clearance are
not checked by this search. A terminal survivor would still need a compatible
full path and its own decoded/full-body/engine audit. A failure of this finite
population is not a proof that every continuous or differently parameterized
motion is infeasible.

## Reproduction and tests

Local ignored assets and bound prior studies are required. Use fresh outputs:

```powershell
.venv/Scripts/python.exe -u scripts/search_terminal_hand_edge.py reports/scene-pair-full-approach-path-v1 reports/scene-pair-terminal-hand-search-v1
.venv/Scripts/python.exe -u scripts/diagnose_terminal_hand_rates.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-terminal-hand-rates-v1
```

The complete public Python suite passes 620 tests in the minimal environment.
A focused suite of 56 tests passes in the development environment. Coverage includes diagonal speed limits,
deduplication, the frozen suffix gate, between-key failure rejection, complete
sample coverage for a pass and actual GLB decoder equivalence. The preceding
commit `91f547a` also passed its hosted Windows/Linux source checks.

## Completed search and rate diagnosis

| Outcome | Candidates |
|---|---:|
| Native reach or pose-budget rejection | 525 |
| Internal decoded motion rejection | 2,749 |
| Passed motion, rejected by hand geometry | 1 |
| Passed both necessary conditions | 0 |

All 3,275 declared candidates were evaluated. The sole motion-passing candidate
was the unchanged source. At the first queried time, 2.066666667 seconds, its
hand depth is 21.333458 mm, so it is rejected after two directional queries.
The other six times are not queried for that candidate; 21.333458 mm is an
observed lower bound on this edge's hand peak, not a complete peak audit.
No candidate reaches a full-path search or publication.

An independent bound diagnosis replays 11 controls: the source, six pure 5 mm
axial offsets and four single-elbow swivels of +/-7.5 degrees. All 11 have valid
native poses. The ten nonzero probes fail motion checks, while the zero control
passes every motion category.

For the 5 mm Xminus offset, the internal failure is angular speed only:
`B:LeftForeArm` reaches 2.802394 rad/s against a 2.779043 rad/s cap at 2.0875 s,
an excess of 0.023351 rad/s. Its frozen-junction check also fails angular speed
only. This is distinct from the 5 mm Zminus offset, whose B forearm speed reaches
0.600137 m/s against 0.506977 m/s, and whose return acceleration reaches
20.890374 m/s^2 against 11.017452 m/s^2. The latter also has angular-speed
violations. Single-elbow probes show further forearm speed or angular-speed
failures and return acceleration failures; a valid native pose is not a valid
motion segment.

This evidence motivates a continuous coupled terminal-control solve with small
compensating elbow rotations and arbitrary wrist directions, preserving the
current caps and frozen contact. A 7.5-degree swivel grid cannot establish
whether a much smaller compensation can remove the measured 0.023351 rad/s
excess. Such compensation is a hypothesis to test, not a demonstrated solution.
The objective must address actual hand clearance; proximity to a known
colliding route is insufficient. Only then attempt a compatible complete path,
full-body geometry and engine validation of the same candidate.

Both workers completed. No motion was accepted, no Studio output was replaced,
and no training, new model/data acquisition or human review was performed.
All 14 release capabilities remain unapproved.

| Artifact | SHA-256 |
|---|---|
| Search request | `5b5bb657b5eb639169fd38b84da77bfa5d219172443e92d3b9c94a2e5e0ac99a` |
| Candidate outcomes | `23bbf1d8f6b59a8e1c177bbd8ce4f478c49b2aca38709139d79790b1260c3e72` |
| Hand rejection witness | `1ae9f3883af0471bacc2eb73690cc3d566d0c3b9ddfeff60ae76cdca99c796c0` |
| Diagnosis request | `a5e1afbcb14af7969cb186440b9ea31ff9ea95fc40bebfc844374c8f77fda27e` |
| Rate probes | `545d498304e6357d0d1a7806494ed06a0ca37f3ce3a9d564993acb7a2bcf68f5` |

See [the six-route hand screen](paired-hand-route-screen-v1.md).
