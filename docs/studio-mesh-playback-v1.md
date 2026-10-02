# Playback mesh-contact fitting in Studio

Studio now exposes the [tested mesh-contact clocks](mesh-contact-clock-v1.md)
and guarded fitting path. This is an experimental finite-clip authoring option,
not a trained model or a claim that the [crawl contact failure](crawl-body-contact-frame-hold-v1.md)
has been solved.

## Use

Open an exported character motion, then its mesh-contact editor. Choose mesh
patches, intervals, fixed world targets and editable joints as before. The new
**Fitting method** selector offers **Across the clip · experimental** for finite
clips or the existing frame/cycle fit. The new method is the initial choice for
eligible finite clips; older metadata and periodic clips keep the existing path.

For across-clip fitting, **At authored frames** constrains active frame keys.
**Hold through each frame** explicitly adds samples until the next frame after
the last selected frame, clipped to the available animation duration. Both
methods check decoded floor geometry. Native keys, midpoints and 120 Hz samples
are finite observations, not continuous-contact guarantees. One clock applies to
all contacts without an override. [Individual interval timing](mesh-interval-clocks-v1.md)
is now available for mixed key/hold conditions in one job.

Advanced budgets expose control spacing (1–120 frames), floor iterations
(1–200) and contact iterations (1–200); defaults are 10, 30 and 60 respectively.
The existing 5 mm floor and 20 mm contact screens cannot be relaxed through
these controls. Inspect contact errors before fitting: diagnostics include
authored frames and the chosen playback clock, with a button to seek the worst
fractional sample. A fit saves a separate job; it does not overwrite the input.

Periodic motion explicitly rejects the new mode in both the client and API:
this trajectory fitter does not preserve cycle closure. Use the existing cycle
contact fitter for loops. Moving object and partner targets belong to the scene
workflow; this editor's targets remain fixed in world space.

## Saved request, candidate and failure

`contact-fit.json` uses `strep-mesh-playback-fit-v1` and is separate from the
unchanged contact-spec schema. Browser fitting preferences are stored separately
and tied to the exact GLB hash. Jobs bind the options, draft, input and fitting
implementation hashes before launch. The worker verifies its source archive
before and after fitting, retains the original transfer and saves the raw fitter
evidence under `mesh-fit/`.

The result includes separate contact and floor inspection links, the saved
choice and fitting result. Failed candidates remain available; the existing
result selector defaults to the retained input when correction is rejected.
Passing sampled errors alone cannot override optimizer/acceptance failure.
Progress shows the phase and iteration, without assigning approval to a trial.
The ZIP includes the original, candidate, option record, fitter evidence and
implementation archive; packaging verifies CRC and file bytes.

No numerical result establishes anatomical patch correctness, intended support,
action correctness or naturalness. Developer/animator review and timed cleanup
remain separate requirements.

## Validation

Sixty focused Python checks pass across the new adapter/options, existing
contact-clock/playback guards and desktop build. A new DOM/source JavaScript
suite exercises explicit option snapshots, separate persistence, unchanged
legacy payloads, periodic rejection, duplicate submission prevention, stale
inspection/metadata responses, storage failure and fractional diagnostic seeks.
These checks do not render a browser or exercise GPU skinning.

The broader model-free workflow also passes: 1,589 Python checks and fourteen
explicit JavaScript suites. This is source regression coverage, not full
inference, visual or animation-quality validation.

An actual Studio worker ran on a synthetic seven-frame rig using frame-hold
timing, spacing 2 and floor/contact budgets 3/8. It reached sampled contact
errors below the cap but exhausted the declared contact budget: correction was
rejected, the exact input retained and quality unapproved. The completed package
passes CRC and selected original/candidate/evidence byte checks. Local evidence
is under `reports/studio-playback-smoke-v1/`; it is not published asset payload.

The existing fixed real-character crawl study is unchanged. This integration
does not rerun it, consume reserved held-out cases, generate new motion, train
a model, or add human review evidence. The single project-wide release goal and
all fourteen unapproved release capabilities remain open.
