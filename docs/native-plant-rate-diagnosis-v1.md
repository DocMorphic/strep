# Native planting: matched motion-rate diagnosis

This diagnostic separates search constraints from acceptance. It tests whether
the four source-relative motion-rate families contribute to a failed planted
contact correction. It does not define new authoring limits, select a clip,
approve animation quality or prove that an authored request is infeasible.

`scripts/native_plant_rate_diagnosis.py` offers four frozen modes:

| Mode | Source-rate rows retained during search |
| --- | --- |
| `original` | Speed, acceleration, angular speed, angular acceleration |
| `omit_translation_rates` | Angular speed and angular acceleration |
| `omit_angular_rates` | Speed and acceleration |
| `omit_all_rates` | None |

Only the named rate rows become zero during proposal search. Their structural
derivatives become zero too. Native interior leg controls, source anchors,
foot patch membership, contact clocks, support clearance and maximum gap,
ankle displacement, angular edit bounds, root/translation protection and
frozen boundary/outside keys stay fixed. The original 120 Hz source clock,
four source bins and rate tolerance are never rebuilt around a proposal.
Raw FP32 exports and the existing shadow-native conversion are both decoded
before a step can improve the diagnostic merit. The shadow is not an actual
SOMA-native NPZ conversion or a game-engine import.

Each probe reports diagnostic merit **and original merit**. Final independent
audits still check all four original rate families across all joints, contact,
support, clearance and protected mesh/track payloads. Rate failures include
the worst joint, sample time, source-bin cap, actual value, units and excess.
The selected `candidate.glb` is always an exact copy of the supplied base,
including when an ablated proposal happens to pass the original checks.
`diagnostic.glb` is a separate unapproved experiment.

Inputs, methods, policy, search budget and decoded probes are hashed and
archived. Changed inputs or methods make the run terminally fail rather than
publishing a result. A fresh output directory is required. The CLI acquires
the shared worker lock and limits numerical libraries to one thread.

Example with already acquired, source-bound local assets:

```powershell
.venv/Scripts/python.exe scripts/native_plant_rate_diagnosis.py source.glb base.glb draft.json policy.json reports/fresh-diagnosis --seed prior-proposal.glb --mode omit_all_rates --iterations 8 --trust .001
```

## Matched development case

The development experiment retains the female Quaternius run/roll/stand case
from the previous multi-rig study. Both authored foot stances are 6.0–6.6 s;
editable keys are 165–204. Public limits remain 1 mm source-anchor error and
5 mm/s patch speed, 0.25 mm clearance, 5 mm maximum gap, 30 mm ankle
displacement and 45 degree local rotation changes. All searches use the same
separately archived 4.99 mm/s proposal target, eight joint LP iterations and
0.001 radian trust. They start at the same prior raw proposal, not at the
previously fitted result. These are developer conditions, not human contact
annotations or general biomechanical realism limits.

The completed original-rate control from `native-roll-plant-v2` is reused
after verifying every archived method and input against current bytes,
redecoding its raw and shadow exports, reproducing its final constraint
merit exactly and reproducing the complete original search audit. This
avoids rerunning an identical completed search. The three ablations execute
sequentially with fixed inputs. Each receives a separate original public
audit and an actual headless Godot import using the original contact
population plus all twelve declared game-frame rate/phase clocks.

The local immutable evidence lives in
`reports/native-roll-rate-diagnosis-v1/`. These generated files, character
payloads and model weights remain excluded from public Git.

## Interpretation

All three new searches and imports complete. They add 1,836 source/proposal
pose observations across six scene imports, each with 65 bones and three
surfaces. The 612 observations of the reused control are counted separately.
Source observations repeat the same character/clip; these are not distinct
held-out motions or independent action coverage.

| Search mode | Native left/right patch speed (mm/s) | Native contact limits pass | Original failed rate rows: speed/acceleration/angular speed/angular acceleration | Imported worst frame speed (mm/s) |
| --- | --- | --- | --- | --- |
| Original control | 5.536534 / 16.080120 | No | 32 / 23 / 4 / 10 | 16.120047 |
| Omit translation rates | 4.997617 / 4.991240 | Yes | 56 / 39 / 0 / 11 | 5.250642 |
| Omit angular rates | 8.129227 / 12.729412 | No | 24 / 18 / 4 / 13 | 12.792564 |
| Omit all rates | 4.990007 / 4.989958 | No | 56 / 37 / 8 / 24 | 5.163385 |

Support/edit bounds and authored clearance pass for all four proposals.
Every full original audit and combined imported contact check still fails. No
diagnostic replaces the selected input. The translation-rate ablation meets
native public contacts but misses the stricter search target, retains eleven
angular-acceleration failures, and overshoots imported speeds. Removing only
angular rates has less effect on contact in this fixed-budget comparison.

The all-rate ablation's diagnostic worst deficit falls to 0.000008407206;
this is still nonzero. Its raw left/right anchors exceed 1 mm by approximately
0.204/0.350 nanometres. These remain failures, even though a rounded table
could make them look exact. Its imported right anchor is 1.000396 mm and
both feet exceed the speed bound. No tolerance is enlarged to accept it.

The largest original acceleration excess for every mode occurs at the right
toe leaf at 6.6 s, the authored stance end. The unchanged source-bin cap is
1.593403 m/s²; the original control reaches 5.214569 m/s² and the all-rate
ablation 15.472710 m/s². This localizes a correction-exit problem in addition
to the observed imported speed overshoots. It does not establish a biological
limit or mathematical impossibility of the requested contact.

The next solver work should test smoother correction entry/exit and proposal
constraints on the already fixed game-frame clocks, retaining original
acceptance. An ablation's nearly planted feet are not sufficient evidence
to replace the rate contract with a looser one. Actual engine pose/skin
effects must remain independent of the shadow-native approximation.

Seventeen diagnostic tests and 54 adjacent planting/headroom tests pass in
a model-free interpreter. They verify exact row omission, unchanged caps,
all-joint failure locations, structural finite-difference coverage, actual
serialized probes, original audits, passing/failed input retention, fresh
outputs, input-mutation rejection and unapproved results. The diagnostic
suite joins both model-free CI jobs; production planting paths are unchanged.

A better diagnostic merit can coexist with worse original motion rates or
contacts. A linearly feasible LP step is not a feasible serialized edit.
Failure after a bounded search does not prove mathematical infeasibility,
that the generator misunderstood an action, or that changing the rate policy
would solve it. Any future author-specified motion budget needs its own
versioned contract and independent audit; this tool does not supply one.

This investigation is development evidence only. GPU appearance, continuous
collision, balance/force, action and style correctness, human cleanup and
general scene/partner/body support remain separate unfinished requirements.
The full project goal and all release requirements remain unchanged.
