# Export the retained temporal correction

Development evidence, 2026-10-18. This exports the exact 216-control half-step
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
