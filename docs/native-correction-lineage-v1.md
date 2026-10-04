# Correction evidence in portable scene and game assets

Selected character correction files now carry their original clips, edit
permissions, source motion-cap archive and contact intent into portable scene
packages. Game and finite runtime packages preserve those entries byte for byte.
This closes a provenance gap when proposals become new scene inputs; it does not
approve a correction or transfer its numerical decisions to a different scene.

## What is preserved

For a selected asset from a completed `native-scene-fit-jobs` job, scene
preparation resolves its exact declared original or proposal URL and hash. A
portable snapshot contains every actor from that correction job, including
unchanged partners, both source and candidate GLBs, original/candidate contact
scenes, edit permissions, geometry policy and the exact source-rate NPZ archive.
Permissions and geometry keep all authored values while their contact hashes
are rebound to the portable original scene JSON. Mesh references, selected
animations, placements, object trajectories, clocks and limits are preserved.

Prior contact-intent audits from explicit patch revisions remain separate and
include portable scenes evaluating that intent on candidate motion. Ancestors
through both continued corrections and newly authored corrections of earlier
proposal files are retained. A fresh experiment remains distinguishable from a
continuation; source limits are never silently described as belonging to the
older epoch.

`corrections/record.json` maps each current scene actor to its correction actor,
selected role and hash. It distinguishes proposals, original clips and unchanged
participants. Each parent job records source/result/request hashes, controls,
solver options, original rate parameters and its measured decisions. Original
machine paths and raw logs are excluded from this portable record. Local
preparation separately binds complete parent inputs and retained snapshots.

The context-preservation field compares the whole current draft against the
parent's complete proposed scene, including every participant, placement, object,
contact and geometry policy. Renaming, translating, omitting partners or changing
targets/limits produces a different context. Parent decisions still describe the
parent job only; the new scene always receives its own contact and engine checks.
Neither context identity nor successful packaging supplies human approval.

## Packaging and integrity

The scene ZIP includes `corrections/record.json` and its complete referenced
artifact population. The provenance record is also a separate Studio download.
All entries participate in the existing scene package hashes and exact ZIP
readback. Game export copies these entries unchanged; finite runtime extraction
and packaging retain them within the original game manifest.

Preparation and later serving recheck selected sources, all correction parents,
record contents, material bytes and complete snapshot population. A changed cap
archive, source/candidate clip, permission, observation or parent receipt blocks
verification. Dropped or extra lineage files are rejected. Numerical failures
remain visible in diagnostic exports and never become animation-quality approval.
The ordinary UI still requires passing native and sampled geometry conditions
before explicitly staging a proposal. A diagnostic export of a failing proposal
is separate from that staging workflow and leaves Studio selection unchanged.

Complete snapshots support at most 16 correction jobs, 128 artifact files and
768 MiB of material. Exceeding a bound rejects the snapshot; ancestors, actors,
samples and precision are never silently truncated. Existing runtime limits on
the whole game ZIP still apply. Older scene/game archives retain their original
evidence scope; this feature does not retrofit missing provenance into them.

The archive records sampled motion limits and preserved authoring constraints.
It does not independently establish continuous collision freedom, source-rate
agreement after engine import, physical attachment, semantic correctness,
retargeting quality, animator cleanup or release readiness. Original character
and model licenses remain applicable.

## Validation and actual handoff

On 2026-10-04, 142 related Python cases passed, followed by nine final method and
compatibility checks, including two new cases: 144 unique cases in the union.
The new tests use actual procedural CPU correction jobs for complete partner
snapshots, original/proposal selection, context changes, patch-revision intent,
continued/fresh ancestry, cap/clip/permission tampering and complete portable
packages. Older ordinary archives retain their earlier method population; new
jobs cannot omit the lineage method or selected correction evidence. Mocked
engine cases test transport only and do not count as actual engine evidence.

An actual diagnostic handoff then exported the earlier retained humanoid root-only
correction proposal through the scene, game and finite runtime pipeline in
headless Godot 4.7.2. All three authoring stages and independent replay completed
at all 2,017 times. Sampled floor geometry passes; contact and combined scene
conditions still fail. Runtime checks pass for embedded, extracted and mixed root
modes and their previews, complete imported skin and a controlled authored
integration checkpoint. The unconfirmed support-inspection marker stays separate.
The checkpoint tests dispatch; it is not a contact event inferred from the motion
or a submitted human review.

Independent portable replay recomputes all original motion-cap arrays from the
packaged original clip, checks the protected source rows, reproduces the exact
candidate GLB bytes and reads back every contact observation. All lineage files
are identical across scene, game and runtime ZIPs. This does not rerun the
completed engine producer or reuse engine evidence from a different clip.

The exported diagnostic candidate is
`fb2cb45aa02c573d5fb5b65e67b0fe4bfdab280a11381e6d9c89143e12742b97`;
its original first native input is
`c638651bd985835edec75e860cb9582a882cfd28cbe9ca6ccf05f0dc71d3819a`.
The input is the previously floor-restored development crawl, rather than an
earlier raw model skeleton. No new inference, training, live Studio request,
server restart, GPU render, physics or animation-quality approval occurred.
All release gates remain open. Local evidence is retained under
`reports/native-correction-lineage-handoff-v1/`, including independent
`portable-replay-v1/result.json`; only methodology and source are published.
