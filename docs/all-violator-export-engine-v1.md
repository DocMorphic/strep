# Retained correction: export and actual-engine checks

Development study, 2026-10-18. This follows the raw logical-control step in
[the complete current-violator study](all-violator-surface-study-v1.md).
The original motions remain untouched. The outputs are diagnostic assets;
neither the qualified reference nor the Studio selection changes.

Both actors receive separate Float64 intent poses, Float32 native motion with
recomputed forward kinematics, and GLBs patched at their original stored keys.
The original rig, geometry, eight influences, binary prefix, old samplers,
unselected channels and protected keys remain intact. An independent reader
derives the permitted keys from the original controls and checks **35,894
zero/unpermitted saved keys byte-for-byte**. Each actor also preserves 671
protected selected-joint keys. Original foot-contact labels are inherited;
their preservation does not establish planted feet.

The original edit caps remain five degrees and 20 mm. Independent raw and
saved measurements both pass. Saved maxima are:

| Actor | Joint orientation edit | Root displacement |
| --- | ---: | ---: |
| A | 4.332186 degrees | 13.392403 mm |
| B | 3.413219 degrees | 11.266872 mm |

Model-free replay excludes Torch, the writer, gradients and optimization. It
observes 14 actor/representation combinations and seven paired sets, keeping
raw, nominal 30 Hz saved samples and actual native-key samples separate.
Candidate and intent motion caps and floor screens pass in every measured
representation. Saved floor maxima are approximately 0.68031 mm for A and
4.89986 mm for B, against the unchanged 5 mm development screen. These guards
preserve passing conditions; they do not promise that every numeric metric
improves. In particular, A's floor depth increases from the previous retained
diagnostic's zero depth while remaining inside that screen.

The unchanged original B clip has one motion-cap failure on its native-key
saved clock. That baseline failure remains visible. The three point targets
pass for the new candidate, but the saved hand gap is **29.9796 mm** against a
30 mm screen. This is not convincing hand contact or a completed high-five.
Palm orientation and body-overlap failures remain distinct requirements.

Nine serial guarded blocks measure every original surface vertex against the
original partner triangles at all 120 editor frames, in both directions, for
candidate raw, saved-grid and saved-key motion: 720 direction queries. The
ledger joins those measured rows without rerunning geometry. Complete final
checks reconstruct all 496 original scalar conditions for each representation.
Retention requires the original benchmark guard, the previous-progress guard,
and preservation of every passing condition in the retained raw step.

All three representations pass those retention checks. Each still has 40
physical failures; no previously passing retained-raw condition is lost.
Maximum working violations are 5.281045107659161 for raw Float32,
5.280934624304987 for saved-grid, and 5.280934624304971 for saved-key motion.
The correction survives storage, while the action remains physically failed.

Local evidence is kept under `reports/all-violator-export-v1`,
`reports/all-violator-export-replay-v1`,
`reports/all-violator-export-partner-clock-v1` and
`reports/all-violator-export-gates-v1`. Large assets and machine receipts remain
ignored. The source components retain their 307 passing focused cases locally
and on each hosted Windows/Ubuntu job; no source change is made in this study.

Actual Godot 4.7.2 import is a separate observation path. Both real exported
GLBs are imported and captured at every one of their 120 native keys. The audit
reconstructs CPU skin from the actual imported raw weights and topology, checks
pose/skin fidelity, and separately measures floor, full declared motion arrays
and the three hand targets. It does not query partner-body depth again, verify
GPU buffers, play physics/events in real time, or establish animator quality.

The ordinary import exposes a failure missed by direct saved-file sampling.
Joint poses pass, but skin-position error exceeds the unchanged **0.1 mm**
screen at 61 A keys and 59 B keys. Godot's sequential Float32 normalization and
unsigned-16 truncation lose weight mass. The measured hand gap becomes
30.015644 mm, failing the unchanged 30 mm point screen. Floor and motion caps
still pass. This original failed capture remains immutable.

The existing [opt-in weight derivative](godot-weight-derivative-v1.md) is then
tested on separate copies. All 13 existing focused weight tests pass locally.
The derivative reorders paired joint/weight entries and balances quantization;
**weight coefficients explicitly change**. Original exports remain untouched.
An independent byte mask confirms that all unrelated payload bytes, including
animation, remain exact. All 120 animation worlds compare exactly, and canonical
skin differences from the original copies stay below 0.002018 mm.

A second actual engine capture measures fidelity against the **original
non-derivative exports**, preserving the original reference and thresholds:

| Import | Peak A skin error | Peak B skin error | Hand gap |
| --- | ---: | ---: | ---: |
| Original export | 0.151963 mm | 0.151786 mm | 30.015644 mm, fails |
| Weight derivative | 0.002023 mm | 0.001846 mm | 29.979758 mm, passes |

Both derivative actors pass joint pose, skin fidelity, floor and full motion
caps. All three hand point targets pass. Of the 256 observed floor/global
conditions, one still fails: own-palm orientation. Partner-body depths are
outside this engine measurement population. The 40 failures measured in the
original raw/saved copies are not silently cleared or transferred as verified
geometry results for the derivative. The hand gap remains a generous
development screen, not proof of a believable high-five.

Evidence: `reports/all-violator-godot-weight-tests-v1`,
`reports/all-violator-godot-weights-v1` and both
`reports/all-violator-engine-fidelity-v1` / `v2`. No default export or selected
asset is replaced by these experiments.

A separate capture reader imports neither the producer nor the weight writer.
It reconstructs all 120 pose arrays, skin-position errors and floor depths for
each of the four actor/capture combinations, plus the three point observations
in each capture. Every recorded observation compares exactly. This is replay
of sealed actual engine output, not another engine execution or new body-depth
query. The first reader stops before measurements on an incorrect pose-helper
import path; it is preserved. A fresh v2 fixes only that path and completes.
Evidence: `reports/all-violator-engine-replay-v1` / `v2`.

Export retains a 2 GiB process-tree cap; pure numerical checks retain 512 MiB.
The separate actual-engine profile includes the engine child and complete
imported topology within a 1 GiB cap, with a 768 MiB admission estimate. All
retain the 600 MiB available-memory reserve. Global/model admission defaults
remain unchanged. No model inference, training or weight/data change occurs.
All release capabilities and genuine human-review requirements remain open.
