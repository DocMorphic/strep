# Developer review of the full motion population

The raw breadth study covers 390 actor clips from 72 cases across 12 action families and five seeds. Its six independent-review packets require an independence attestation. The project owner chose developer review first, so developer observations now have a separate packet identity, export schema and importer. The existing native correction reviewer and rig/scene feedback tools remain useful for their own editing workflows; this mode covers the complete raw diagnostic population.

`scripts/developer_packet_review.py prepare` verifies an existing portable neutral packet's complete inventory and clip bindings, then creates a fresh developer packet and ZIP. Every clip, prompt, timing field and missing-context restriction is copied unchanged. The original packet and archive are preserved. The viewer and local dependencies are bundled from current source, and each developer packet gets a new UUID and browser storage key. Organizer keys, model weights and workspace dependencies are excluded from the ZIP.

```powershell
python scripts/developer_packet_review.py prepare PATH_TO_INDEPENDENT_PACKET PATH_TO_NEW_PACKET PATH_TO_NEW_ZIP
```

Extract the complete ZIP, run `python serve.py` (or `py -3 serve.py` on Windows), and open the printed local URL. A WebGL browser and Python 3 are required. No account, motion model or network download is needed for review. The user supplies every rating. Use normal-speed playback first and retain poor takes. For unavailable object or partner context, contacts/collisions must remain N/A with an explanation.

The export uses `strep-developer-packet-review-v1`, with `human_review=true`, `review_type=developer`, `independent_human=false`, `quality_approved=false` and `release_approved=false`. It contains the exact packet/manifest binding and the same five-category rubric and cleanup records as independent review. Cleanup requires actual edits to the downloaded clip, active editing seconds and operations; playback time is not cleanup. Abandoned and time-limited attempts are retained. These are human attestations, not machine verification of editing or animation quality.

```powershell
python scripts/developer_packet_review.py import PATH_TO_DEVELOPER_PACKET PATH_TO_EXPORTED_JSON PATH_TO_FRESH_IMPORT_FOLDER
```

The importer checks the role, complete response fields, packet and manifest hashes, clip hashes, duplicate or unknown clips, ratings, unavailable-context restrictions and cleanup records. It retains the original response byte-for-byte. Partial review is allowed and reports the missing clips. The independent importer rejects developer responses and developer packets, including an independent response forged with the developer packet's identity. Developer import never grants release approval or substitutes for independent animator evidence.

## Validation

The focused suite has 47 passing Python tests across the existing independent validator, portable packaging and new developer mode. Synthetic fixtures exercise partial review, role/approval rejection, exact source preservation, all clips and contexts retained, archive inventory, changed/escaping clips, organizer data exclusion, immutable imports and actual-cleanup record rules. The JavaScript tests execute the role and export helper, including rejection of unknown roles and prevention of a stale identity injecting independence or approval into a developer export. No fixture is a real review record. The same 47 Python checks and both JavaScript scripts also pass in a fresh source-only copy containing no vendor checkout, downloaded character assets or models; packet-copy licenses and runtime files are explicit synthetic fixtures. A second JavaScript test executes the actual page form and export handlers with a synthetic DOM. It checks save/reload, role-specific storage and response fields, missing-context N/A, attestation rejection and reached-time-limit cleanup. It creates no renderer, server, browser or rating file.

Full viewer rendering and browser interaction have not been revalidated in this change. No GPU renderer or live Studio is used. Preparing packets is not action-quality evidence, and the raw study is development data rather than a held-out release comparison. Human ratings and actual cleanup measurements are still absent.

The complete six-round developer set is prepared under `reports/developer-breadth-review-v1`. Every round retains 65 actor clips and all 12 families. All 390 clips, source packet inventories, original archive bindings, case contexts and 3,480 ZIP members were verified without running an HTTP server, browser or GPU renderer. The 200 flat-floor-eligible and 190 missing-context clips retain their original restrictions. All original independent packets and ZIPs remain unchanged. Human reviews and cleanup measurements collected remain zero. The local organizer index is `reports/developer-breadth-review-v1/README.md`; evidence is `completion.json`, `request.json` and per-round `checks`. The packet builder exited successfully and was consumed.
