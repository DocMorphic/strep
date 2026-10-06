# Reusable stored-value repair and articulation study

`scripts/native_stored_pair_repair_job.py` turns the finite one-neighbor repair step into a pinned offline command. It handles v1 correction jobs and v2 jobs with explicitly bound static-joint references, including scenes where only some actors are edited. It preserves original clips and every original motion/reference/contact/geometry limit.

## Run and input contract

```powershell
python scripts/native_stored_pair_repair_job.py --request path/to/repair.json --output reports/new-repair
```

The output directory must be fresh and outside the original saved study directory. Nested destinations are rejected before any output directories are created, preserving the original study's artifact inventory. The strict request has `schema: strep-native-stored-pair-repair-job-v1`, three pinned files (`job`, `study`, `independent_replay`, each with `path` and `sha256`), `settings` with integer `maximum_stages` (1–8) and `maximum_probes_per_stage` (1–64), and a nonempty appended-clip `label`.

The `job` is the original [correction job request](native-stored-pair-job-v1.md), including its [v2 static-reference binding](native-static-rotation-variants-v1.md) when applicable. The `study` is its completed result, retaining every actual exported fraction. Its request, input, current implementation and artifact identities must match exactly. Artifacts cannot escape the study directory. The independent replay must be complete, identify that exact study, and cover its complete native Jacobian, every control derivative and original rate arrays. A pinned receipt is provenance, not motion-quality approval; actual exports are checked again during repair.

The command chooses the lowest recorded geometry score among fractions whose actual centered proposal passes native conditions and whose original-reference bounds pass. It verifies that centered feasibility and the selected geometry's original clock, limits and score before searching. This choice is local search guidance; original assets stay selected.

Continuous controls remain fixed. Up to the declared finite budget, the existing search tries absolute nearest/negative/positive neighboring Float32 components on permitted angular-acceleration support. It can add, restore or replace a component without accumulating steps. The existing source-bound policy still permits at most one neighboring step and at most its declared correction count. This heuristic does not search every possible repair or resolve arbitrary contact/dynamics failures.

Each fresh probe exports edited actors and independently decodes every actor's motion. Unchanged partners keep actual source playback and have no new actor file. All old conditions, caps/scales and source/reference permissions remain. Failed probes and processing failures are retained. After complete native/reference pass, the final candidate receives the full original geometry audit and separate appended clips preserving the original animation library and binary prefix. Neither numerical pass nor appended export grants engine, physics, semantic, human-quality or release approval.

Probe pose arrays are archived on disk and released after use. The command retains file paths in its cache, then decodes the final chosen probe again and compares every native residual and actor world matrix with its archived observations before checking reference bounds, geometry and appended clips. This avoids accumulating all probes' pose arrays in memory.

## Tests and repaired regression

An initial validation run has 60 passes and four failures. It exposes a real frozen-partner bug: the callback tries to compare a new file for an actor that is correctly unedited. Two protocol-fixture mutations also use different path separators from the Windows producer. The failing implementation, tests, diagnostics and exit1 are retained. After that worker exits, checking all partner worlds while comparing files only for edited actors fixes the implementation; fixture mutations preserve the actual producer keys.

The corrected run passes **64 focused CPU tests in 133.87 seconds, zero skips**: 23 new job cases, 16 existing finite-search cases, 13 correction-job cases and 12 static-reference cases. Both v1 and v2 integration cases perform actual export, source/reference/cap checks, complete sampled geometry and appended-library replay. Other cases reject changed bindings/methods/artifacts, incomplete replay, path escapes, invalid budgets and falsified scores. Re-pinned false raw observations retain a failed output and never create a successful result. Protocol fixtures explicitly do not claim a solver/Jacobian study ran; the larger study below supplies that separate evidence. CI adds the new suite; hosted CI success is not claimed.

After the memory change, the latest run passes **65 focused CPU tests in 89.03 seconds, zero skips**. The added regression performs four actual export/decode callbacks, confirms that archived edited pose arrays can be garbage-collected after each callback, and checks that the final probe is reloaded for complete geometry and appended export. The original 64-test run and the larger repair study below predate this memory change and remain immutable; the larger study has not been rerun with the new implementation.

The subsequent destination guard passes **four focused tests in 16.52 seconds, zero skips**. Both v1/v2 nested destinations reject with no output directory created and the original study's complete artifact population/hash mapping unchanged. The separate-output v1/v2 cases still perform actual fixed-control repair, complete native/reference/geometry checks and source-library/appended-world preservation. Protocol fixture replay flags remain receiver-test inputs rather than claims that those fixtures ran independent Jacobian studies. Existing larger results and archived implementations remain immutable; they are not rerun merely to publish this guard.

## Sixty-control correction study

The [separate articulation baseline](pair-articulation-baseline-v2.md) retains the original reference and limits, adding node7 rotation beside node6 for each actor. Its public v2 correction job completes with all 60 controls, 29870 native norms, 276742 scalar surface rows, 120439 equivalent encoded rows, 156303 exact dominance implications and 2854 depth witnesses. The nine original rate-array payloads and 1707 native/1673 geometry sample times remain unchanged.

The primary phase reports `Solved`; surface and minimum-norm phases report `AlmostSolved`. Predicted native excess is approximately 4.98594e-8. The measured normalized depth deficit is about 0.00574784637 versus the primary optimum 0.00574768733: this exceeds the requested 1e-9 phase lock. No exact optimum/phase-lock or nonlinear acceptance certificate is claimed.

Every actual export receives a complete geometry audit, including motion failures:

| Step fraction | Stored native failures | Centered native failures | Contact failures | Penetration, mm | Triangle records | Contained vertices | Failed geometry samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 46 | 36 | 0 | 5.030226 | 30424 | 22 | 1600 |
| 0.5 | 6 | 0 | 0 | 5.064515 | 30437 | 42 | 1600 |
| 0.25 | 0 | 0 | 0 | 5.082653 | 30437 | 52 | 1599 |
| 0.125 | 3 | 0 | 0 | 5.091700 | 30434 | 54 | 1599 |

All cumulative original-reference bounds pass. The quarter step passes raw native motion/contact checks. Every geometry result still fails the original five-millimetre and surface-crossing requirements.

A separate consumer imports no new job/model/proxy/guard/reduction/solver implementation. It exactly recomputes the original rate arrays and every native Jacobian entry, verifies every exact affine guard/surface implication, reconstructs stored offsets and replays all 60 scalar derivative columns within **3.3306690738754696e-13**. It checks every raw payload/world observation and saved geometry transport. Geometry predicates are not independently reimplemented. An additional displacement consumer confirms reference bounds across every native sample; uniform and all-native maxima happen to coincide in all four exports. Its initial array-indexing failure is retained and fixed after the worker exits.

## Applied repair and remaining failure

The new command chooses the half step as the best complete geometry score among actual centered-feasible, original-reference-passing fractions. At fixed controls, it tests five neighbors across six retained probes. Native failures progress **6 → 9 → 6 → 3 → 1 → 0**. Three added absolute component choices bring the final correction list from 17 to 20, including permitted node6 and node7 keys. All original limits remain; contact failures stay zero.

The final actual candidate passes native motion/contact and cumulative original/static-reference bounds. Maximum joint displacement is approximately 2.204085 mm for A and 2.232299 mm for B. Node6 rotation changes remain approximately 0.334437 and 0.334085 degrees; node7 changes remain approximately 0.086603 degrees each, within their five-degree bounds.

Complete final geometry is identical to the raw half-step score: about **5.064515009511399 mm** penetration, **30437** triangle records, **42** contained vertices and **1600** failed samples. Depth and containment improve from the 5.100709 mm/60-vertex baseline, while crossings and failed samples increase. Complete geometry still fails; this is an unapproved diagnostic anchor.

A separate repaired-key consumer imports no repair-job/search/storage/proxy API. It manually applies each absolute neighbor, verifies every retained probe and all 29870 native conditions at 1707 times, recomputes original rate arrays and animated/static reference bounds, and verifies complete original libraries and appended variant worlds. Geometry transport is checked, not its predicates independently rerun. Both appended variants preserve all six clips from the derived source and add index6. The new local model request changes only anchor controls/files/corrections; original source, reference, static bindings, rate/contact/geometry/edit limits and settings remain.

No new model inference/training, production humanoid action, rendering/GPU, engine, physical realism, semantic correctness, animator rating or cleanup-time evidence is claimed. Broad action/rig/object/partner and release requirements remain open. All fourteen release evidence arrays remain empty and the project-wide goal stays active. Next build a fresh correction from the independently replayed stored anchor, keep every failure and original limit, and measure whether further correction improves complete geometry.

Large local observations, assets and drivers stay ignored. Receipt SHA256 identities:

- Full v2 correction study: `3f555a752dcb131733ef830d14b5730a7e54aa4c8c357477c0e4c1a61fc19ad2`.
- Complete model/scalar replay: `8d7813e40195de08d106397f8ab4afe619ed56c6ac38392950e94ba9c566a974`.
- All-native reference displacement: `067529b362cf8eccae6de99d8844eb1938ed53286abaf6b189dc7ee013bdb72a`.
- Reusable repair job result: `1be2aafa26eef39fd2f2fe7e13760c4661daf6df50e0f90660e3c060264e64d7`.
- Repaired-key replay: `a9e2fed03e8d2122f5d114385f8920a9953bde2a11ea7f2e66e4bc40d2f2d23f`.
- Diagnostic anchor: `d31631bbb6962b1b850eec44e6646fd9e6d4d25b49b5b6ebaffb7acf6bc9fa39`.
