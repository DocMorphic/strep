# Explicit target response across actions

Status: all36takes complete; only dance meets the frozen numerical screen. No quality promotion. Same full-project goal remains active.

This development study tests whether a small authored hand/foot displacement survives generation across jumping, crawling, dancing and getting up. It uses the unchanged checkpoint,100diffusionsteps, original local text encoder, no movement profiles and no postprocessing. Three conditions share each prompt and seed: no guide, captured static pose, and offset static pose. Both guided conditions use the same root, heading and terminal orientation. The two static targets differ only in the selected limb chain and descendants.

Sources are the existing action-coverage seed11 raw clips. The four target choices were feasibility-checked once before the protocol was frozen, and every attempted target is retained. They are new action families for this target-editor check, not held out from model training or every prior project study. Seeds501/502/503 are fixed before generation. There are36takes across12requests.

| Action | Effector | Target frame | Offset (metres XYZ) | Static maximum edit |
|---|---|---:|---|---:|
| Jump and land | Right foot |45|0,0.06,0|14.128degrees|
| Crawl | Left hand |60|0.06,0,0|14.423degrees|
| Dance | Right hand |75|0,0.08,0|15.626degrees|
| Get up | Left foot |90|0,0.06,0|5.182degrees|

All four static edits reached within0.001mm under the45degree budget. Independent decoded-GLB verification confirms terminal orientation and unrelated world chains preserved. That accuracy applies to static target authoring, not generated motion. Source crawl/get-up poses already have75.477/97.620mm floor penetration, retained without filtering. Neither source nor target is quality approved.

The frozen primary screen uses the generated offset-minus-captured effector displacement at the authored frame, projected onto the requested direction. A seed passes only if response is at least half the requested offset and final error to the offset target is at most30mm. An action requires at least two of three seeds. All free/captured/offset errors, opposite-limb positions/travel, predicted support speeds and full eight-weight floor depths are retained. These are numerical diagnostics, not semantic correctness or limb-identity classification.

Protocol: `reports/pose-response-v1/protocol.json`. Request digest `bbadc10bb494fb1029364c197935169fba446a140cdebbb92223a3b23526fc55`. Frozen executable analyzer and implementation snapshots are preserved. Six scoring tests pass, including missing/duplicate triples, wrong direction, excessive distance, and invalid numbers. The application was not changed in this study.

Real execution is `reports/action-jobs/pose-response-v1`. A finalizer waits for the observed generator process to exit, then requires a complete pipeline before running ground audits, frozen analysis, glTF validation, actual Godot all-frame import and byte checks for servedGLBs/ZIPs. Failures are saved, never silently restarted. Finalizer state/log live in the study folder.

The comparison page is prepared at `reports/pose-response-v1/viewer.html`: paired grey characters, all three conditions, seeds, actual variable clip durations, cyan captured target, orange offset target, and an authored-frame button. It does not display partial generation as a successful result. Browser checks cover all four actions, all three conditions, seeds501and503, authored-frame jumps, and120/150/180frame timelines. Both grey characters and target markers render; no browser errors.

Action preservation, intended limb, naturalness and actual animator cleanup remain unreviewed. Do not promote this experiment to reliable capability/stat control or release approval solely from the numeric screen. After results, choose correction or model work based on measured failure, preserving unchanged-generation comparisons.

## Final measurements

| Action | Projected response, seeds501/502/503 | Offset error, seeds501/502/503 | Seed passes | Action screen |
|---|---|---|---|---|
| Jump and land |100.5% /77.4% /127.1%|25.2 /41.6 /64.1mm|1/3|Fail|
| Crawl |97.2% /102.8% /100.9%|34.6 /49.0 /21.3mm|1/3|Fail|
| Dance |97.5% /100.5% /93.7%|21.7 /33.6 /16.8mm|2/3|Pass numerical only|
| Get up |95.6% /85.5% /106.1%|42.5 /80.6 /41.6mm|0/3|Fail|

All12paired offsets move at least half the intended displacement, but only4/12also meet30mmabsolute error. This supports local directional response in these cases; it does not establish reliable absolute placement or action preservation.33/36rawclips exceed the proposed10mmfloor screen; maximum323.271mm. No half-frame floor audit or body/object collision certification was added by this study.

Generation pipeline520.55seconds, peak process-tree RSS3.079GB. Finalizer complete. All44GLBs (36motions +8static target previews) validate without errors or warnings. Godot imports5146pose samples with maximum world-joint position difference5.541e-7m.72servedGLB/ZIP byte checks pass. All generation request, cache, checkpoint, compiled constraint, source target, package member and raw-motion hashes are checked by the frozen analyzer.

The next engineering step is bounded temporal target correction with floor/support constraints, preserving raw generation and evaluating motion continuity and unwanted changes. Repeating a mobility wording sweep would not address the measured absolute-placement error. The corrected-output comparison must retain every failed target and source-floor defect.

An independent reviewer packet is available at `reports/pose-response-human-review-v1/viewer.html`; it randomizes36neutralclipIDs and removes condition/seed animation extras from copies. Original binary motion payloads and remaining glTF content are verified unchanged. It collects no ratings automatically. Review importer/tooling is described in `docs/human-review-v1.md`. No human reviews or cleanup times exist yet; this is collection capability, not evidence of approval.
