# Explicit position repair and clip-edge authoring in Studio

Studio adds **Clearance with position repair**, using the new
`strep-studio-native-scene-fit-v4` request. It combines the
[typed stored-key repair](native-component-storage-v1.md) with optional actual
start/end editing. Existing contact modes and v3 clearance retain their earlier
contracts; v3 still preserves boundaries and uses rotation-only repair.

The author selects native tracks and bounds, chooses per-character start/end
permissions and saves them. Each enabled edge contributes an additional control
time for every selected track. Live and saved counts include these controls
within the same 96-component scene budget. Oversized saves preserve previous
bounds, speed limits and edge choices. A window must reach the actual clip edge;
protected interpolation support and native-key availability remain hard checks.

Editable edges require explicit acknowledgment that new starts, ends and
transitions will be reviewed. This is authoring permission, not an approval of
transition compatibility. Mixed precision repair only touches selected rotation
or translation tracks within original limits. It cannot grant new rig, object,
clock, source-rate or control permissions.

Saved jobs retain the complete boundary contract, mixed policy, source assets,
original caps, typed corrected state, method archives and raw failed probes.
Continuation restores the objective, edge choices, acknowledgment, budgets,
track bounds and authored speed limits. Changed boundaries, scene/geometry,
permissions, speeds, stored evidence or mixed/legacy mode reject; there is no
implicit upgrade of a prior source epoch. Native-feasible geometry failures may
continue but cannot be staged. Staging still requires passing native conditions,
declared geometry and any authored speeds, plus valid boundary acknowledgment.
The original job and assets stay retained; motion/engine/human review remains.

The desktop bundle is rebuilt from the updated editor source. Offline editor
checks exercise v4 requests, edge acknowledgment, exact continuation loading,
invalid boundary reviews, failed-floor staging and atomic edge budgeting. These
checks do not establish live browser, engine or animation-quality behavior.

Two-key LINEAR native tracks expose a separate clip-edge capability in the
catalog. Their legacy eligibility remains false; the new mode enables them only
with explicit edge authoring. Saving one without an editable actual edge rejects.
The backend uses the boundary-aware editor from initial validation onward, so
it does not incorrectly require an interior key before examining the edge
contract.

All **223 related Python checks** pass in one complete local run, including the
new 21-case Studio v4 suite and existing Studio/legacy storage, mixed repair,
native fitting and authored-speed integration. Cases cover actual prepared jobs
and their continuations with/without edges and speed limits, exact controls and
cap identity, malformed boundaries/acknowledgment, protected/internal edges,
excess capacity, changed modes/policies/state, two-key edge editing and visible
floor failures. All 673 resource observations replay. The additive catalog fix
then passes all three affected catalog/two-key checks (78 deselected); all 42
observations replay. No new full 223-case rerun after that catalog change is
claimed. The final offline Node suite passes, including edge capacity, atomic
saves, acknowledgment, staging rejection, source-bound restoration and two-key
mode eligibility. Inventory is 473 Python modules / 42 Node suites.

The previous [focused run at `6e8277d`](https://github.com/DocMorphic/strep/actions/runs/38199635126)
passes all six Windows/Linux jobs: 834 Python checks per OS (767 contact/rig,
35 lineage, 32 game packages), 23 subtests and the offline editor. That revision
precedes this UI integration; its success is not a new hosted coverage claim
for the current source. Full source CI remains separate.

## Continued development crawl

A second fixed-candidate mixed search starts from the independently reconstructed
twelve-component anchor with the root correction, 44 remaining native failures
and zero intended failures. The original 63 controls, source assets, cap arrays,
rate clock and policy stay unchanged. It uses the same finite 8/16 effort.
This is explicit failed-candidate study state, not a newly approved source clip.

The worker completes at **358.532 s execution**, with 59 complete native exports
and all 371 recorded resource observations independently replayed. Its best
greedy-merit anchor has 41 remaining failures and preserves passing root
acceleration conditions. No candidate passes all original conditions; the
returned twelve-component seed retains 44 failures. Its complete floor screen
still fails every one of 2,017 times at **257.398701 mm** peak.

The worker pins numerical source and verifies every imported project module.
Studio and the desktop builder are excluded from those pins and verified
unimported, allowing UI work during this owned numerical process. It introduces
no new model generation, held-out use, training, engine, browser/renderer or
human approval. Evidence remains in
`reports/crawl-component-continuation-v1`. Increasing bounded search effort
alone does not prove that the intended clip can be repaired or made realistic.

A separate numerical replay reconstructs the returned 44-failure seed and best
41-failure anchor byte-for-byte, matches every native world/residual and original
intended/cap/clock/control value, and verifies typed continuation re-export.
Both retain passing root acceleration conditions. Every returned floor sample
is freshly recomputed and identical. All 59 raw probe arrays/assets receive
hash validation; other neighbors are not numerically replayed and best geometry
is unassessed. This worker shares repository arithmetic; it completes at
42.890 s execution with all 60 resource observations replayed. Evidence remains
under `reports/crawl-component-continuation-replay-v1`. Neither partial anchor
is approved for animation, training or release.
