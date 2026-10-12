# Inspecting stored-key failures and the actual Studio crawl attempt

`scripts/native_component_receipts.py` locates failures in complete saved mixed
repair observations without loading NumPy, a model or a renderer. It validates
the original contact/boundary/policy bindings, source actor hashes and clocks,
native/unrounded arrays, row caps/scales, exact declared failure counts and
selected native asset hashes. Original cap matrices can be row-major or
column-major; both are read in logical row order.

The report covers each edited actor's track bounds, joint displacements and all
four original source-rate metrics. It identifies failing node names, rate-frame
indices, sample-time stencils, recorded caps/scales and structurally influential
**permitted** rotation/translation tracks and editable native support keys.
Own-joint rotation is excluded from positional support; self/ancestor translation
is excluded from angular support. Protected support and boundary permissions
remain reflected in the key lists. Contact and authored-speed suffix rows stay
counted explicitly without inferred joint interpretation. A detail limit never
changes complete group/decision counts; the report states when details truncate.

This is archive inspection. Matching a cap archive does not independently
rebuild those caps from motion, and possible support is not proof of a repair.
No fresh pose, geometry, engine, causal or animation-quality approval follows.

For the retained best crawl anchor:

```powershell
python scripts/native_component_receipts.py --contacts reports/kenney-crawl-stored-boundaries-v1/fit/contacts.json --boundary reports/kenney-crawl-stored-boundaries-v1/fit/boundary-edit.json --caps reports/kenney-crawl-stored-boundaries-v1/fit/source-rate-caps.npz --policy reports/crawl-component-continuation-v1/policy.json --report reports/crawl-component-continuation-v1/proposal/storage-repair.json --native-label storage-4-8 --output reports/my-new-crawl-diagnostic.json
```

The output path must be fresh. Omitting `--native-label` inspects the returned
candidate. Inspecting a partial best neighbor never promotes it to a passing
animation. The named action paths are reproducible development examples, not
an allowed-prompt list.

## Measured remaining conditions

Fresh inspection of the
[second mixed crawl anchor](studio-component-storage-v1.md) reproduces all
107,895 conditions and all 41 failures: **24 positional acceleration and 17
angular acceleration**, with zero intended-motion failures and no unclassified
suffix. All failing rate rows have some permitted native support. Their saved
norm caps range from 19.736287 to 362.314477; none is a zero-cap failure.
Angular failures cluster at row-frames 167 (seven) and 363 (six), primarily the
left forearm/hand and finger descendants. Multiple descendants can reflect the
same parent motion; these counts are not independent anatomical defects.

This distinguishes the remaining problem from the earlier uncovered root
translation. It motivates measuring coordinated neighboring keys/components,
including their effects on previously passing rows. Merely increasing identical
single-component greedy trials is not yet justified. Structural support alone
does not prove that a passing stored clip exists within the current envelope.

All **12 standard-library inspection tests** pass (six new and six existing),
with all 20 resource observations independently replayed. They check known
row/node/time/translation support, multiple actors, suffix counts, detail limits,
column-major matrices, original cap/clock dimensions and tampered arrays,
receipts, assets, policies and labels. The first actual inspection rejected a
valid column-major source cap; the reader was corrected before the passing
checks and final reports. Final records live in
`reports/component-failure-inspection-v2`; prior attempt/report evidence remains.
Inventory is 474 Python test modules / 42 Node suites.

The preceding Studio commit `536d4a7` passes all six focused Windows/Linux
jobs: 855 Python tests per OS (788 contact/rig, 35 lineage and 32 packaging),
23 subtests and the offline editor checks. This predates these six new diagnostic
tests. Its actual-engine fixture workflow also passes; full-suite outcomes and
this diagnostic commit's hosted outcomes remain separate evidence.

## Actual Studio v4 humanoid outcome

The retained original humanoid crawl was submitted through Studio v4 with the
same 63-control root/arm budget, both actual clip edges editable, explicit
transition-review acknowledgment, unchanged caps/geometry and the default
8-stage/16-probe mixed effort. No new motion was generated. Preparation froze
the exact inputs and correction methods before execution.

The owned worker stops at the existing **900.547-second execution limit**; all
901 resource observations independently replay. It leaves no completed fit or
validated final animation. There are 86 complete raw native receipts, seven
completed outer repair receipts and seven full geometry receipts (original
start plus six changed candidates). Every completed changed candidate fails
native conditions; every completed geometry receipt fails all 2,017 floor times.
The strongest rejected peak is 242.172674 mm versus 263.015264 mm at the start.
The selected returned form of proposal `1-2` has 52 stored failures and zero
intended failures, reproduced by the new inspection tool.

The terminal guard is authoritative. The former outer processing state is saved
byte-for-byte before recording a bound supervisor-stop receipt and failed Studio
status. This is explicit reconciliation of this owned interrupted job; it is not
an automatic future worker-liveness feature. Raw proposals, assets and inner
processing receipts remain unchanged. A separate read-only check verifies the
prepared/method/source bindings, stopped review status, original selection,
empty downloads and a **byte-identical original cap archive**. It completes at
8.110 s execution; all 26 resource observations replay. No fresh pose/geometry
computation is claimed by that metadata check.

Evidence remains under `reports/studio-crawl-mixed-v1`,
`reports/native-scene-fit-jobs/crawl-mixed-v1` and
`reports/studio-crawl-mixed-verification-v1`. These raw interrupted results are
development failures, not held-out or training evidence. New native repair
search, interrupted-worker handling, complete clearance, semantic quality,
engine fidelity and human cleanup remain required work.
