# Character-dependent motion controls

Current authoring update (2026-09-27): [movement profiles](motion-profile-v1.md) now carry editable designer stat-to-description rules into arbitrary timed action requests. This is experimental text direction; numerical capability response and realism remain unvalidated. Earlier running-study artifacts below remain unchanged.

Product direction agreed from the user's request on 2026-09-24: the same action should support different abilities, movement styles, current conditions, and multiple takes. A parkour character should be able to request a trained, responsive movement style. The existing neutral run is an engineering baseline, not a universal animation template.

Status: the profile pilot and separate-angle calibration milestone are executed. See [control calibration results](control-calibration-results.md). Supported source-angle choices are implemented; gameplay-stat conditioning remains unvalidated. The sections below preserve the original design and sequence; their proposed-work phrasing is historical.

## Authoring contract

An animation request combines:

1. Action and gameplay requirements: run, approach a vault, recover from a roll; target travel speed, duration, direction, turn radius, root motion and loop/transition requirements.
2. Character capabilities: agility, strength/power, endurance, balance, mobility and coordination. Use game-defined normalized ranges, preserve their original values, and version every mapping. Fitness may be a preset that populates several capabilities; do not silently count it as another independent multiplier on all the same controls.
3. Learned movement style/skill: parkour, sprinting, distance running, casual, cautious, energetic; optional reference clip. High agility alone does not imply parkour training. A strong character need not move slowly or heavily.
4. Current state and context: fresh or fatigued, urgency, carried load, footwear, surface and scene geometry. Endurance is a capability; fatigue is a current state. High endurance must not automatically produce a visibly different short fresh run without a declared design rule.
5. Variation: seed and requested take count. Changing the seed should provide coherent alternatives within the requested style; preserve the seed for exact recreation.

The user can start with a prompt and a preset, then edit sliders or direct controls. Show the resolved movement brief and allow overrides. Resolve conflicting speed/cadence/stride requests explicitly; do not silently make one knob cancel another. Unsupported controls must be labeled unverified or unsupported.

Example authoring intent:

> Generate three seamless runs for this character at 4 m/s. Parkour-trained, high agility, strong balance, moderate strength, high endurance, currently fresh. Compact arm carriage and responsive steps. Keep the selected movement identity across the later stopping and vault-approach clips.

These are creative/game design controls. Numeric agility 90 does not have a scientifically established conversion to a particular knee angle, cadence, or force. Initial mappings are exposed, editable hypotheses until tested.

## Implementation path

Create a versioned character profile and an explicit motion brief. Translate supported physical descriptors into text conditioning, and measurable requirements such as travel path, heading and timing into the available motion constraints. Keep inferred stylistic biases distinct from constraints the implementation can actually enforce. Save profile, mapping version, expanded prompt, constraints, seed and measured output together.

The current Kimodo checkpoint accepts text, duration and kinematic constraints; it does not expose trained RPG-stat input channels. Its model card also warns about prompt-following failures and lack of scene-object awareness. See [official model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1) and the pinned local generation CLI. Thus descriptive style prompts and path constraints are a first experiment, not proof that an agility slider works. More expressive/cartoon styles may exceed this realistic-human-motion checkpoint's scope.

Our current generation wrapper replays a hash-checked cache of five fixed benchmark prompts. New profile descriptions require newly encoded text, using the documented local offload route or an explicitly evaluated replacement. Never reuse a cached generic run embedding for different style text. Add resumable encoding and per-description hashes without modifying the frozen baseline benchmark/cache. Confirm genuinely new prompts work offline.

Generate multiple full-body candidates. Rank action compliance, requested motion properties, quality and diversity together, retaining failures. Existing correction code can be reused, but its effects on style must be measured: aggressive constant-speed root replacement or contact locking can reduce a requested bounce or cadence signature. Do not implement variation as random per-joint noise.

## First experiment

Use the same rig, action, duration, target speed/path and three shared seeds (11, 22, 33). Generate five descriptions:

- Neutral, fresh run as the control.
- Parkour-trained, compact and responsive run.
- Sprint-trained run with the requested arm and leg action, evaluated at the same travel speed for the style comparison.
- Run carrying a specified load, with the load state explicit rather than inferred from high strength. Initially evaluate the requested body style only; an actual carried object requires geometry/contact work.
- Fatigued version of the parkour profile, retaining the same underlying capabilities and training.

This 15-clip exploratory comparison asks whether descriptions produce useful differences. It does not validate numeric stat sliders, true load dynamics, sprint performance or parkour obstacle skill. If matched speed is infeasible for a profile, record that failure rather than silently rescale the output.

Then test one control at a time at low/middle/high settings, with shared seeds and a held-fixed profile. Prioritize controls with observable definitions (cadence preference, arm-swing range, torso lean, fatigue style); keep endurance/strength behavior unverified where the chosen action cannot demonstrate it. Extend the action set to acceleration, turning, stopping and jump/landing before claiming an agile parkour repertoire. Vaults additionally require explicit obstacle geometry and contact targets.

## Acceptance and failure reporting

Retain the existing loop, sliding, penetration, root travel and transfer checks. Add:

- Requested-speed/path/timing compliance before and after cleanup and retargeting.
- Cadence, stride length, stance fraction, pelvis vertical excursion, torso lean, arm-swing range and left/right symmetry, with definitions and confidence limits. These are motion descriptors, not direct measurements of strength or fitness.
- Within-profile diversity across seeds, after controlling for phase, heading and root translation; exclude invalid motion from successful diversity claims but report all failures.
- Between-profile separation at matched speed. Do not count “same motion played faster” as successful style control. Shared seeds reduce one source of comparison noise.
- Blind viewer/animator matching of clips to intended descriptions, alongside naturalness and cleanup-time ratings. Numeric separation alone is not perceptually meaningful style.
- Preservation of the requested style after correction and rig transfer.
- For individual numeric controls, repeatable directional response and unchanged unrelated controls; report interactions and non-monotonic failures. Do not declare all stats working because one combined preset looks different.

Freeze operational thresholds after inspecting appropriate reference motions and before the held-out evaluation. Publish every seed and reject rate; avoid choosing one flattering take per preset. Keep the existing contact defects visible while this study proceeds.

## Proposed next goal

Build a profile-driven run authoring prototype, produce and compare the 15-clip style pilot on this laptop, and deliver a character viewer where the user chooses a style/profile and then a take. Save reproducible inputs and distinguish working controls from unverified or failed ones. Preserve the current baseline and quality checks. This is the next proposed milestone; a persistent goal has not been created by this document.
