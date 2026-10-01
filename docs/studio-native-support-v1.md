# Native foot-support authoring in Studio

Characters now has a **Native foot supports** panel. Select a saved motion result
and version, load its exact exported GLB, check the thigh/knee/foot mapping, and
add fractional stance intervals. Choose frozen edit-boundary keys from the
selected chain’s original rotation clock. The panel exposes a static unit plane
normal and offset, clearance/gap, ankle displacement and local rotation bounds.
No stance or anatomical identity is inferred from an action prompt.

Submit a draft to create a separate native-support job. Input and draft are
snapshotted before launching the single-worker fit. This delegates to the
[native support method](native-support-intervals-v1.md) without changing its
support or source-relative rate gates. The output retains the input when the
input already satisfies sampled supports or no proposal meets all bounds.
Completion alone is not a correction success or quality approval.

Use **Refresh saved jobs → Compare input and proposals** to inspect a completed
job. The separate native viewer preserves seconds while switching versions and
seeks exact authored stance boundaries. It shows a grey character, the chosen
GLB-world plane, minimum/gap diagnostic times when a serialized proposal has
them, support heights, rate failures and all rejection reasons. Rejected trials
that produced no GLB are still reported. Input, final GLB, serialized proposals,
result audit, authored support markers and root tracks remain accessible.

## Isolation and provenance

- Draft storage binds to the selected GLB SHA-256, duration and mapped root.
  Changing the selected job/version invalidates the editor. Late metadata
  responses cannot attach to another selected version. Form changes must be
  added/replaced as intervals before submission.
- `POST /api/native-support-edits` accepts only an existing completed character
  job, supported version and strict native support spec. It accepts no arbitrary
  filesystem path. Invalid mapping, clocks, bounds or source hashes are rejected.
  Existing Host/Origin and exclusive local-worker guards remain in force.
- `reports/native-support-jobs/<id>/` contains the frozen source/draft/request,
  wrapper archive, live worker identity and terminal status. Fits use fresh
  immediate `reports/native-support-fit-<id>/` folders, preserving the CLI’s
  output contract and archived implementation.
- Completed reviews bind the frozen request, source and draft, archived wrapper,
  result and all declared fit outputs. Changed evidence invalidates discovery,
  review and asset serving. The namespace serves only declared output files;
  wrapper snapshots, implementation files, logs and unrelated files are
  inaccessible through that route. The declared input GLB is downloadable.
- The viewer hashes GLB bytes before loading. The same grey-material loader is
  used in the offline verification; embedded source materials/textures stay in
  the unchanged downloadable files. Four- and eight-weight skins are supported
  by this review renderer. Closing the panel unloads it; hiding Characters pauses
  its separate playback. It does not change the main character result selection.

These are the **selected exported GLB’s keys**. Preparing an existing rough clip
currently samples it at 30 fps upstream; this editor does not recover that
original file’s native keys. Repeated loop variants, helper-bone chains, multiple
skin primitives, non-LINEAR rotations, scene placements/moving geometry and
whole-sole/balance constraints remain outside this path. Plane coordinates are
GLB world coordinates, not a placed scene actor’s coordinates.

## Real development smoke tests

Both tests use existing Studio transfer `20260926-185422-40a6c246`, selected GLB
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`.
Duration is **3.9666666984558105 s**, with **120** native rotation keys. Left
thigh/knee/foot nodes are 8/9/10; right nodes are 4/5/6. Both authored stance
intervals are **[1.6, 2.4] s**, edit keys **[15, 105]**, clearance 0.25 mm,
maximum gap 5 mm, maximum ankle displacement 30 mm and maximum rotation 45°.

`smoke-native-support-v1` uses a Y-up plane at offset 0. The selected transfer
penetrates it by **58.584 mm left / 56.785 mm right** in the stance. All four
proposals reject the unreachable stance under the unchanged 30 mm limit. The
job completes with original input retained and four explicit rejection reasons.
Result SHA-256:
`e922ea123b16f036aca9b356136357c90c6efe330dac465446d46a6f036e340a`.

`smoke-native-support-v2` explicitly changes the plane offset to **−0.056 m**;
this is a different authored support condition, not a fix of the preceding
ground-zero test. Each of its four serialized proposals meets both foot-height
screens at **142 stance samples per foot**. Across proposals the minimum is
**0.249990 mm** and maximum lowest foot-region height is **1.866936 mm**. All
701 full-clip audit times preserve root/other branches and outside-edit motion.
Source-relative rate failures remain:

| Proposal | Position speed | Position acceleration | Angular speed | Angular acceleration |
| --- | ---: | ---: | ---: | ---: |
| 1 | 80 | 14 | 36 | 13 |
| 2 | 91 | 12 | 36 | 15 |
| 3 | 88 | 12 | 34 | 14 |
| 4 | 82 | 11 | 35 | 13 |

No proposal is selected; the final GLB is byte-identical to the input. Rate
derivatives use the full uniform 120 Hz clock and four equal bins from this
selected source; the **31.789 ns** derivative tail is reported. This does not
replace the earlier paired fixture’s independent original-baseline caps.
Result SHA-256:
`a2c4e1dfee64dec9b13c6322be0b0446bc14f7815bdee4f537191701017b5470`.

Offline Three.js/GLB verification loads all **six** v2 assets, preserves their
track population/native clocks, restores skin weights and checks forward and
backward poses at exact stance/end times, including identical repeated seeks.
There are **zero GLB errors** and one
`NODE_SKINNED_MESH_NON_ROOT` warning per asset, already present on the preserved
input. This is a loader check, not fresh browser rendering or engine validation.
Receipts are retained locally in `reports/native-support-studio-smoke-v2/`.

Synthetic tests exercise actual HTTP submission/serving, exclusive busy
rejection, origin guards, immutable snapshots, parent mutation, evidence
mutation, source/version changes, fractional clocks, failed worker retention
and drafts restored from browser storage. These do not provide human-motion
quality evidence. Model-free CI now installs the pinned process-inspection
dependency used by real worker/status handling.

The full model-free source suite passes **1,229 Python tests** and all **14
JavaScript suites**. The generated Studio bundle matches its editable sources.

## Next work and release status

The editor makes authored support conditions and measured failures accessible;
it does not solve contact and motion-rate feasibility together. Simultaneous
serialized rate/contact/orientation correction, broader rigs and scene supports,
engine checks and developer/animator review remain unfinished. There is no new
training, held-out use, submitted human review or release approval. All 14 release
capabilities remain unapproved under the single full-project goal.
