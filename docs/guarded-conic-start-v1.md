# Conic starts through guarded native interval correction

The [isolated conic proposal helper](geometry-conic-start-v1.md) is now an explicit option in the existing fitter and native interval repair command. The default remains `supporting-planes`. Selecting `conic` changes proposal search; the complete nonlinear, tangent, saved-representation and whole-interval retention decisions remain mandatory.

For an existing completed V17 source study, the interval command accepts:

```powershell
.venv/Scripts/python.exe scripts/repair_contact_interval.py `
  reports/your-completed-v17-study reports/fresh-contact-repair `
  --start 60 --end 121 --proposal-geometry-solver conic
```

This requires the pinned `requirements-scene-proposals.txt` dependencies in that Python environment. Existing motion studies, character payloads and weights are not bundled in the public source snapshot. Use the existing owned resource supervisor with the unchanged **2 GiB estimate plus 600 MiB reserve**, fifteen-second stable admission, 7 GiB process-tree cap and runtime/RAM-floor stops before launching a full native fit. This example does not run a model or certify an exported asset.

## Retention and provenance

The fitter records `proposal_geometry_solver` separately from `proposal_start`. Both backends share the ordered full/quarter/sixteenth/zero margin schedule and one twenty-second proposal budget. Its selected margin changes only search headroom. The original preservation thresholds still decide every attempted backoff, optional local correction, SLSQP query and retained pose. Exhausted measurement/time budgets return the last jointly retained point.

Conic start records preserve complete caps, bounds, merit gradients, vectors, primary and selected proposals and checked phase metadata. The numeric control count is `control_count`; `controls` remains the original normalized pose vector in the shared archive format. Proposal records stay unretained even when a separate pose trial passes. Invalid solver selection fails before measuring or acquiring the native worker lock.

The native repair archives `geometry_conic_start.py` alongside its other methods. Continuation requires matching explicit solver choices in protocol and fit report and the archived conic implementation. Older supporting-plane archives remain accepted under the existing full bindings. Conic replay independently reconstructs every scalar row, norm vector, control bound, slope and primary/secondary epigraph without invoking Clarabel. Interval replay additionally binds original caps, exact trust bounds and start controls to the measured linearization, and binds geometry-start trials to their checked proposal and declared backoff. Later backoff checks retain only a small checked direction/identity per iteration; complete vector/Jacobian records are not accumulated in that lookup. Nonlinear/represented local replay and complete original-interval checks still follow. No saved conic success becomes a motion state on its own.

## Validation and execution status

The focused NoTorch suite passes **145 checks**, including twenty new integration regressions. Actual small conic starts flow through nonlinear and saved-pose replay; deliberately failing saved rows reject every proposed pose despite solver improvement. Measurement expiry after a rejected trial cannot promote its checked start. Complete streamed proposal records replay numerically; changed populations, caps, vectors, controls, epigraphs, phase/status and approval fields are rejected.

A frozen source fixture with **2,088 bound Python files**, no vendor assets or motion archives, passes **584 checks across eighteen modules**. It uses Torch for CPU fixture math. Native Jacobians, windows, original-source preservation, repair, resume/history reuse and the existing solver tests remain covered. The successful guard exits zero in 83.328 seconds with 664,780,800 bytes sampled peak RSS; independent resource replay verifies all 81 observations. Source-fixture admission remains 1 GiB plus 600 MiB. The first setup guard starts before its binding manifest is ready and fails; the next reports 554 passes and thirty failures because the selected venv lacks Clarabel. Both failures remain saved, and their six/81 resource observations independently replay. Installing the already pinned Clarabel 0.11.1 from the offline cache repairs the environment; no network model download occurs.

The final checkout also passes all **62 native continuation tests**, including five conic cases: complete proposal replay, missing archived solver code, removed solver choice, checked backoff linkage and a changed backoff that disguises a different saved pose. This covers legacy continuation, final method-check ordering and the bounded direction lookup. It supplements the frozen suite; it does not convert its earlier source binding into a claim that every broad test reran on the final continuation implementation. The numerical fitter/helper/repair implementations remain byte-identical to the successful frozen fixture. The explicit model-free inventory is **416 Python modules / 41 Node suites**.

The next real worker is bound to the independently verified V7 retained state and the previously stalled 117–119 window. Every other partition is explicitly excluded for this isolated diagnostic. It never resumes provisional V8 motion. Its first guard **defers without starting a child** after 60.687 seconds: all 61 independently replayed samples fail the unchanged 2,776,629,248-byte requirement. Native guard admission and outcomes are preserved under ignored `reports/conic-start-integration-v1/`; full V8 independent geometry replay remains outstanding. Native motion improvement is unproven until an admitted fit and independent local/interval replay complete. The trusted state stays V7, complete physical/keyed passes stay 0/62, and all fourteen release capabilities remain unapproved. The single full-project goal continues through broad action/scene/partner/rig/edit/style/transition/engine validation and actual developer review and timed cleanup.

## 2026-10-10 verification update

The [complete V8 frozen replay](isolated-contact-replay-v1.md) now passes and V8 stage 2 becomes the latest verified contact state. This diagnostic keeps its predeclared V7 input for comparison. Its next full native guard defers without a child after60.688 seconds, with61 independently replayed observations and unchanged2GiB plus600MiB admission/fifteen-second stability. Conic native motion improvement remains unproven; no pose or quality gate changes.

The later [admitted conic diagnostic and complete independent replay](native-conic-contact-v1.md) now retain six local improvements at117–119. Worst penetration in that window falls from24.379 to13.764mm; the full interval remains0/62 complete passes. The predeclared V7 comparison branch does not replace V8's additional retained edits. Batch coverage now supports explicit conic selection with unchanged default calls, scheduling and retention gates. Earlier pending descriptions and deferrals remain historical records.
