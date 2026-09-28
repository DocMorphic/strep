# Complete portable breadth reviewer set

The six packets in `reports/breadth-review-set-v1/archives` contain all390 raw actor clips from72 cases across12 families and five seeds. Each round has12 cases,65 actor clips and all12 families. Both independently generated actors are retained for each partner case. The original corrected round01 archive is reused byte-for-byte; rounds02–06 are newly packaged with fixed organizer randomization seeds. No poor take is omitted.

The [organizer index](../reports/breadth-review-set-v1/README.md) links all six ZIPs. Nothing has been sent externally. Only the ZIPs belong in a blinded reviewer handoff; organizer keys remain outside every packet and archive.

## Verification

`scripts/build_breadth_review_set.py` freezes source protocol/completion/first-packet bindings and its implementation, verifies each round's exact request/seed population and missing-context instructions, and calls the established portable packager. Every archive is extracted into a fresh independent folder at `C:/wassup/Strep Review Set v3`. A temporary loopback-only server serves the relocated copies for verification and is closed after the run. Existing Studio/reviewer servers were unchanged.

All390 review GLBs match their original motion binary and scrubbed glTF document. The neutral copies remove metadata and condition/seed labels while preserving editable animation. Every ZIP entry, packet inventory, clip download and bundled runtime download was checked. Across the six packets, 3468 inventoried files and42 runtime/document HTTP downloads are recorded; all390 HTTP clip downloads match. Archives total380,287,675bytes.

`scripts/verify_breadth_review_set.py` independently joins organizer keys against the frozen72-case protocol and verifies all390 request/seed identities exactly once, all12 families in every round, current ZIP/clip hashes, packet identities, completion links and missing-context restrictions. Evidence: `completion.json`, `results.json`, per-round `checks` and `independent-verification.json`. Build exec68775 exited0 and was consumed; no builder remains live.

## Scope

There are200 flat-floor-eligible clips and190 clips missing required scene/partner/physical context. The latter require N/A with a reason for contacts/collisions, not a fabricated zero or success score. Their action ratings concern the visible actor only. All score fields remain blank; human reviews collected and cleanup comparisons remain zero.

This is the complete RAW DEVELOPMENT diagnostic population, not a held-out release study or an improved-motion comparison. Independent ratings, actual editing/cleanup timing, action correctness, scene interactions and release acceptance are still missing. Packaging/transport checks do not constitute human review. The previously tested viewer code is reused; no new browser-interaction certification was claimed in this build.

To use a ZIP, extract it completely, run `python serve.py`(Windows:`py -3 serve.py`), and open the printed loopback URL in a WebGL browser. Python3 is required; weights, accounts and online dependencies are not. The six packets share no rating store because each has a distinct packet identity. Independent reviewers should use separate profiles, enter their own records, and export JSON through the existing validated workflow.
