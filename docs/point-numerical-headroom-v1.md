# Numerical headroom for explicit contact points

The V15 correction retained a strict contact failure after imported playback: the first take reached 1.000020 mm against an authored 1 mm limit. V16 preserves that authored specification and the independent evaluator, while reserving a small amount inside the solver's working point limit. This does not convert a failure into a pass by changing acceptance.

The optional absolute headroom is 10 micrometres, capped at 1% of each existing working limit and applied only to active explicit contact keys, including compiled release guards. Thus this study fits a 0.990 mm working limit and still evaluates against 1 mm. Inferred/inactive keys and distributed-region fitting retain their existing behavior; nonzero headroom rejects use with a distributed fitter or without a point specification. Zero headroom remains the exact default. Recipes retain complete original/working/reserved frame-region matrices. Positive finite limits, a complete boolean mask and finite bounded margins are required. Numerical headroom is not a convergence, export-rounding or interpolation error guarantee.

## Actual correction and playback

The two unchanged guided takes, seeds 7103 and 7104, use the same one-second moving-box engineering reference, original bounds, six solver stages, V15 quarter-key object checks and 10 micrometre object buffer. No checkpoint sampling, training or reference modification occurs. Previous failures stay immutable.

Both fits complete with unchanged acceptance and empty contact-failure flags. Native maximum point errors are **0.986421 mm** and **0.937427 mm**. Maximum local rotation changes are 4.170° and 3.834° within the original bounds; maximum root lift is 0.0221 mm. Local correction times are 351 and 327 seconds, not a portability or throughput claim.

Actual headless Godot playback at **240 Hz** compares both V15 and both V16 exports: four clips, **932 actor samples**, all 77 bones and all 18,056 original vertices/eight influences. It checks the imported poses against a separate SciPy/GLB reader before measuring skin geometry. V16 maximum errors over each complete 17-sample contact interval are **0.986383 mm** and **0.937432 mm**; both satisfy every saved contact sample under the original 1 mm requirement. Every V16 playback sample has zero measured analytic box and floor penetration. The unchanged V15 failure remains present in the comparison.

All four new GLBs validate with zero errors and warnings. The imported full-skin replay is a finite-grid observation using shared original geometry and CPU skinning of actual engine bone transforms. It does not prove continuous collision clearance, GPU skin rendering, triangle intersection, physical attachment, naturalness or held-out interaction quality. Method snapshots preserve all 35 source modules during the study, and the dense audit rechecks all saved input hashes. Local evidence lives under `reports/scene-reference-correction-v5`, `reports/point-numerical-headroom-playback-v1` and the corresponding integration/model-free test folders.

All 143 focused Python tests pass. They include the preceding native contact/compiler/solver checks, zero-margin compatibility, absolute/relative caps, unchanged populations and inputs, a complete 1800-frame mask, invalid margins/matrices and unsupported fitter combinations. A separate environment without Torch passes 45 overlapping model-free tests. Hosted source coverage now declares 394 Python modules in four shards (99/99/98/98) and 37 Node scripts per operating system; validation of this publication is pending.

## Broader next cases

A source/preview/context preparation check retains the original six-second box-lift fixture and four-second high-five inputs. The lift has two physical surface targets and 5,694 declared hand vertices; its quarter-key clock contains 717 poses. High-five has two actors and world/partner contacts, with no scene objects, so the current object-specific V16 mode is unsuitable. Do not add dummy objects to bypass that distinction. A partner path must independently check both complete actors, meeting/release timing, body clearance and usable boundary poses.

These preparation checks verify metadata and saved input hashes only. An initial compiler import in the model-free environment fails because native contact compilation imports Torch; context-only preparation succeeds. That is an environment dependency, not scene infeasibility. Earlier oriented lift studies retain contact/normal failures and high-five retains separate flags; none is release approval. The next substantive experiment must cover these longer actual actions rather than extend this short reference indefinitely. The existing exact sparse skin operator may reduce memory for the larger pose population, but its interpolation/solver behavior needs verification before use.

## Reproduce and limits

Use separately acquired pinned vendor assets and a compatible original guided collection; keep old outputs by selecting fresh directories:

```powershell
.venv\Scripts\python.exe scripts/run_scene_fit.py <guided-scene-1.json> <guided-scene-2.json> --output reports/<new-correction> --solver-version 16 --preview-base reports/<original-guided-collection>
node scripts/validate_scene_exports.mjs reports/<new-correction>
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/<new-correction> reports/<new-key-audit>
```

Dense Godot replay must supply a complete denser `sample_times_s` clock to `godot_import_audit.gd` and remeasure the full original skin against the scene geometry. Native-key import alone cannot prove playback clearance. This study shares one native rig/skin and analytic geometry; it does not assess realistic grasp, physical attachment, forces, balance, self collision, partner dynamics, held-out semantics, target-rig transfer or human cleanup time. All fourteen release evidence lists remain empty and the whole-project goal stays active.
