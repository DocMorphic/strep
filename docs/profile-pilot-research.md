# Profile-driven motion: research and pilot protocol

Checked 2026-09-24 before inspecting the new pilot outputs. This study is an offline authoring experiment on the existing machine and checkpoint, not a trained stat-conditioned system.

## Findings that determine the implementation

1. Kimodo exposes text, duration, root paths and other kinematic constraints. Its official guidance favors one or two behaviors with moderate descriptive detail and warns that conflicting or excessive constraints can hurt results. Dense root paths are the exception to the usual sparse-constraint recommendation. Therefore the pilot uses one sentence per style and one shared dense path; it does not constrain each limb to a template. [Best practices](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html).
2. Root-path constraints use XZ coordinates in metres, starting at the canonical origin. The model accepts a path sample at each frame. We request `x=0, z=3*t` at 30 fps for 120 frames; last key is at 119/30 seconds. This is a requested 3 m/s path, not proof of achieved speed. [Constraint format](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html).
3. Separate classifier-free guidance weights can balance text and constraints. Freeze both at 2.0 and diffusion at 100 steps across all takes, rather than tuning each profile to improve its result after inspection. [Generation parameters](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/configuration.html).
4. The vendor evaluates motion quality, constraint following and text alignment separately. Predicted-contact skating can look misleading when contact predictions are wrong. Keep height-based and predicted-contact proxies separate; no single style or quality score is enough. The 15-take exploratory sample and absence of a matched ground-truth set do not justify a broad FID/reliability claim. [Benchmark metrics](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html).
5. MotionCLIP demonstrates text-driven style and motion editing through a learned representation. This establishes precedent for semantic style control, not an off-the-shelf mapping from agility numbers to biomechanical quantities in Kimodo. [Authors' project](https://guytevet.github.io/motionclip-page/).
6. MoST treats the separation of action content and style as a substantive problem and studies transfer across different actions. Success distinguishing several runs would not establish that a character's style transfers to vaults, rolls or object handling. [Authors' project](https://boeun-kim.github.io/page-MoST/).

No third-party training data or replacement checkpoint is acquired. Kimodo's lack of scene awareness still applies: the backpack description tests body motion, with neither an actual backpack asset nor physical load simulation. Numeric strength, agility and endurance fields are recorded authoring intent and are explicitly not passed off as validated model inputs. A fatigued profile retains the fresh parkour profile's capabilities; the changed state is described in the prompt.

## Frozen pilot

Configuration: `benchmarks/profile-pilot-v1.json`. Five descriptions: neutral, parkour-trained, sprint technique, backpack running, fatigued parkour runner. Seeds 11, 22 and 33 are shared across profiles. Each take is four seconds, 30 fps, with the same 3 m/s path. New descriptions are genuinely encoded locally through the documented original-precision offload implementation. Existing generic-run embeddings are not substituted. The full resident 8B encoder equivalence qualification remains unresolved.

New engineering speed screens: mean forward speed within 5% of 3 m/s; pelvis XZ path error p95 no more than 0.10 m against the requested linear travel. The second is a pelvis-path proxy, not an exact reimplementation of the vendor's smoothed-root constraint metric. These tolerances are pilot choices, not industry standards or perceptual validation. Report actual numbers and failures.

Apply the same frozen loop extraction and stance-correction code/configurations to every take. Preserve raw motions and every candidate. Preserve source/full-clip, selected source-cycle, loop-corrected, stance-corrected and retargeted measurements separately. Never present a selected interval as the complete raw generation or silently retime/rescale motion to meet the requested speed. The target character uses its documented leg-length scaling, which changes world speed and is reported separately.

## What would constitute useful evidence

- Distinct takes for the same profile, after accounting for time phase and root translation, without interpreting failures/jitter as successful diversity.
- Different profiles at similar measured speeds, described by cadence, stride length, stance fraction, vertical pelvis excursion, torso lean, knee drive and arm swing. These quantities describe motion; none directly measures agility, strength or endurance.
- Style differences that survive cleanup and rig transfer, with all regressions retained.
- Blind reviewers can identify the intended descriptions and rate naturalness and cleanup effort. The prototype can hide labels and export review entries; no human ratings are fabricated.

Descriptor differences and phase-aligned pose distances are exploratory diagnostics. Three seeds per description are too few for dependable estimates of population variability; report ranges and individual results. Profile classification, if shown, must separate training and test seeds and avoid fitting normalization to the held-out take. The pilot must not claim success merely because animation files differ byte-for-byte.

Completion means an executed 15-take pilot, source/character exports and a working profile/take viewer with measured outcomes, including negative findings. Slider calibration and cross-action identity consistency remain later experiments.
