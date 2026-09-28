# Portable review packets for broad motion

The first breadth round now has a model-free reviewer packet containing all **65 actor clips**, with neutral IDs and randomized order. It retains every take from that round, including numerical failures. The organizer's source/seed key is outside the packet. No independent human ratings or cleanup records have been collected.

Use [the relocated reviewer](http://127.0.0.1:8771/viewer.html) on this laptop. The distributable artifact is `reports/breadth-human-review-v2/reviewer-round-01-v2.zip`; no one has been contacted and nothing has been sent externally. Share only the ZIP when reviewers are arranged, never the sibling private key or research folder.

## What changed

`review_session.build_many` combines completed action jobs without filtering their trials by quality. It checks source containment and hashes, preserves the GLB motion payload, removes extras and replaces scene/animation labels. The breadth builder additionally verifies the exact frozen case/actor/seed population for a complete round; it refuses missing, duplicate or selectively omitted takes.

The viewer now frames all clip poses, supports horizontal root following or a fixed world view, checks each downloaded GLB against its manifest hash before displaying it, and preserves normal-speed playback/scrubbing. Bone bounds plus a 0.18 m skin allowance provide practical SOMA framing, not a strict mesh-bounds certificate. Numeric quality diagnostics and seed/condition labels remain hidden.

Required but absent scene context is disclosed. For those clips, contacts/collisions cannot receive a numeric score: the reviewer must choose N/A and explain why. The response validator enforces the same rule. No N/A choice, reason, score, identity or human attestation is filled automatically. Action ratings in these cases assess the visible actor only; they cannot establish a complete object or partner interaction. Flat-floor cases retain the contact rubric. Swimming starts with the ground grid hidden.

The packet includes Three.js, the eight-weight SOMA skin helper, licenses and a Python-standard-library loopback server. It needs an installed Python 3 and a WebGL browser, but no model weights, accounts, Strep workspace or online dependency downloads. Extract the whole ZIP, run `python serve.py` (or `py -3 serve.py` on Windows), then open the printed localhost URL. The README explains browser drafts, separate reviewer profiles, JSON export and actual cleanup timing. This is not a standalone Python installer or second-hardware qualification.

## Validation and retained failure

The initial archive's files and motion payloads verified, but browser execution failed: bundled import addresses lacked the `./` prefix required for relative module resolution. The failed archive, relocated folder and browser-error record remain intact. Revision 2 fixes only path resolution; the review manifest, clip bytes, order and organizer key are unchanged.

Revision 2 was extracted to **`C:/wassup/Strep Review Test v2`**, served independently on port 8771. The verifier checked all 578 inventoried files, all 579 archive members, every source/neutral GLB document and binary comparison, all 65 HTTP clip downloads and seven runtime/document downloads. These match their retained hashes. Browser tests exercised swimming and jumping, frame seeking, playback, world/follow framing and canvas interaction. Missing-context scores are disabled, all ratings remain blank, saved reviews remain 0/65, and export is refused without reviewer identity and attestation. The only recorded browser error predates the corrected reload. A full-page screenshot showed a stitching duplicate; DOM counts confirmed one actual form and one field per rating.

The focused suite passed **26 tests** in 1.02 seconds after the path fix. Test ratings are synthetic fixtures only and do not enter evaluation. No full-suite claim is made for this turn. The frozen breadth generator and dependencies were revalidated unchanged; its run continues independently.

Evidence is in `reports/breadth-human-review-v2`: `build.json`, `initial-browser-failure.json`, `build-v2.json`, `verification.json`, `verification-v2.json`, `ui-verification.json`, `runtime.json`, `focused-tests-v2.json` and implementation snapshots. The first verification is transport evidence for the failed UI version, not an overall pass.

## Continuing the study

Use `scripts/build_breadth_review.py --round N --output NEW_PACKET --key PRIVATE_KEY --archive NEW_ZIP --seed RANDOMIZATION_SEED --evidence NEW_BUILD_RECORD` only after both seed shards of that round complete. The command verifies the frozen population before packaging. Separate independent reviewers should use separate browser profiles; repeated sessions by the same reviewer are not independent reviewers.

Import actual reviewer JSON with the existing `scripts/review_session.py import PACKET RESPONSE --output NEW_DIRECTORY` workflow. Import still rejects changed assets, invalid packet binding, duplicate/unknown clips, invalid or unexplained scores and invented cleanup fields. A syntactically valid response is an attestation, not identity or independence verification. Missing reviews, paired cleanup comparisons and the final held-out release study remain open. This diagnostic round is not release approval.
