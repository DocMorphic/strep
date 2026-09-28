# Character movement profiles for arbitrary action requests

2026-09-27. Authoring path and matched composite-profile generation check complete. Profile response and release quality are not approved.

The Studio composer can now attach one reusable movement profile to every segment in an arbitrary action request. Profiles retain a name, style, training, current state, rule-set name and up to twelve game stats. Each stat has a 0–100 integer value and either no mapping or three editable text descriptions selected at 0–33, 34–66 and 67–100. Values within a band intentionally use the same description. This is an explicit designer policy, not a learned physiological interpretation of RPG stats.

The example policy includes agility, strength, balance, mobility and coordination descriptions. Endurance deliberately has no default description: its number remains in the saved profile, while an author can describe current fatigue separately. Custom stats and custom rules are supported. Fitness is not silently added as a second multiplier over the same capabilities. These example descriptions are hypotheses about art direction; no output is certified as agile, strong or physically capable merely because the profile requests it.

## End-to-end data contract

`motion_profile.py` validates and resolves the profile without modifying the user's action text or input object. The composer shows the resolved description before generation. Profile drafts survive reload, and reusing a profiled request restores its rules; reusing an ordinary request clears the profile. The read-only local `/api/motion-brief` endpoint remains available while a model worker is busy, using the same origin/host restrictions as other Studio requests.

The encoder and model both consume the same resolved segment descriptions. Profile request hashes bind the original request, applied/unmapped rules, compiler version, compiler file hash and resolved text. Requests without profiles retain their prior digest and conditioning behavior. Changed descriptions cannot reuse an unrelated conditioning cache. The original action timeline remains separate from the expanded description.

Profile jobs retain `motion-briefs.json` and the implementation snapshot. Generated records and each animation package retain `motion-brief.json`, including original and resolved prompts, numeric values, rule descriptions, compiler provenance and unreviewed status. The Studio inspector displays the generated brief, and the download is available alongside the animation pack. A raw model-generated profile response is not a deterministic joint-angle control or a force/endurance simulation.

## Validation so far

Twenty-nine focused profile/request tests pass. They cover rule boundaries, custom stats, unmapped metadata, immutable source text, overlong/invalid inputs, exact legacy digests, profile-sensitive cache validation and the read-only brief API while generation is busy. The full suite passes 378 tests in 112.76 seconds with four existing Torch deprecation warnings. Module and inline JavaScript syntax checks pass.

Browser checks exercise profile enabling, training/style/current-state fields, high agility/balance selections, a two-action request, the resolved preview and persistence through reload. A character-loading focus change initially covered the composer; bringing the composer forward resolved the interaction. Browser DOM-evaluation commands timed out, so restored values were verified through accessibility state instead. No browser errors were reported.

`benchmarks/motion-profile-sequence-v1.json` freezes a matched integration check: an eight-second balance-and-bow sequence, plain versus one composite parkour profile, both seed 44 with the unchanged checkpoint. This comparison can verify data flow and changed motion output; it cannot attribute effects to individual stats or validate monotonic style response. `scripts/verify_motion_profile.py` checks the saved brief, cache, package bytes, every decoded pose and full-skin integer/half-frame floor depths. Both requests completed on the unchanged checkpoint in 249.63 seconds total including encoding and exports, peaking at 3.35 GB process-tree RSS. Individual generation took 22.6 seconds plain and 25.4 seconds profiled. The four conditioning cache entries, checkpoint hash, implementation snapshot, original timeline, all package members, and every decoded joint pose were verified. Plain/profile joint-component RMS difference is 9.25 cm; this establishes different outputs only.

Both GLBs have zero validator errors and warnings. Actual Godot playback passes for both 240-frame clips (480 frames total), with maximum joint-position error 3.78e-7 m. All five served GLB/package/brief downloads match local hashes. Packages contain ten files for plain and eleven for profiled, including the resolved brief and license.

Independent decoded full-mesh maximum floor depth is 9.75 mm plain versus 7.79 mm profiled; half-frame depths are 9.50/7.57 mm. A separate all-eight-weight SOMA audit is attached to Studio. These exceed the stricter 5 mm diagnostic used in recent contact experiments, but remain below the release matrix's currently proposed 10 mm surface limit. The release gates are still provisional; this is not a release pass. Neither clip is quality-approved. The saved brief, text rules and numeric values are available in the Inspector and animation pack. No per-stat calibration, physical-strength interpretation, animator review or generalization is claimed.

Next evaluation must isolate individual rule changes across several actions and seeds, retaining a no-profile baseline and measuring action preservation as well as recognizability. Object/partner constraints, rig quality and release review remain separate open requirements.

Completed-take browser checks confirm the generated brief, surface audit, profile restoration, and clearing when editing a plain request. The profile draft was restored afterward. The grey SOMA character remains visible after scrubbing. These are UI checks, not perceptual motion ratings.
