# Timing capacity before submitting character corrections

Studio now previews the cost of a character's selected tracks and interior
motion control times while they are edited. It distinguishes the unsaved scene
total from the saved request total, including every other saved character.

The existing fitting limit remains 96 controls. Each selected track uses three
components per interior time. Four tracks and six interior times use 72; adding
a second character with four tracks and two interior times reaches 96. Extra
timing detail therefore needs a deliberate choice of which joints to edit.
This is a local solver capacity limit, not an animation quality score.

Saving checks the proposed whole-scene count before replacing any actor bounds
or turning-speed limits. An oversized save preserves the complete previous
request. The submission-time guard also remains. Removing a character or
switching selections refreshes the preview; malformed timing lists receive an
inline message. Requests and all backend motion, contact and geometry limits
remain unchanged.

The offline editor suite passes. It checks the live 72/96 example, exact-limit
saving, two-character totals, replacement without double-counting, oversized
track/time saves retaining prior bounds, invalid times and removal. Existing
speed choices, continuation, stale responses and atomic staging still pass.
The desktop bundle is rebuilt and exactly matches its sources. No live browser
or animation-quality approval is inferred from these source checks.

At commit `1178c2a`, the complete focused
[Windows/Linux workflow](https://github.com/DocMorphic/strep/actions/runs/38175516303)
passes 635 Python checks per OS (568 contact/rig, 35 lineage and 32 game
packages), plus the updated offline editor. The separate
[imported-key engine workflow](https://github.com/DocMorphic/strep/actions/runs/38175516354)
passes 185 checks per OS. Those engine checks use their existing fixtures;
they are not playback approval for the kick proposals below. The broader
model-free inventory has not yet completed successfully at this commit.

An independent development study uses the already measured Kenney leg/foot
chain with four rotation tracks and either two or six interior times. Both
cases start from the feasible original, keep source-cap arrays and declared
full-mesh checks, and lock the root and clip endpoints. Its outcome must be
recorded separately in the [timing-layout study](kenney-kick-temporal-layout-v1.md):
a capacity preview does not establish that extra timing controls can resolve a
particular motion failure.
