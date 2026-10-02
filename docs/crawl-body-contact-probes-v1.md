# Crawl hand and shin contact diagnostics

The existing mesh-contact editor accepts arbitrary explicit vertex patches;
it already permits hand, shin and body targets. This development probe uses it
on three previously examined crawl clips: CesiumMan and Quaternius female/male,
three assets across two rig families. It does not add a prompt whitelist or
claim independently annotated support surfaces.

The public [probe specification](../benchmarks/crawl-body-contact-probes-v1.json)
binds every source GLB, selected vertex index, joint role, target and budget.
For each mapped shin joint or hand subtree, select the three reference vertices
nearest the joint among vertices with at least 65% total relevant skin weight,
breaking ties by source index. These are geometry proxies. A surface near the
shin joint is not necessarily the kneecap, and a surface near the wrist is not
necessarily the palm; reviewed anatomy remains necessary.

Targets retain the patch centroid's X/Z at frame 54 and set Y to ground zero.
All four intervals are frames 54–56 inclusive, fixed before inspection. This
short diagnostic does not assert that simultaneous stationary support is the
correct crawling contact schedule. The existing screens remain 5 mm sampled
whole-mesh floor depth and 20 mm patch-centroid target error. The existing root,
joint and per-step budgets remain unchanged.

## Source measurements

| Character | Whole-clip maximum floor depth | Left / right shin maximum target error | Left / right hand maximum target error | Failed intervals |
| --- | --- | --- | --- | --- |
| CesiumMan | 7.821 mm | 14.430 / 40.684 mm | 140.697 / 102.596 mm | 3 / 4 |
| Quaternius female | 48.343 mm | 31.282 / 47.586 mm | 187.503 / 147.937 mm | 4 / 4 |
| Quaternius male | 88.755 mm | 35.291 / 48.851 mm | 184.040 / 148.640 mm | 4 / 4 |

These failures establish a mismatch to these authored proxies. They cannot
alone distinguish incorrect anatomy, inappropriate targets, rig transfer
defects or incorrect generated action semantics. No independently reviewed
palm/knee contact or force/balance conclusion follows.

## First fixed fitting pilot

The first declared case, CesiumMan, runs through the real Studio mesh-contact
worker without changing the draft, screens or solver budget. The workflow
edits the complete 120-frame clip under its global floor objective; it does
not promise unchanged motion outside the three contact frames.

Maximum patch error improves from 140.697 to 109.487 mm but remains far above
20 mm. Worst floor depth worsens from 7.821 to 15.663 mm, although failing
floor frames decrease from 41 to three. The candidate is marked **rejected**
for both floor and contact screens; the original input remains available.
Root edits reach 28.203 mm horizontally and 25.058 mm vertically; root steps
reach 14.950 mm within the original 15 mm limit. Joint edits and edit steps
remain within their authored bounds. This is not a successful support repair.

Independent reloaded-mesh inspection confirms 15.663 mm floor depth and two
failed hand target intervals. Every frame receives an edit, including 117
outside the contact interval. Saved controls show right forearm/hand edits of
zero degrees at frames 52/53, then approximately 5/10/15 degrees at frames
54/55/56, followed by decay. The current fitter solves sequential frames and
has no future-contact objective before frame 54. This motivates testing
anticipation or a coupled trajectory solver under the same limits; it does
not prove those targets are feasible or that look-ahead alone will solve them.

The solver's optimistic invariant-vertex floor bound is zero. That means it
cannot prove this floor request infeasible; it is not a feasibility certificate.
No new engine or GPU rendering validation was run for this rejected pilot.

## Reproduction and remaining work

Acquire the same licensed character/motion versions and verify the source hash.
Extract a case's `spec` into a JSON file, then use the existing inspector:

```powershell
.venv/Scripts/python.exe scripts/inspect_rig_contacts.py character.glb draft.json reports/my-body-inspection.json
```

Studio's **Edit mesh contacts** workflow can submit the same explicit draft.
The original inspection is local at `reports/crawl-body-contact-inspection-v1`;
the completed pilot and independent inspection are at
`reports/crawl-body-contact-pilot-v1`. The Studio job is
`reports/rig-jobs/crawl-body-contact-pilot-v1`. All raw source, candidate, solver
controls and failure outputs are retained.
Inspection result hash:
`bfd3be88af7c0be3def4ac0bf1155267e95b03a34593032cbc0d8d8bca4ed89b`.
Completed pilot result hash:
`921f66875c90bbd73ef1256b37b0fc770eb82d1be876c57140adbf197d87e6ed`.
The combined 831-file evidence rehash receipt is
`28058c0d69f12b9e4e322b3bfdb932cc1671dc6b7d914e3cb0aeaf76b2018ac7`.

Next review or replace the proxy patches/contact schedule and evaluate an
anticipatory bounded trajectory correction. Broader body/scene/partner actions,
semantic quality, clean import/playback, style/edit controls and human cleanup
remain required. No training, new generation, formal reserved held-out usage or
release approval occurred. All 14 release capabilities remain unapproved.

The subsequent [coupled trajectory pilot](crawl-body-contact-coupled-v1.md)
does anticipate these targets, but still fails contact limits and worsens
floor penetration. It includes fresh actual Godot joint playback checks of
the original and both candidates. Its retained failure motivates explicit
floor/contact feasibility constraints, alongside reviewed patches/scheduling.
