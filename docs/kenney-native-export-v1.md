# Seven-action native export and skin-encoding audit

The existing seed-77 development clips were carried through actual native scene
authoring and game packaging on the independent Kenney rig: jump/land, crawl,
dance, wave, kick, get-up, and run/roll/stand. These are evaluation examples,
not a prompt whitelist or held-out release population. No motion was regenerated,
model changed, training admitted, or supplied character modified.

Godot 4.7.2 observes all 1,020 original native keys. The full imported mesh has
1,029 vertices and 1,604 triangles; correspondence retains every source skin
function and the triangle population. The floor is explicitly Y=0, with a 5-mm
penetration screen. Current speed intent is an explicit 200 degrees/s cap on
Hips, LeftArm, RightArm, LeftLeg and RightLeg. This uniform diagnostic setting is
**not an anatomical, style or realism threshold**. Native-key interval-average
principal rotation speeds do not certify instantaneous motion between keys.

Every source pose comparison passes. Scene and game sampled decisions fail for
all seven clips and remain failed inside both packages. Four fail the sampled
floor condition; all seven exceed at least one selected speed cap. Five exceed
the separate unchanged 0.1-mm native-to-imported skin comparison tolerance.

| Motion | Floor peak (mm) | Skin discrepancy (mm) | Selected joint peak (degrees/s) |
| --- | ---: | ---: | ---: |
| Jump/land | 0 | 0.144323 | 432.115 |
| Crawl | 263.014921 | 0.173554 | 271.302 |
| Dance | 0 | 0.099366 | 591.932 |
| Wave | 0 | 0.096257 | 366.988 |
| Kick | 49.727425 | 0.100121 | 445.864 |
| Get-up | 662.040380 | 0.127009 | 202.001 |
| Run/roll/stand | 978.276080 | 0.692680 | 596.562 |

The speed audit loads the exact saved actor Animation resource. Fresh numerical
replay checks its actual observed matrices and arrays; scene and game manifests
retain the failure. A separate passive certificate verifies 168 ZIP member
bindings, 749 archived method bindings, source snapshots, unchanged character
bytes and exact packaged resource/policy/observation bytes. Passive byte checks
are distinct from the producers' numerical replay.

Game packages retain embedded character root motion plus reference tracks;
applying those references a second time would duplicate movement. This study
declares no contacts or gameplay markers. Empty-event helper checks do not prove
physical interaction or runtime animation playback.

## Separate mesh encoding from pose errors

`scripts/audit_native_skin_encoding.py` explains an existing actor-only capture
without re-executing the engine, changing weights, correcting a clip or relaxing
acceptance. It validates original producer bindings and uses the exact captured
clock and source-ordered skin correspondence. At each key it evaluates this
ordered additive path:

1. Original source pose and source skin.
2. Observed engine pose with the same source skin.
3. The loader's sequential Float32 weight normalization.
4. Unsigned-16 packed weights with the same source bind functions.
5. Raw observed imported weights and bind functions.

Adjacent differences sum to the original skin discrepancy. The report retains
each component's per-key maximum, the largest total-error vertex with all terms
at that same vertex/time, and the unchanged original skin and combined decisions.
Component maxima can occur at different vertices or times and must not be added.
Reconstruction uses raw imported weights; renormalizing them would hide drift.

In this seven-clip capture, packing dominates the discrepancy. Pose contributions
are at most 4.471 micrometres; Float32 normalization contributes zero here, and
observed-bind differences are below 4e-15 m. Run/roll's packing contribution peaks
at 0.689696 mm. At its worst total-error vertex, source weights sum to 1 while raw
imported weights sum to 0.9999542236328125. This is a measured encoding effect,
not evidence that the underlying animation is realistic. The centimetre-scale
and larger floor failures still require independent correction.

Six generated-fixture checks exercise reordered bones/surfaces, eight influence
slots, a slow per-influence skinning oracle, known common translation and
encoding drift, and rejection of incomplete/nonfinite world matrices. Together
with the related imported-scene checks, all 34 pass locally. The public audit's
seven-case replay reproduces the separate prototype measurements to 1e-12 m.

For a retained actor-only native-authoring capture:

```powershell
python scripts/audit_native_skin_encoding.py contacts.json geometry-policy.json actors-engine reports/skin-encoding-audit
```

The output must be fresh. Replay requires the original bound producer methods
and inputs; it rejects stale or changed evidence. Numerical jobs use the guarded
worker workflow. This study's export, prototype diagnosis, test, and final audit
resource traces are retained separately. The first final-audit study wrapper
stops on an incorrect expectation that every actor-only decision is false;
the corrected wrapper reuses its three completed audits and computes the other
four. The original failed trace and outputs remain available.

## Related end-to-end checks and remaining work

At `fba61d5`, [the imported-speed workflow](https://github.com/DocMorphic/strep/actions/runs/38165446115)
passes all 185 Python checks on each of Windows and Linux, plus both offline
editor suites. Nine actual-engine cases include real correction staging: the
editor retains an existing root policy alongside a newly corrected foot policy,
and game export preserves both. A root cap of 100 degrees/s passes this fixture;
1 degree/s fails both scene and game despite passing the correction's foot check.
The [compatibility workflow](https://github.com/DocMorphic/strep/actions/runs/38165446109)
passes all 518 checks per operating system. These are software checks, not human
approval of the seven motions above.

Raw character, motion, engine and generated payloads stay in ignored local
reports. Export evidence is under `reports/kenney-native-export-speed-v1`;
prototype encoding evidence is under `reports/kenney-skin-error-v1`; the final
tool study spans `reports/kenney-skin-encoding-tool-v1` and `v2`.

Next, use explicit body/hand/knee support intent and bounded rig-aware fitting
on the retained floor failures. Preserve root paths and motion limits, evaluate
complete mesh clearance, and compare candidate fidelity on exact engine assets.
A blanket lift, relaxed cap or weight renormalization does not establish a usable
animation. The project still needs held-out semantic, style, interaction,
transition, rig, runtime and developer-review evidence. All release capabilities
remain unapproved and the single whole-project goal remains active. See the
[matched source/target floor comparison](kenney-source-target-floor-v1.md) and
[current export-policy integration](studio-export-speed-v1.md).
