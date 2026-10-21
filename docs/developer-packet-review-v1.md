# Developer review of the full motion population

The raw breadth study covers 390 actor clips from 72 cases across 12 action families and five seeds. Its six independent-review packets require an independence attestation. The project owner chose developer review first, so developer observations now have a separate packet identity, export schema and importer. The existing native correction reviewer and rig/scene feedback tools remain useful for their own editing workflows; this mode covers the complete raw diagnostic population.

`scripts/developer_packet_review.py prepare` verifies an existing portable neutral packet's complete inventory and clip bindings, then creates a fresh developer packet and ZIP. Every clip, prompt, timing field and missing-context restriction is copied unchanged. The original packet and archive are preserved. The viewer and local dependencies are bundled from current source, and each developer packet gets a new UUID and browser storage key. Organizer keys, model weights and workspace dependencies are excluded from the ZIP.

```powershell
python scripts/developer_packet_review.py prepare PATH_TO_INDEPENDENT_PACKET PATH_TO_NEW_PACKET PATH_TO_NEW_ZIP
```

Extract the complete ZIP, run `python serve.py` (or `py -3 serve.py` on Windows), and open the printed local URL. A WebGL browser and Python 3 are required. No account, motion model or network download is needed for review. The user supplies every rating. Use normal-speed playback first and retain poor takes. For unavailable object or partner context, contacts/collisions must remain N/A with an explanation.

## Windows walkthrough for the crawl comparison

Use the latest local packet, which includes the saved-timer validation fix.
Python 3 and a browser with WebGL are required. These files are generated local
outputs, not included in a fresh GitHub clone.

1. Press **Windows+E** to open File Explorer. Paste
   `C:\wassup\strep\reports\crawl-native-developer-review-timer-v1`
   into its address bar and press Enter.
2. Right-click `crawl-developer-review.zip`, choose **Extract All**, and extract
   the complete archive to a new folder. Open the extracted folder containing
   `Start Review.cmd`, `serve.py`, `viewer.html`, `clips` and `runtime`.
3. Double-click **Start Review.cmd**. Leave its command window open while
   reviewing; it serves the files locally and opens your default browser.
4. If the browser does not open, copy the printed address into it. The default is
   `http://127.0.0.1:8771/viewer.html`. This address works only while the launcher
   is running. Do not double-click `viewer.html` to launch the review.
5. Enter a reviewer identifier and check the human developer-review attestation.
   Select a clip and watch its complete motion at normal speed before scoring.
   Use **Play**, **Restart** and the timeline; drag to orbit and scroll to zoom.
   Click **Fit clip** if the character moves out of view. Use **Front** and
   **Side** to compare viewpoints and keep **Ground grid** visible for contact.
   Inspect the crawl's floor contact, supporting hands and knees, torso movement,
   limb intersections and any sudden changes. Compare each labeled condition
   independently; a correction is allowed to look worse.
6. Fill every rating, the major-defect answer, confidence and any notes. Record
   the visible problem and playback time, such as a knee slipping at 1.2 s.
   Leave cleanup **Not performed** unless you actually edit the downloaded clip.
   Click **Save this review**, then select the next clip and repeat.
7. Click **Export saved reviews**. Keep the downloaded JSON file and return it
   to the organizer for import. The viewer does not upload it.
   A partial export is allowed; its saved-review
   count shows what remains. Press Ctrl+C in the launcher's command window after
   finishing.

If the launcher reports an occupied port, first close the earlier review server
with Ctrl+C. Alternatively, open PowerShell in the extracted folder by typing
`powershell` in File Explorer's address bar, then run
`py -3 serve.py --port 8772 --open`. Use the same browser profile and port when
returning to saved ratings; changing either can make those ratings unavailable
in the current page. Export existing reviews before switching.

The earlier `crawl-native-developer-review-v2` and
`crawl-native-developer-review-launcher-v1` folders remain preserved. The latest
packet retains their original two clips, manifest and review identity; only the
timer module and integrity record differ from the launcher edition. All 520 ZIP
members were verified. See
[timer validation evidence](cleanup-timing-v1.md#restored-timer-validation-2026-10-21).

These steps use the existing local crawl packet. They do not start the Studio
server, run the motion model or convert developer feedback into independent
animator approval.

The export uses `strep-developer-packet-review-v1`, with `human_review=true`, `review_type=developer`, `independent_human=false`, `quality_approved=false` and `release_approved=false`. It contains the exact packet/manifest binding and the same five-category rubric and cleanup records as independent review. Cleanup requires actual edits to the downloaded clip, active editing seconds and operations; playback time is not cleanup. Abandoned and time-limited attempts are retained. These are human attestations, not machine verification of editing or animation quality.

```powershell
python scripts/developer_packet_review.py import PATH_TO_DEVELOPER_PACKET PATH_TO_EXPORTED_JSON PATH_TO_FRESH_IMPORT_FOLDER
```

The importer checks the role, complete response fields, packet and manifest hashes, clip hashes, duplicate or unknown clips, ratings, unavailable-context restrictions and cleanup records. It retains the original response byte-for-byte. Partial review is allowed and reports the missing clips. The independent importer rejects developer responses and developer packets, including an independent response forged with the developer packet's identity. Developer import never grants release approval or substitutes for independent animator evidence.

## Validation

The focused suite has 47 passing Python tests across the existing independent validator, portable packaging and new developer mode. Synthetic fixtures exercise partial review, role/approval rejection, exact source preservation, all clips and contexts retained, archive inventory, changed/escaping clips, organizer data exclusion, immutable imports and actual-cleanup record rules. The JavaScript tests execute the role and export helper, including rejection of unknown roles and prevention of a stale identity injecting independence or approval into a developer export. No fixture is a real review record. The same 47 Python checks and both JavaScript scripts also pass in a fresh source-only copy containing no vendor checkout, downloaded character assets or models; packet-copy licenses and runtime files are explicit synthetic fixtures. A second JavaScript test executes the actual page form and export handlers with a synthetic DOM. It checks save/reload, role-specific storage and response fields, missing-context N/A, attestation rejection and reached-time-limit cleanup. It creates no renderer, server, browser or rating file.

Full viewer rendering and browser interaction have not been revalidated in this change. No GPU renderer or live Studio is used. Preparing packets is not action-quality evidence, and the raw study is development data rather than a held-out release comparison. Human ratings and actual cleanup measurements are still absent.

The complete six-round developer set is prepared under `reports/developer-breadth-review-v1`. Every round retains 65 actor clips and all 12 families. All 390 clips, source packet inventories, original archive bindings, case contexts and 3,480 ZIP members were verified without running an HTTP server, browser or GPU renderer. The 200 flat-floor-eligible and 190 missing-context clips retain their original restrictions. All original independent packets and ZIPs remain unchanged. Human reviews and cleanup measurements collected remain zero. The local organizer index is `reports/developer-breadth-review-v1/README.md`; evidence is `completion.json`, `request.json` and per-round `checks`. The packet builder exited successfully and was consumed.

## Launcher validation (2026-10-21)

All **70 tests** across portable packaging, developer review, independent review and native-asset review pass in the guarded integration run. The source hashes remain unchanged and the complete resource trace replays. The 13 portable/launcher checks are included in that total, not an additional population. The Windows command launcher was executed from a directory containing spaces and an ampersand using a recording-only Python child; it passed the expected arguments and used the packet directory. Server/browser calls were replaced with test doubles to check successful loopback binding, occupied ports, invalid ports, missing packet manifests, manual startup, browser-launch failures and closing after interruption. No HTTP server, browser or motion model was launched by these checks.

The developer importer accepts the new inventoried launcher while retaining compatibility with old packets. Existing role separation, rating validation, missing-context rules, immutable imports and original clip preservation remain tested. The earlier local test failure came from quoting the command path in the test harness; its raw output is retained. No launcher success was claimed from that failed run.

The first broader integration had 68 passing checks and two missing-runtime setup failures. The detached checkout lacked Three.js; the existing local installation was copied unchanged, its complete file hashes were pinned, and the full suite was rerun. No production or test assertions were changed to resolve those setup failures.

Local evidence: `reports/review-launcher-v3`, `reports/review-launcher-integration-v2` and `reports/review-launcher-v2/packet-result.json`. The fresh crawl archive has two exact original clips and 520 verified members. The original packet and review identity are unchanged. Live browser rendering, actual human ratings, timed cleanup and release approval remain unverified.
