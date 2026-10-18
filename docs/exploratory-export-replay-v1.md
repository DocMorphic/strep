# Independent native and saved replay of the partial correction

Development experiment, 2026-10-18. The previous complete-frame solver retained
a partial numerical correction. This study exports it and independently checks
the actual native and saved data. **The improvement survives export, but the
animation remains unapproved: 41 physical conditions still fail.** No clip is
selected in Studio or substituted for the qualified reference.

The two-character high-five is a development case for reusable authoring and
validation. The broad action scope and original release requirements remain.

## Export and preservation

The same retained 72 controls remain relative to the original native clips.
Original five-degree joint and two-centimetre root limits, protected keys and
selected joint identities are unchanged. Export produces separate Float64
intent pose arrays, Float32 native arrays with recomputed cached poses and
patched GLBs. Original source files are preserved alongside the diagnostics.

The new [native-key exporter](stored-track-deltas-v1.md) preserves zero edits
without normalization drift and isolates shared samplers before editing a
channel. An independent replay verifies original binary prefixes, static rig,
materials, all eight skin influences, 18,056 vertices and 36,108 faces. All
unselected channels and 671 protected rotation keys per actor remain exact.
Reconstructing zero-edit masks from the original controls independently checks
**35,894 zero/unpermitted saved keys byte-for-byte**. Actual raw and stored
rotation/root differences pass the original limits without a physical epsilon.

Foot-contact labels remain inherited from the original motion; they are not
new evidence of planted feet or newly validated gameplay events.

## Raw, nominal playback and native key times

The model-free replay excludes the writer, Torch, decoder, gradient and
optimizer modules. It observes fourteen actor/representation metric sets and
seven paired-contact/orientation sets:

- Original raw motion, Float64 intent and candidate raw motion.
- Original and candidate GLBs on the nominal 30 Hz grid.
- Original and candidate GLBs at their exact stored native key times.

Complete original metric populations and frozen motion policies remain. All
candidate forms pass the full declared motion ceilings and the 5 mm sampled
floor screen. Actor A's maximum floor depth is zero; actor B's is about
4.900 mm. The original raw floor maxima were 10.430 and 8.328 mm respectively.
A floor-depth pass does not establish foot planting.

All three authored point targets pass. The saved palm gap is **29.958 mm**,
inside the existing 30 mm development screen. That is not a claim that palms
visually touch or that the action meets professional quality requirements.
Actor A's palm orientation remains a failure.

One original actor-B motion-cap row fails at exact stored key times. It stays
in the report; no cap is rebased to conceal it. Candidate motion caps pass on
both saved clocks. Historical strict per-index source comparisons remain
separate and are not presented as nonregressing when they worsen.

The maximum joint/rotation/skin differences between decoded files and cached
poses stay within the existing technical 1e-5 fidelity bound. That comparison
does not add clearance, contact, motion-cap or edit-budget tolerance.

## Complete independent body-overlap replay

Nine serial geometry blocks query all 120 frames in both directions for
candidate raw, saved-grid and saved-key motion: **720 direction queries**.
Every original source vertex is considered; retained points query the original
target triangle mesh. Conservative broadphase rejection does not replace
mesh queries with a hull proxy. The original 5 mm depth screen is unchanged.

| Representation | Deepest overlap | Frames exceeding screen | Vertex/direction/frame exceedances |
| --- | --- | --- | --- |
| Candidate raw | 32.113259 mm | 22 | 6,445 |
| Saved 30 Hz grid | 32.112805 mm | 22 | 6,445 |
| Saved native keys | 32.112805 mm | 22 | 6,445 |

The deepest condition is B to A at frame 37 in each representation. Counts
above are repeated observations, not distinct vertices across the whole clip.

Independent composition rebuilds all **496 original signed conditions** from
actual floors, partner queries, contacts, normals, tangents and motion tracks.
Each representation passes the original fixed retention test: 449 required
rows plus passing warm-reference conditions form 455 required/protected rows;
original author bounds pass and the original worst-working-violation measure
strictly decreases. No required condition is waived or previously protected
condition lost.

Each representation still fails **40 directed partner conditions and actor
A's palm-normal condition**. Passing the fixed subset is a partial improvement,
not all 496 physical rows passing. Stored edit bounds are measured separately
from logical optimizer controls; exact control reconstruction from rounded
file values is not claimed.

## Verification and remaining work

All **264 focused source cases pass locally and on Windows/Ubuntu**, including
25 new export cases and two existing GLB cases alongside the previous 237
([hosted run](https://github.com/DocMorphic/strep/actions/runs/39144245348)).
The final audit streams source hashes and replays resource records, original
input identity, exact zero/protected keys, payload and stored limits, complete
metrics, all 720 overlap queries and every original final guard decision.
The preceding whole-goal receipt remains bound. Only progress text changes in
the original release contract.

Two study scripts needed reader-only repairs: the first metric replay used an
incorrect NumPy axis order, and the first coverage join supplied keyword-only
arguments positionally. Their failed records remain intact. Fresh versions
fix those calls; all 720 geometry queries are reused without rerunning them or
changing a numerical criterion.

Tensor jobs keep the 2 GiB process-tree cap; pure replay and geometry jobs keep
512 MiB. All retain the 600 MiB free-memory reserve, 15-second stable admission
and 300-second execution limit, under the serial worker lock.

Local evidence: `reports/stored-track-deltas-tests-v1`,
`reports/exploratory-export-v1`, `reports/exploratory-export-replay-v1` and `v2`,
`reports/exploratory-export-partner-clock-v1`,
`reports/exploratory-export-partner-join-v2`,
`reports/exploratory-export-gates-v1` and
`reports/exploratory-export-progress-v1`. Generated assets and bulky study
outputs remain local and ignored by Git; third-party asset rights are unchanged.

Next address the remaining body overlap and palm orientation using the
demonstrated native/saved constraints. Continuous-time, edge-only and
self-collision, forces, actual engine/runtime behavior, held-out actions,
rigs, objects and partners, realistic semantics and genuine human cleanup
ratings remain open. Model weights, training data and model inference are
unchanged. The entire-project goal stays active.
