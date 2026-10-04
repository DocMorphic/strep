# Explicit contact patch revisions in Studio

The native scene editor can now revise a source patch, a partner patch, or both
sides together without deleting and recreating the contact. It records explicit
new contact intent and retains the entire original authoring draft. Supplied
character clips, placements, objects, durations, timing, contact limits,
geometry conditions and bounded object-edit settings are preserved.

This follows [contact-region review](native-contact-region-review-v1.md): exposed
whole-hand candidates are not automatically substituted for an intended palm.
The author uses the existing mesh picking or bone/box draft controls to choose
a localized patch. Deformation ownership and geometric selection still do not
establish anatomical correctness.

## Authoring workflow

1. Load a scene draft and select the existing contact under **Revise an existing
   contact patch**.
2. In Mesh contacts, pick the source character's intended surface and choose
   **Stage selected source patch**. For a partner contact, select the partner's
   clip, pick its surface and stage it separately.
3. Choose individual point correspondence or the arithmetic average patch
   position explicitly. Changing this reduction changes contact meaning.
4. Select **Preview patch changes**. The original draft remains untouched. The
   backend validates both the original and proposed scene and checks exact asset
   bindings. The comparison shows patch counts/reductions and original/authored
   endpoint separation, with expandable exact references and endpoint positions.
5. Inspect the staged geometry and comparison, then **Apply reviewed changes**.
   Apply repeats validation and requires the same preview and implementation
   receipts. Applying modifies only the local draft; saving or building is a
   separate action.
6. **Restore original draft** reverses all contact revisions and restores the
   original authoring controls. Other authoring fields are locked while a
   revision is active, so their changes cannot masquerade as a patch update.

Source and partner changes are applied atomically. Individual correspondence
must preserve equal measured-point counts on both sides; the workflow does not
pair points automatically. World and object targets preserve their exact point
arrays. Patches contain 1–256 distinct existing native mesh references, with no
truncation. Oversized selections must be explicitly refined by the author.

Changing the chosen contact, staged patch, reduction or draft invalidates a
pending preview. Failed, late, malformed and duplicate responses cannot apply
changes. Rechecking an unavailable or changed source preserves the original
draft. A delayed character-add response also rejects a changed scene draft.

## Binding and source preservation

`scripts/native_contact_revision.py` defines
`strep-native-contact-revision-v1`. A revised Studio draft contains an additional
`contact_revision` record:

```json
{
  "schema": "strep-native-contact-revision-v1",
  "baseline": "<complete original Studio draft object>",
  "edits": [
    {
      "id": "<existing contact ID>",
      "source": {
        "glb_sha256": "<exact actor asset SHA-256>",
        "vertices": [[0, 0, 14712], [0, 0, 14713]],
        "reduction": "centroid"
      },
      "partner": null
    }
  ]
}
```

The baseline above represents an object, not a literal string; the references
are illustrative. Each edit must change an existing contact, and IDs must be
unique. A partner choice has the same patch structure. The backend reconstructs
the proposed draft from the baseline and exact patches, then requires equality
with the submitted draft. Hidden changes to targets, timing, actor selection,
placements, limits, geometry, other contacts or edit settings reject the request.
The baseline cannot contain another revision record. Multiple subsequent patch
choices retain the first complete baseline and the final explicit choices.

`/api/native-scene-contact-revision` is a read-only POST using existing local
host/origin, JSON and 1 MiB request guards. It does not dispatch a worker, edit a
file or load a model. Existing objects are optional for this preview, so an
ordinary high-five needs no artificial prop. The current scene-asset builder
still requires an object; character-only asset orchestration remains a separate
open requirement.

Endpoint inspection uses the supplied native skeleton and actor placement at an
exact touch time, or both hold endpoints. It is not a whole-hold measurement,
surface-facing test, collision check or feasibility decision. The preview binds
the canonical draft and baseline, all actor hashes and the Python implementation.
Its anatomical-review flag remains pending, and quality/training/release flags
remain false. Explicit patch changes do not become animator approval.

## Offline worker and export

Preparation validates the revision again, snapshots the complete original and
revised authoring draft, preserves the original actor bytes and archives the
revision implementation with the existing native scene methods. Frozen jobs
reject altered provenance or source files. Older ordinary job archives remain
readable using their archived methods; they cannot start as current jobs.

The existing scene worker continues to measure contacts, bounded object
proposals, complete sampled geometry, native engine resources and replay. A
completed worker may still report failed contact/geometry conditions. Character
motion is not regenerated or edited by the revision workflow. This does not
resume the character fitter or rebuild its source-rate caps from a corrected
clip; integrating revised intent with source-bound character correction remains
future work.

Revised packages include a hashed `contact-revision.json` containing original
contacts, authored contacts, exact patch choices, actor hashes and the portable
scene hash. The standalone intent record is also a fixed validated download.
Both original and new conditions remain visible; a new centroid condition is
not evidence that the old fixed-point condition was solved. Existing ordinary
packages retain their format. Failed or changed saved evidence blocks downloads.

## Validation scope

Offline Python checks cover world/object/partner patches, atomic individual
correspondence, explicit centroids, original scene and hard-limit preservation,
hidden changes, invalid material references, oversized populations, asset
mutation, endpoint inspection, host/origin/size guards, retained portable intent
and older ordinary archives. Offline Node checks exercise the actual editor
module with transport/DOM test doubles, including stage/preview/apply, source
and method changes, malformed and late responses, duplicate clicks, successive
revisions and restoration. The generated desktop must match its editable
sources. These are not browser rendering or human-review evidence.

The final related Python run passes 166 tests in 304.88 seconds. The initial
integration run retained two generated-page mismatch failures; rebuilding the
Studio from its editable sources fixes them. Three final Node workflows pass,
followed by all four actual saved preview responses through the production
editor with offline DOM/transport stubs. The latest four generated-desktop
checks also pass. No live browser layout or click-through is claimed.

Four existing development clips exercise explicit localized selections from
the prior declared regions. The diagnostic recipes use a 12 mm sphere around
the original contact point at the contact start, or 75 mm for the coarse crawl
rig, and retain every matching vertex. These recipes are not human-authored
anatomical annotations. They create separately labelled new centroid conditions.

| Existing clip | Selected vertices per source / partner region | Contact-time rows | Original / authored point conditions |
| --- | --- | ---: | --- |
| Source high-five | 21 / 21 | 1 | Fail / fail |
| Corrected high-five | 21 / 21 | 1 | Pass / pass |
| Crawl | 19, 19, 33, 33 | 144 | Fail / fail |
| Sphere hold | 15, 15 | 2,066 | Pass / pass |

All 2,212 contact-time rows retain their original clocks and numeric limits.
Source bytes stay unchanged, and all original/authored observation arrays have
exact dtype, shape and byte readback. Repeated bound previews match exactly.
The corrected high-five's old mesh-collision failure is not repaired by changing
contact intent; neither point pass establishes anatomical or motion quality.

An actual headless CPU Godot 4.7.2 procedural fixture completes all eight worker
stages at 1,101 full-scene times. It contains two object holds plus explicit world
and partner touches, and revises all four contacts. The portable package retains
original and authored conditions, unchanged character bytes and exact sidecar
readback. Source contacts, the bounded object proposal and combined sampled
conditions fail; those failures remain visible in the saved result and download
manifest. This validates orchestration/export of failed candidates, not realistic
humanoid motion. The prior ordinary procedural job and its package stay unchanged
and remain readable under their archived methods.

Bound local evidence is in `reports/native-contact-revision-validation-v1/`,
including `checks.json`, `editor-replay.json` and `release-checks.json`. Its actual
worker is `reports/native-scene-jobs/contact-revision-canary-v1/`. Raw studies,
source payloads and generated outputs stay local. No new model, seed, reserved
held-out case, submitted human review or anatomical label is supplied. All 14
release capability evidence lists and frozen acceptance gates remain unchanged.

The full goal remains active. Next integrate explicit localized intent into
character correction while preserving original source epochs, remove the
character-only worker gap, and continue broader motion-quality and developer
cleanup review. Action categories remain evaluation strata, not a whitelist.
