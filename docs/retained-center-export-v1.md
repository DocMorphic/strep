# Export the retained temporal correction

Study begun 2026-10-18, with sealed-capture replay continued on 2026-10-20.
This exports the exact 216-control half-step
retained by the [refreshed contact study](retained-center-refresh-v1.md).
The original source animations and author permissions remain the reference;
the saved asset is not treated as a new baseline with looser limits.

Both actors are evaluated through the same anchored three-knot representation
used by actual raw validation. The export keeps separate Float64 intent,
native Float32 motion arrays and GLB files. It appends edits to original saved
tracks, preserving the original binary prefix, unselected channels, all
61 protected rotation frames and zero-delta keys. Original raw/GLB files are
copied byte for byte for comparison. Root offsets remain constant.

Both logical control bounds and independently read saved-track bounds pass.
The largest saved rotation edits are 4.298643 degrees for A and 3.462650 degrees
for B, below the unchanged five-degree limit. Saved root shifts are 12.983311 mm
and 12.269920 mm, below the unchanged twenty-millimetre limit. Each actor keeps
671 protected rotation keys and 17,947 unchanged saved keys exactly.

## Independent saved-file observations

A separate reader excludes the exporter, gradient code and Torch. It checks
seven representations per actor: source raw, intended Float64, exported raw,
source/candidate nominal grids and source/candidate original key clocks.
Every representation retains its own clock and measured failures.

Both exported actors pass the original complete motion-limit populations and
the five-millimetre floor screen in raw and saved representations. At saved
keys, worst floor depth is 1.175982 mm for A and 4.252558 mm for B. The saved
palm gap is 29.992007 mm against the unchanged developmental 30 mm screen.
This is not physical touch or animation-quality approval. The original B
saved-key motion retains its one motion-limit failure; it is not rewritten
as a passing baseline. Per-metric strict source non-regression is reported
separately from passing the fixed motion caps.

All original topology and eight skin influences are retained. Foot-contact
labels are inherited, not newly validated support or gameplay events. Saved
pose/skin agreement is a transport check and does not establish dynamics,
contact forces, transitions, semantics or animator quality.

Local evidence: `reports/retained-center-export-v1` and
`reports/retained-center-export-replay-v1`. Complete partner-clock re-query and
actual engine import remain separate required checks before any promotion.
The whole-project goal remains active, with all release capabilities unapproved.

The separate partner-clock study completes all 720 directed queries: both
character directions at all 120 frames in each raw/grid/key representation.
Every query uses all 18,056 source vertices and 36,108 target faces. The complete
496-row guards are reconstructed separately for all three representations.
Each preserves all explicitly required, previously passing and retained-raw
passing conditions, with the same 38 physical failures. Working peaks are
5.260144 for raw and 5.260046 for both saved clocks, still below the pre-step
5.281024. No physical threshold is changed. These are preserved diagnostic
improvements, not all-condition passes.

Evidence is `reports/retained-center-export-partner-clock-v1` and
`reports/retained-center-export-gates-v1`. Actual engine checks remain separate.

## Actual engine transport

Both original GLBs are imported in the pinned Godot 4.7.2 engine at all 120
native keys. Pose agreement, floor and motion checks pass, but original imported
skin fails the unchanged 0.1 mm fidelity screen: peaks are 0.151919 mm and
0.151722 mm, with 61 and 59 failing times. The actual hand gap becomes
30.028064 mm and fails the original 30 mm condition. This failed engine result
is preserved.

A separate opt-in Godot copy changes only paired weight/joint payloads using
the existing adapter. All animation worlds and unrelated bytes are exact;
the original exports remain unchanged. Complete-clock comparison against the
original skin gives 2.018 and 1.870 micrometre peak differences.

Fresh actual import of those copies is compared against the original,
non-adapted exports. Both pose and skin tests pass, at 2.058 and 1.896 micrometre
peak skin error. Floor, motion and all point-contact tests pass; palm gap is
29.992129 mm. This is explicit target-specific skin encoding, not a claim that
the original weight coefficients were preserved.

A separate reader excludes the producer and weight writer. It replays both
sealed captures, matching all 120 pose/skin/floor observations per actor and
all point contacts exactly. Evidence is
`reports/retained-center-engine-fidelity-v1`,
`reports/retained-center-godot-weights-v1`,
`reports/retained-center-engine-fidelity-v2` and
`reports/retained-center-engine-replay-v1`.

GPU skinning, physics, gameplay-event playback and semantic quality remain
unverified. Full partner geometry from the actual capture is a separate check;
the passing partial engine observations do not grant scene or release approval.

The additional actual-capture body study completes all 240 directed queries at
the 120 native keys. It reconstructs raw imported CPU skin in source order,
requires complete skin-function and triangle-population correspondence, and
uses the declared source winding for canonical geometry. Every source vertex
and equivalent target triangle remains present; imported weights are not
renormalized for measurement. Peak partner depth is 31.200179 mm, still failing
the unchanged five-millimetre screen. This is actual engine-capture geometry
evidence, not a GPU-rendering or physics claim. Records are in
`reports/retained-center-engine-partner-clock-v1`.

The final engine decision reconstructs all 496 rows from those fresh body
queries and captured floor/global observations. Both current and original
benchmark guards pass, and every raw-passing and saved-passing row is preserved.
There are still exactly 38 physical failures, including partner penetration
and the existing A-hand normal failure. The engine working peak is 5.260036.

Actual engine orientations and root shifts are also checked directly against
the original native files at all 120 keys. Largest selected-joint edits are
4.298645 and 3.462650 degrees; root shifts are 12.983311 and 12.269924 mm.
Both stay inside the unchanged five-degree/twenty-millimetre limits, without
an added allowance. Stored-track preservation and engine pose fidelity remain
separate checks. Evidence is `reports/retained-center-engine-gates-v1`.

The diagnostic improvement survives serialization and the tested engine path.
It does not make the clip game-ready: 31.200 mm body penetration still exceeds
the five-millimetre screen. Studio selection, original references and training
admission remain unchanged. Broader actions/rigs, scene correction, support,
semantic/style evaluation and genuine human review remain required by the
single whole-project goal.
