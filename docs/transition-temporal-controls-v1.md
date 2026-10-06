# Temporal controls and imported contact precision

The retained three-point bridge correction stopped improving a generated partner contact. A read-only decode of its final, full-step and smallest-backoff probes identifies the blocked conditions. Adding two authored timing points then passes the native contact under the original limits, but the saved engine resource still misses that limit. Both outcomes remain visible.

## Rejection diagnosis

The final retained probe has no failed protected source rows and one failed contact row. Its partner gap is about 20.2577 micrometres against a 20 micrometre limit. The proposed full step reduces its normalized contact residual from `0.00257717` to `0.0000174382`, but fails six angular-acceleration rows: nodes 6, 7 and 8 in each actor at `0.4083333 s`. The largest observed rate is `7.740962683 rad/s²` against `7.740507924 rad/s²`, including the original tolerance. Other source-condition groups pass. The smallest backoff returns the same contact merit as the retained final probe.

This diagnosis checks the complete protected row population, recomputes physical edit/displacement/rate quantities from decoded saved GLBs, verifies their residual ordering, and checks the original cap arrays exactly. It does not establish infeasibility or authorize increasing a bound. Receipt: `reports/transition-source-blocker-audit-v1/result.json`, SHA256 `59dda4c751905557398ee3cde04f56d8c87ba229a9a411f2c1762c605ae40e82`.

## Fresh timing-control trial

The trial uses the same sealed source and selected rotation tracks, with five evenly spaced authored knots over the same bridge instead of three. This increases the complete control population from six to eighteen. Source phases, boundary tangent guards, displacement/change bounds, contact targets and limits, geometry policy and one-million-query budget remain identical. Preflight audits all 1,707 times and 665,730 pose/vertex queries. No population is shortened.

This is a fresh epoch from the original source, not a continuation of the previous six-control fit. It permits three primary iterations and finishes after two, with both primary steps selected at fraction one and final solver merit `[0, 0]`. The earlier driver field `fresh_primary_iterations` contains the requested three-iteration budget; the authoritative fitter history and engine-study preflight separately record two actual iterations. The raw receipt remains unchanged.

Native contact, motion/source conditions and actor transition conditions pass; whole-scene geometry remains failed. All nine source-rate-cap arrays, including the clock, match the baseline byte-for-byte after dtype/shape checks. All original source and candidate files remain unchanged. Receipt: `reports/transition-temporal-controls-v1/result.json`, SHA256 `debdc0aa7b1de5babcdd4a5ab2eaf9453cc65eade5859b725a478a0dd5c6d610`.

## Saved-resource result

One real serial CPU/headless Godot run saves and reloads the native actor/object resources and measures all 1,707 requested times. Pose, full CPU-skin, object-pose and root-reference fidelity pass. Pose component error is at most `3.0303e-7`, CPU-skin error `2.4478e-7 m`, and root-reference error `9.5368e-8`. The owned engine exits zero with a clean log and stopped tree; the driver exits zero, its lock is free and all candidate/current/archive bytes remain unchanged.

| Contact measurement | Maximum gap | Original limit | Result |
| --- | ---: | ---: | --- |
| Five-point native partner contact | 19.995175 µm | 20 µm | Pass |
| Five-point imported partner contact | 20.055678 µm | 20 µm | Fail |

Import increases this gap by about 60.503 nanometres. All ground contacts still pass, but imported partner contact and geometry remain failed. A passing general pose/skin fidelity threshold does not imply passing a tighter contact threshold. Receipt: `reports/transition-temporal-controls-engine-v1/result.json`, SHA256 `60c0994b35f2f89b8ce8d47d6f074f42f6003311cc057ef25a98d58dc61deaf5`.

The result supports testing additional timing controls when a source boundary peak blocks a correction. It is one generated closed-cube-skin fixture, with arbitrary gesture clips and an authored micro-contact; it is not a human high-five, a held-out action/rig study or a matched iteration-count performance comparison. Existing three-point failures are retained. No new model sampling/training, live HTTP/browser, rendering/GPU, physics or human review occurred. All fourteen release evidence arrays remain empty.

Next, test an explicit internal reserve for observed export precision while retaining the original acceptance limit, then check the actual saved resource again. Do not automatically accept this native-only success or loosen the declared contact/geometry limits. Production interaction quality and animator cleanup remain open.
