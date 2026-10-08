# Fixed saved-reference contact diagnostics

Interaction planning can now explain a necessary contact-distance failure using saved target tracks even when targets occupy different rigid frames. This holds the recorded world coordinates fixed. A partner's resampled/refitted motion can change those coordinates, so this diagnostic never becomes a joint-generation blocker or a general infeasibility claim.

The optional `reference_tracks` authoring input contains the original scene and complete evaluation source/clock identifiers plus every contact's complete target-world track. Scene metadata must match, actor paths/checksums must agree, contact IDs must be distinct and complete, all target coordinates must be finite, and constant world targets must match their authored points across the full clock. The check preserves every overlapping same-joint pair and every requested integer frame. It uses exact rational comparisons of the supplied rounded values under ideal rigidity; it does not recertify the producer's transformations or reconstruct poses/meshes. Mesh/region source points remain unassessed rather than becoming joint proxies.

Studio projects its saved evaluation to those complete target tracks, displays fixed-reference conflicts separately from intrinsic metadata contradictions, and includes them in the checked-plan download. Original motion profiles, timing and contact intent remain unchanged. The reference report explicitly records `joint_generation_blocker=false`, `producer_correctness_revalidated=false`, and unapproved feasibility/quality. Inputs exceeding 262,144 target points or pair-frames reject without thinning; these are diagnostic computation budgets.

Inspect a saved scene/evaluation bundle offline:

```text
python scripts/scene_reference_contact_consistency.py saved-scene.json reports/reference-check.json
```

The CLI binds the complete input file and diagnostic methods before reading, rechecks their bytes before exclusive output creation, and preserves previous output. Source-file identities are checked as supplied metadata; the CLI does not read source pose archives. The separate development scan below additionally hashes the actor archives without loading their arrays.

The complete original ten-scene/twenty-variant collection retains ten overlapping pairs. Five wrist high-five pair-frames have a fixed-reference conflict at frame 60; five palm pairs remain unassessed. For the wrist cases, both source contacts use the same zero-offset A wrist point. Its world meeting target and B's saved hand target are farther apart than their combined 6 cm tolerance:

| Development seed | Saved target separation, approximately |
| --- | ---: |
| 11 | 33.84 cm |
| 22 | 90.44 cm |
| 33 | 92.95 cm |
| 44 | 90.68 cm |
| 55 | 58.55 cm |

These comparisons explain why changing A alone while holding B's recorded target fixed cannot meet both point tolerances. Refitting/resampling B may remove this necessary failure; it does not certify reach, palm anatomy, normals, collision, dynamics or action correctness. Box variants have no qualifying same-joint pair, which is also not a feasibility pass. Existing contact/geometry failures remain unchanged.

A separate check enumerates all twenty variant populations and verifies these equal-source-offset cases directly with target-distance-squared greater than tolerance-sum-squared. It does not import the main diagnostic. Saved inputs and Fraction arithmetic are shared; producer/pose/geometry correctness is not independently replayed. Every input/archive/report hash is checked, and all original and development reports remain preserved.

Validation: 183 model-free Python tests and the offline Node editor check pass. Coverage includes complete target clocks, changed source/scene identities, missing/nonfinite values, off-event world-target drift, mesh exclusions, conditional outcomes changing with a partner reference, explicit population budgets, exclusive outputs/input races, direct handler stubs, profile/planner/preflight contracts and the reproducible desktop bundle. Browser appearance, live HTTP, source pose evaluation, inference/training, dependency acquisition, engine playback and human review are not performed.

The hosted inventory contains 392 Python modules, four shards of 98 per operating system, and 37 Node scripts; validation of this commit is pending. All fourteen release evidence arrays remain empty and the whole-project goal remains active. Next compare appropriately bound native/model-reference failures and fit consistent references before sampling when execution is permitted; keep reference-specific failure distinct from jointly changing actor feasibility.
