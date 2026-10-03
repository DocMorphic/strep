# Imported contacts across actions and character rigs

The fixed engine-clock audit now has a frozen batch runner and a broader
development study: jump/land, crawl, dance, kick, get-up and run/roll/stand on
CesiumMan and Quaternius female/male. These are previously examined seed-77
clips and retargets. They are not a new held-out population, a motion whitelist
or independent contact annotations.

## Reproducible populations

`native_engine_contact_population.py` accepts a JSON manifest with schema
`strep-native-engine-contact-population-v1`, a scope description and a nonempty
case list. Every case has a unique `id`, explicit source/candidate/base/draft/
policy paths and SHA-256 hashes, plus label metadata. Relative paths resolve
against the manifest. For example, one case looks like:

```json
{
  "id": "landing-character-a",
  "source": {"path": "source.glb", "sha256": "<source hash>"},
  "candidate": {"path": "proposal.glb", "sha256": "<proposal hash>"},
  "base": {"path": "source.glb", "sha256": "<source hash>"},
  "draft": {"path": "support-draft.json", "sha256": "<draft hash>"},
  "policy": {"path": "plant-policy.json", "sha256": "<policy hash>"},
  "metadata": {"action": "jump-land", "rig": "character-a", "candidate_role": "rejected_raw_proposal", "original_selection": "retained_input"}
}
```

The actual hashes must be 64 lowercase hexadecimal characters. Labels describe
the author's chosen population; they do not prove that an animation performs
its action or that a candidate was approved. The per-case policy independently
binds source, base and draft. The runner never generates, edits or selects clips.

```powershell
.\.venv\Scripts\python.exe scripts/native_engine_contact_population.py population.json reports/my-contact-population
```

Each case uses all twelve [fixed game-frame clocks](native-game-frame-contacts-v1.md)
and preserves the original stance contact gate. Cases run sequentially under
one shared worker lock. Inputs, methods, manifest bytes and sampling rules are
bound before execution and checked again between cases. Each completed engine
audit archives its actual imported bindings/poses and CPU skin measurements.
Unsupported imports are saved as unavailable cases and other cases continue;
input or method changes stop the batch. A terminal batch can contain failed
imports or failed motion checks. Neither can become an all-candidate pass.

## Predeclared development comparison

For all 18 cases, the comparison was fixed to historical trial zero when it
exported, or the exact retained input when no proposal existed. Thus 13
comparisons use previously rejected raw proposals and five use retained inputs.
All original selected clips remain byte-for-byte unchanged. Earlier draft
intervals, planes, edit bounds and rate references remain intact. The added
diagnostic policy requests 1 mm fixed-patch anchor error and 5 mm/s speed;
these are explicit development choices, not universal realism standards.

All 18 imports complete: **11,610 source/candidate pose observations**, 36 scene
imports and 84 imported surface instances. CesiumMan has 19 bones and one
surface; both Quaternius characters have 65 bones and three surfaces. Original
and imported vertex bindings match under the existing identity tolerance, with
no posed-nearest matching or weight renormalization. Maximum imported/native
foot-region position difference is 0.178930 mm.

Every comparison fails both the original and fixed frame planted-contact
requirements. The table gives worst imported frame speed across both feet and
all twelve clocks, in mm/s:

| Action | CesiumMan | Quaternius female | Quaternius male |
| --- | ---: | ---: | ---: |
| Jump / land | 16.569 | 23.344 | 25.700 |
| Crawl | 1444.913 | 2228.240 | 2308.645 |
| Dance | 2514.192 | 2950.441 | 3398.038 |
| Kick | 11.166 | 13.258 | 13.909 |
| Get-up | 45.809 | 94.784 | 102.213 |
| Run / roll / stand | 18.256 | 28.467 | 29.322 |

Five comparison exports pass the independent imported height/maximum-gap
conditions; nine pass those conditions in native skin at the same point clocks.
All still fail planting. Height checks cannot substitute for fixed source
anchors and speeds. The added clocks and imported weight/pose effects remain
visible rather than enlarging the authored clearance allowance.

The authored both-foot condition can conflict with dance steps or crawling.
Crawl also needs hand, knee and body supports. These failures cannot establish
that the motion generator misunderstood the action. They do establish that
the requested diagnostic conditions are unmet by these exports. Original
fitting failures and selections remain authoritative.

## Character payload compatibility

The next bounded correction on the female run/roll/stand rig exposed a software
rejection before optimization: its mesh-preservation check used a decoder that
rejects normalized attributes. This character stores `COLOR_0` as normalized
unsigned bytes and `COLOR_1` as normalized unsigned shorts. Both encodings are
defined for colors in the [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#meshes-overview).

The planted-motion audit now compares stored integer elements and their
encoding metadata without dequantizing these static attributes. Real leg-edit
fixtures preserve both encodings; changed values, normalization flags,
component types and counts reject the candidate. Sparse accessors remain
unsupported. This change does not make the motion sampler support normalized
skin weights, arbitrary quantized positions or all glTF extensions. The
initial rejected attempt remains archived separately.

A fresh matched attempt then completes eight bounded joint iterations at
0.001 radian trust from the fixed historical raw proposal. It preserves the
three-surface character, native clocks, root and unrelated tracks. The worst
normalized constraint deficit falls from 5.381602 to 2.349188, but the proposed
native anchor errors remain 1.064302/1.097578 mm and speeds
5.536534/16.080120 mm/s. Support/edit bounds pass; motion-rate failures increase
from the prior proposal's 12 speed rows to 32/23/4/10 speed, acceleration,
angular-speed and angular-acceleration rows. This is not motion-quality
improvement or acceptable planting.

Another 612 actual imported source/proposal observations preserve the failure.
The imported proposal's frame speeds are 5.631816/16.120047 mm/s and anchor
errors 0.932722/1.070607 mm. A passing imported left-anchor value cannot
override native anchor failures, either speed failure or the rate screen.
The selected output remains the exact original input. Editable target-rig
GLB is checked here; no SOMA-native NPZ conversion is claimed for this rig.

This is imported joint/CPU skin and software compatibility evidence. GPU
appearance, continuous collision, force/balance, action/style correctness and
timed human cleanup remain unverified. No training admission, real model
update or release approval follows. All 14 release capabilities remain
unapproved; the formal 72-by-five population is untouched and the full goal
stays active.

Raw evidence stays local under `reports/native-contact-rig-breadth-v1/` and
`reports/native-roll-plant-v1/` and `reports/native-roll-plant-v2/`.
Public Git contains the runner, fixtures and
methodology, excluding models, characters and generated exports.

The final checks pass 1,826 model-free Python tests, all 16 JavaScript suites
and 215 CPU adapter/native-review tests. Both previously completed Studio
planting jobs still serve their bound selections. The owned idle Studio
listener is refreshed after terminal workers and checks using process/socket
observations only. Live HTTP/browser and fresh GPU appearance are not verified.
The batch study retains its executed implementation archives separately from
the later single-buffer manifest parser and color-preservation fix; the frozen
case list resolves identically with the published parser. Receipt:
`reports/native-contact-rig-breadth-validation-v1/verification.json`.
