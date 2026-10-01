# Native knee smoothing under a stance height corridor

Smoothing knee bend reduces the diagnostic leg-rate excess introduced by the
previous floor correction by 96.56% for actor A and 98.19% for actor B on the
matched development case. Floor, hand contact, sampled partner geometry and
native authoring timing still pass. Original motion caps and absolute peak
guards still fail. This is an experimental comparison, not a selected default
or evidence of realistic motion across actions.

## Method and bounds

The input remains `checkpoint-guard-contact-v1`. Only the six canonical thigh,
shin and foot rotation tracks change; original float32 key clocks, translations,
root and non-leg channels/world transforms remain exact after serialization.
Foot orientation and horizontal ankle position are retained at native keys.
Endpoints may change under the new full-clip stance condition. Whole-body
protected spans, scale/shear, non-direct chains and mismatched clocks are rejected.

For each foot, the method uses the 1,195 vertices whose positive source influences
all lie in its subtree. The lowest point must lie between 0.25 and 4.75 mm at
native keys. The serialized audit independently requires no penetration and a
maximum lowest-point height of 5 mm at all 642 original full-clip audit times.
The smaller native-key upper bound provides an inward reserve. This bounds one
region's lowest point, not the whole sole, contact force, balance or foot skating.
It is an explicitly authored stance condition and must not be applied blindly
to airborne, stepping or rolling phases.

Each key's hip/ankle geometry converts the permitted vertical lift into a knee
bend interval. A convex quadratic smooths bend velocity, acceleration and
deviation from the minimum-lift solution. Derivative and integration weights use
the actual irregular native clock. Endpoint bends remain free inside their
boxes. The source's exact per-key segment lengths are retained, including tiny
animated translation differences; no translation is replaced with a fixed value.
Converted ankle lifts use the existing exact two-bone reach solver with a 30 mm
lift bound and a source-relative 45 degree local rotation bound.

The fixed grid uses acceleration times of 0.05, 0.15 and 0.35 seconds, crossed
with reference weights of 0.05, 0.5 and 5 inverse seconds squared. A minimal-lift
control is also retained for each actor. Every exported alternative is reloaded
before evaluation. Ranking uses only leg columns' squared positive excess above
the original motion caps, normalized by each cap with denominator floors of
0.05 m/s, 0.5 m/s², 0.1 rad/s and 1 rad/s². These are diagnostic scaling factors,
not new acceptance thresholds. Original cap tolerances remain unchanged.

The selected grid entries are acceleration time 0.05 seconds for both actors,
reference weight 0.5 for A and 5 for B. The minimal controls are byte-identical
to the previous floor-study GLBs, providing a matched control. One of the 18
smoothed proposals is rejected because its projected-gradient residual exceeds
the solver's convergence bound; all 19 completed alternatives and the rejection
are retained. Selection precedes the independent partner-mesh/contact audit;
passing the stance screen alone does not approve a candidate.

The first study attempt stopped before exporting candidates: its fixed-length
precheck rejected source variation up to 0.327 micrometres. That failed attempt
remains in `native-leg-smoothing-v1`. The repaired v2 uses exact key lengths.

## Measured development results

| Measurement | Actor A | Actor B |
| --- | ---: | ---: |
| Minimal-lift diagnostic score | 0.09680545 | 0.39672672 |
| Smoothed diagnostic score | 0.00333020 | 0.00718952 |
| Diagnostic reduction | 96.56% | 98.19% |
| Full-clip source/imported CPU floor depth | 0 / 0 | 0 / 0 |
| Minimum imported CPU height | 0.238823 mm | 0.227652 mm |
| Maximum imported foot-region lowest height | 4.750046 mm | 4.749982 mm |
| Maximum native-key lift | 10.771354 mm | 10.940852 mm |
| Maximum local rotation edit | 11.801935 degrees | 13.616678 degrees |

All 53 original partner-mesh checks pass on both source skin and actual imported
raw-weight reconstruction, with zero crossings, containment depth or degenerate
faces. Source palm contact remains exactly the prior measured 1.000026 mm gap;
imported contact remains 1.049559 mm, with maximum anchor error 0.088439 mm.
The maximum imported vertex difference at those samples is 0.155145 mm.

Both clips pass all 642 native authoring pose/clock observations in Godot.
Maximum position-component error is 0.534013 micrometres and seek difference is
4.440892e-16 seconds. The actual GPU audit passes all 84 body/hand silhouettes
and detects all six shifted-bind controls. Minimum positive IoU is 0.999412517;
maximum boundary distance is one pixel. Imported raw weights retain eight
influences, bounded 16-bit quantization, exact rest positions and inverse binds.
The separate imported full-clip stance audit checks both floor clearance and
the upper height bound at all 642 observed engine times per actor. CPU skin
reconstruction is not GPU vertex readback or engine-physics collision evidence.

## Remaining rate failures

The original contact-window cap counts improve against minimal lifts, but remain
worse than the direct checkpoint input. Global maximum excesses stay unchanged
because immutable upper-body motion dominates them.

| Rate | Checkpoint input | Minimal lifts | Smoothed lifts |
| --- | ---: | ---: | ---: |
| Position speed failed rows | 129 | 441 | 354 |
| Position acceleration failed rows | 297 | 338 | 332 |
| Angular speed failed rows | 980 | 1,272 | 1,162 |
| Angular acceleration failed rows | 144 | 193 | 182 |

An independent full-clip comparison uses 441 uniform 120 Hz samples. The final
79.47286 ns fractional tail is excluded from these derivatives and reported;
the separate pose/floor audit still includes the exact native endpoint and
fractional contact time. Full-clip absolute peak guards still fail for both
actors. The following are worst per-joint increases against the direct input,
not global body peaks or the diagnostic score:

| Full-clip peak increase | A minimal | A smoothed | B minimal | B smoothed |
| --- | ---: | ---: | ---: | ---: |
| Position speed (m/s) | 0.046916 | 0.004216 | 0.063633 | 0.007482 |
| Position acceleration (m/s²) | 3.792400 | 0.297177 | 8.084936 | 0.329596 |
| Angular speed (rad/s) | 0.070075 | 0.004067 | 0.086524 | 0.011433 |
| Angular acceleration (rad/s²) | 3.361884 | 1.475929 | 11.259040 | 0.516430 |

Against minimal lifts, some individual peaks still rise: five/three joints'
position-speed peaks, five/two angular-speed peaks and six/two angular-acceleration
peaks for A/B. No position-acceleration peak rises in that comparison. This is
not an all-joint improvement, despite the lower diagnostic score and reduced
worst regressions against the input. All original acceptance failures remain
visible; neither candidate passes combined motion-quality requirements.

## Reproduce and review

Use separately acquired local dependencies and character/source evidence, with
fresh output names. No model inference, training or held-out samples were used.

```powershell
.venv/Scripts/python.exe scripts/study_native_leg_smoothing.py reports/checkpoint-guard-contact-v1 reports/new-leg-smoothing
.venv/Scripts/python.exe scripts/run_native_contact_engine.py reports/new-leg-smoothing reports/new-leg-smoothing-engine --native-tracks --authoring-seek
.venv/Scripts/python.exe scripts/audit_native_gpu_skin.py reports/new-leg-smoothing-engine reports/new-leg-smoothing-gpu
.venv/Scripts/python.exe scripts/diagnose_imported_native_contact.py reports/new-leg-smoothing-gpu reports/new-leg-smoothing-contact
.venv/Scripts/python.exe scripts/diagnose_imported_full_floor.py reports/new-leg-smoothing-gpu reports/new-leg-smoothing-stance
.venv/Scripts/python.exe scripts/diagnose_full_leg_rates.py reports/new-full-rates reports/checkpoint-guard-contact-v1 reports/native-leg-floor-v1 reports/new-leg-smoothing
```

Studio → Scenes → Native contact comparisons → Refresh → **native leg smoothing
v1** offers the input, minimal lifts and smoothed lifts on the exact native
seconds clock. Six comparison GLBs pass offline glTF/Three.js loader checks with
zero errors or warnings. The viewer explicitly separates diagnostic improvement
from failed original rate gates and explains the new stance-height condition.
Browser rendering, human review, continuous collision/rate bounds, balance and
whole-sole planting remain unverified. No Studio default selection changes.

All 1,178 model-free Python tests and the workflow JavaScript checks pass.
Next work must constrain serialized joint rates and foot orientation together,
then expose support targets through rig mappings and explicit stance intervals
across diverse actions. General scene, editing/style, export, held-out and human
cleanup requirements remain open. All 14 release capabilities remain unapproved;
the single full-project goal remains active.

| Local evidence | Result SHA-256 |
| --- | --- |
| Smoothing study v2 | `31b63a4a9b37417916528900a02cde82b11575db245a78e4b90c9162b76a1a9f` |
| Native authoring engine | `56dcb7efcc0b4466c4cc717789f4d421d2326bb28e5f7cf9d66ccb9b04db028a` |
| GPU/imported-data audit | `f0720abd9b9cc773bfc14d60506ad7e8ab23d8585515dffece3ed1ef11ea131a` |
| Imported contact/partner mesh | `0e2a2f3b24795dfca2afacbf3a32baa022bc234cccba50a6bd2ddcb94f420005` |
| Imported full stance audit | `f5e1babfd84809b0f9da0ca300b0b1938cc5bfa16c611fa89637df926362659e` |
| Full-clip absolute rate comparison | `58ccd59ed8a43fc2868606ed515650d68951a6aa1c34f056b8c7b2fb9ca07f3e` |
| Published comparison build | `1d926588f9167227f920350d95675ec0644f4c5543a103a5b2f1e96743de448f` |
