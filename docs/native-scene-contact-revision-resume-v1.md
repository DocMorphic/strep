# Contact revisions within a native correction source epoch

An author can change explicit mesh contact patches and continue a completed
native scene fit with `--contact-revision` and `--resume-from`. This changes
the contact objective while retaining the original character clips, placements,
object geometry and motion, contact targets, timing and limits. It applies to
world, object and partner contact patches; it does not infer anatomy or choose
a replacement patch automatically.

The revision receipt uses `strep-native-scene-fit-contact-revision-v1`:

```json
{
  "schema": "strep-native-scene-fit-contact-revision-v1",
  "original_contacts_sha256": "SHA256_OF_PRIOR_CONTACTS_JSON",
  "original_permissions_sha256": "SHA256_OF_PRIOR_PERMISSIONS_JSON",
  "edits": [
    {
      "id": "existing-contact-id",
      "source": {
        "glb_sha256": "UNCHANGED_ORIGINAL_ACTOR_GLB_SHA256",
        "vertices": [[6, 0, 1], [6, 0, 2]],
        "reduction": "centroid"
      },
      "partner": null
    }
  ]
}
```

References are existing `[mesh node, primitive, vertex]` triples in the supplied
GLB, not joint names or indices into a remeshed preview. The displayed triples
are examples, not a humanoid anatomical recipe. Partner patches use the same
record with the partner actor hash; both sides must preserve explicit point
correspondence. Non-partner targets cannot acquire a partner patch. Missing
references, duplicate edits, unchanged patches and unbound receipts fail.

Supply a revised contacts JSON that exactly matches the receipt's edits. Keep
the previous permissions JSON unchanged except for its `contacts_sha256` field,
which must bind the revised contacts bytes. Keep an existing geometry policy
unchanged except for the same contact binding. In particular, do not shorten
the geometry clock, remove planes, relax penetration limits, increase edit
bounds, change protected keys, or substitute the previous proposal as input.
Ordinary continuation now also rejects dropping or changing existing geometry
checks. Adding an explicit geometry policy to a previously unaudited epoch
remains possible. Revision of an epoch with an additional surface-facing contact
policy is explicitly unsupported for now and fails before a new job starts.

```powershell
reports/model-free-ci-v1/env/Scripts/python.exe scripts/native_scene_fit.py revised-contacts.json revised-permissions.json reports/revised-fit --proposal-model storage-vector --iterations 2 --restoration-steps 3 --resume-from reports/prior-fit --contact-revision revision.json --geometry-policy revised-geometry.json
```

The example CPU environment is local development tooling, not a bundled public
installer. Use a configured Python environment with the repository dependencies
on another machine. The CLI produces a proposal; the current Studio server is
not restarted or upgraded by this command.

Continuation reproduces the prior retained GLBs byte for byte before optimizing.
Original sampled motion-cap arrays must match in dtype and values, and the
decoded starting clip must pass the original protected constraints. The new
job archives the receipt, prior snapshots and source epoch; later ordinary
continuations recheck that revision receipt too. Both original and revised
contact intent are measured on the same final proposal, with complete point and
held-speed observations preserved. Old merit belongs to the old intent; a new
merit cannot be presented as improvement of that old requirement.

Storage-vector proposals protect each current contact condition individually
against regression and enforce the original edit, displacement and sampled
motion limits on accepted steps. Geometry is audited on the final proposal;
this mode does not enforce floor or triangle constraints on every intermediate
probe. Originals remain selected. Neither revised intent nor a successful audit
confirms realistic motion, anatomy, continuous collision, animator approval or
training eligibility.

## Retained crawl development comparison

The first native correction epoch uses a supplied, previously floor-restored
rough crawl clip: 19 joints and 3,273 original skin vertices. This is not the
earlier raw mocap or rig-transfer epoch. Explicit development permissions allow
one torso translation track and eight limb rotation tracks, 54 normalized
controls, a 1.3–2.3 s window, protected outer intervals, a 0.1 m translation
bound, 20 degree rotation bounds and a 0.15 m joint displacement bound. These
are logged experiment inputs, not anatomically approved defaults for other rigs.

The first fit attempts two primary iterations. Two continuations then each
attempt two further iterations from its exact retained export, with the same
trust, derivative step, 64 storage cells and up to three restoration solves.
One retains the original three-vertex contact patches; the other explicitly
revises them to 19/19/33/33-vertex centroid patches from a prior development
geometry recipe. The actor bytes, permission values, original sampled rate
arrays, targets, contact interval (1.8–1.8667 s) and 20 mm/0.005 m/s limits remain
unchanged. The revised regions have not received anatomical review.

Neither branch accepts a primary step. Both final exports are byte-identical
to their starting export. They pass the complete sampled native floor check
at 2,017 times, while all four held-contact conditions fail. Changing the patch
changes the measured requirement, as shown on that same retained motion:

| Contact | Original position error (mm) | Revised position error (mm) | Original slip (m/s) | Revised slip (m/s) |
| --- | ---: | ---: | ---: | ---: |
| Left shin | 19.016 | 37.841 | 0.191382 | 0.193128 |
| Right shin | 71.242 | 79.098 | 0.541481 | 0.548859 |
| Left hand | 78.486 | 91.806 | 0.272876 | 0.251903 |
| Right hand | 78.061 | 88.195 | 0.275883 | 0.275851 |

The lower left-hand slip for the revised region is not a motion improvement;
no correction was accepted. Both original and revised final contact audits keep
all native and twelve frame-population observations and exact array readback.
Original inputs remain selected.

A separate replay reconstructs all 68 retained trial/start/final GLB exports
byte for byte and rederives the source rate bins from the 477 original uniform
samples. Direct positional/angular speed and acceleration equations identify
source-rate excesses in all 62 attempted trial exports. The diagnostic arithmetic
uses a 1e-9 roundoff comparison allowance; the optimizer retains its original
1e-5 physical-unit rate allowance and its strict decoded acceptance checks.
Across the original branch trials the largest acceleration excesses are
0.004580 m/s² and 0.000818 rad/s²; revised trials reach 0.000878 m/s² and
0.000514 rad/s². These are witnesses for the finite rejected probes, not proof
that every feasible correction is impossible. Improving the proposal and
decoded restoration is the next motion-repair task; increasing a contact
tolerance or hiding the original failures would not solve it.

The retained export also completes actual CPU Godot 4.7.2 authoring, portable
game tracks and finite playback. All 2,017 times, full imported skin, three root
modes, initial/middle/end development markers and eleven malformed playback
configurations remain checked. Maximum imported/native vertex error is
0.089638 mm against the existing 0.1 mm numerical condition. Geometry and finite
playback pass; contact and combined scene conditions still fail. Original/revised
contact intent is read back from each scene/game/runtime ZIP, with exact actor
bytes and no synthetic prop. The fitting source epoch remains separately bound;
exporting its retained proposal does not replace that original source epoch.

Independent replay also recomputes all 4,034 native posed-triangle and floor
observations for the two continuations. Their maximum native floor depth is
4.954953 mm against the unchanged 5 mm bound. The geometry NPZ contains only
its clock for these plane-only scenes; plane reductions live in the JSON and
are recomputed from the full skin rather than inferred from archive readback.
Both old and revised patches are additionally measured on the retained actual
imported skin, preserving all 288 contact-time rows and their held-speed
populations. Both imported intent screens fail and their observations roundtrip
exactly. This is a separate replay of the same producer, not another inference
or motion-generation trial.

There are 135 passing related model-free Python cases across the corrected
test groups, including all 28 revision-specific cases. Initial test-fixture
mistakes, the replay's NumPy indexing mistake and an export-driver wrapper-field
mistake are retained locally. The actual authoring job completed before that
last assertion failed; its revalidated terminal outputs were reused for game
tracks/playback without rerunning the producer. The prior public commit
997b53a passes all four Windows/Linux CI jobs. This evidence does not establish
human motion quality, held-out generalization, GPU rendering, physical
interaction, training improvement or release approval.

Bound local records live in `reports/native-crawl-contact-repair-v1/`:
`continuation-release-checks.json`, `rate-witness-replay-v2/release-checks.json`
`engine-export-v2/release-checks.json` and
`intent-plane-replay-v1/release-checks.json`. The project-wide goal remains active;
the release acceptance gates and all capability evidence lists remain unchanged.
