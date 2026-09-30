# Interaction model availability and correction strategy

Checked 2026-09-30 against primary repositories and revision-pinned files.
This is a focused follow-up to [the earlier survey](interaction-research-v3.md),
not an exhaustive claim about available research. No model, motion dataset or
body-model assets were downloaded, and no external project code was executed.
Only documentation, license text and a dependency script were inspected.

## Additional findings

- **PhysiGen** describes collision guidance using geometric body proxies and
  releases core collision/evaluation code. Its README still marks the complete
  training/inference pipeline, bounding-box parameters and checkpoints as
  unreleased. It declares Apache-2.0, but the linked root `LICENSE` returned
  HTTP 404 at the captured revision. It is a method reference, not a qualified
  replacement checkpoint. [Pinned author README](https://github.com/iSEE-Laboratory/PhysiGen/blob/126292014d28d726fa7061cdbe7b7c7671d6ebb7/readme.md).
- **Human-X Interaction** has MIT-licensed code and an available reaction
  diffusion planner. Its capture and physics-tracking components are still
  described as forthcoming. The inspected dependency script fetches supporting
  encoders/evaluators; it does not establish a released interaction-generator
  checkpoint. Data and body-model requirements remain separate. No Windows
  feasibility or commercial model qualification is inferred.
  [Pinned README](https://github.com/humanx-interaction/Human-X-Interaction/blob/b0e73acb58906bc0985183a373effcab27dab063/README.md),
  [license](https://github.com/humanx-interaction/Human-X-Interaction/blob/b0e73acb58906bc0985183a373effcab27dab063/LICENSE),
  [dependency script](https://github.com/humanx-interaction/Human-X-Interaction/blob/b0e73acb58906bc0985183a373effcab27dab063/scripts/download_deps.sh).
- **GNOCHI** generates reacting poses conditioned on a posed body and offers
  optional collision refinement. Its license explicitly covers code and
  released weights under CC-BY-NC-ND-4.0. It is not selected for Strep's
  commercial product path, and pose generation alone would not establish
  animation continuity. [Pinned README](https://github.com/GonzaloGNogales/gnochi/blob/efa74ea727c9841a9b0d0392be4862959a001b52/README.md),
  [license](https://github.com/GonzaloGNogales/gnochi/blob/efa74ea727c9841a9b0d0392be4862959a001b52/LICENSE).
- **InterGen** was rechecked: its README provides training/inference directions
  and a checkpoint-download route, but states a noncommercial CC-BY-NC-SA-4.0
  license for its material. Public download availability does not qualify it
  for the product. [Pinned author README](https://github.com/tr3e/InterGen/blob/b1750df4a859443b8a69329f759ce3a7503ae179/README.md).

## Consequence for Strep

These checks do not establish a ready, qualified interaction model to substitute
for Kimodo. Physics guidance and reactive generation remain useful research
directions, with acquisition, training rights, local execution, rig transfer
and editable export requiring separate evidence. Proxy collision results would
still need checks against the supplied character's actual skin geometry.

The [three-key local study](paired-multikey-hand-v1.md) passes original motion
limits yet retains a 20.932848 mm hand peak and 15 failing sample times, with
some local regressions. The [six-key study](paired-extended-hand-v1.md) is still
running at this inspection. Do not report its intermediate scores as final
geometry results.

If the completed longer-support audit does not materially improve clearance,
the next concrete experiment should remove the artificial equal-and-opposite
wrist-offset restriction. The [independent control module](paired-independent-controls-v1.md)
already preserves legacy exports exactly in tests. Integrate it with explicit
layout metadata, the verified symmetric warm start and unchanged per-actor
motion/guide/contact limits. Compare at the same timestamps and record
directional regressions. Any promising result still needs full-body geometry,
engine and human review; additional control freedom is not proof of feasibility.

If that bounded study also fails, examine measured active constraints and
initial interaction motion before merely adding more optimizer iterations or
silently enlarging quality tolerances. The broader generation, object, editing,
retargeting and release requirements remain part of the same goal.

## Evidence record

`reports/interaction-research-v4/manifest.json` records repository revisions,
file URLs, saved-file hashes and the failed PhysiGen license fetch. Original
retrieved files stay in ignored local reports. No dependencies or runtime
configuration changed. All release capabilities remain unapproved.

Manifest SHA-256: `49cffaba5bb9e45d58f174bb48c7229e2148769bbad5542227af3d64c6a30c88`.
