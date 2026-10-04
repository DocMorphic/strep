# Paired cleanup measurements

`scripts/paired_cleanup_analysis.py` compares actual imported human cleanup records for explicitly matched baseline and candidate clips. It never produces ratings or editing times. Developer and independent review remain separate strata, with no pooled estimate or release approval. The breadth packets currently contain raw development motion; they do not supply a baseline-versus-candidate cleanup experiment by themselves.

Before collecting comparison data, the organizer must define and freeze the matched conditions, action/rig/scene equivalence, cleanup endpoint, time limit, assignment and order. Use the unchanged checkpoint and export baseline required by the research plan. Retain every attempted pair and poor take. Condition keys belong outside reviewer packets and Git. Packet IDs and clip IDs in this design identify neutral review copies, not generator conditions displayed to reviewers. Family labels are arbitrary evaluation strata and do not restrict supported prompts.

Each pair uses distinct clips, each used once in the design, and the same reviewer on both sides. Missing responses stay missing; another person's candidate review cannot fill a baseline review. Reviewer identifiers and independence are attestations, not verified identities. The analyzer does not verify frozen study design, randomization, order, actual edits or equivalence of paired motions.

Place organizer inputs in a dedicated directory. An explicit design has this structure:

```json
{
  "schema": "strep-paired-cleanup-design-v1",
  "pairs": [{
    "id": "matched-case-001",
    "family": "object_manipulation",
    "baseline": {"packet_id": "BASELINE_PACKET_ID", "clip_id": "clip-001"},
    "candidate": {"packet_id": "CANDIDATE_PACKET_ID", "clip_id": "clip-001"}
  }]
}
```

After reviewers export responses, import them with the existing role-specific importer described in [developer-packet-review-v1.md](developer-packet-review-v1.md) or [human-review-v1.md](human-review-v1.md). Bind the design, packet manifests and imported responses in an analysis configuration. Paths resolve relative to the configuration file; SHA-256 values must be actual full lowercase digests.

```json
{
  "schema": "strep-paired-cleanup-analysis-v1",
  "design": {"path": "design.json", "sha256": "DESIGN_SHA256"},
  "packets": [
    {"path": "baseline-packet", "manifest_sha256": "BASELINE_MANIFEST_SHA256"},
    {"path": "candidate-packet", "manifest_sha256": "CANDIDATE_MANIFEST_SHA256"}
  ],
  "imports": [
    {"path": "baseline-review-import", "response_sha256": "BASELINE_RESPONSE_SHA256"},
    {"path": "candidate-review-import", "response_sha256": "CANDIDATE_RESPONSE_SHA256"}
  ]
}
```

```powershell
python scripts/paired_cleanup_analysis.py PATH_TO_CONFIG --output PATH_TO_FRESH_ANALYSIS_FOLDER
```

The fresh output must be separate from all input directories. The analyzer revalidates every response with its original role validator, checks imported validation results, hashes every packet clip, rejects changed bindings and duplicate imports, and checks that inputs remain unchanged before saving. It preserves all specified pairs, each observed reviewer, raw cleanup records, unused imported attempts and provenance. Existing analysis folders cannot be overwritten. No model, browser, server or engine is required.

For a completed pair with positive baseline time `B` and candidate time `C`, the reported reduction is `1 - C / B`. The completed-pair-only median is the median of those pairwise fractions, **not** a ratio of aggregate medians. It may be biased by which edits were completed. Zero baseline times retain their absolute difference but have no percentage reduction. Missing, unperformed and abandoned attempts remain visible and have no assumed completion time. Abandonment is not treated as ordinary censoring.

A reached time limit supplies a lower bound on eventual completion time using the reported active elapsed time, which may exceed the configured limit. For example, a completed 100-second baseline and a candidate stopped after 74 seconds yield an upper bound of 26% reduction, with no finite lower bound. A timed-out 100-second baseline with a completed 60-second candidate yields a conditional reduction between 40% and 100%. These bounds assume eventual finite completion. The tool reports bounds on the median among completed or censored pairs with positive baseline elapsed time, with that subset's count. It does not impute missing/abandoned pairs or claim a full-population bound. Unbounded endpoints are explicit JSON nulls with flags.

Summaries report reviewer and design counts, status counts, completed-pair coverage and results separately by role and family. With no imports, medians and bounds are null and observed-reviewer counts are zero. No inferential confidence interval, automatic threshold verdict or release approval is computed. The proposed cleanup reduction gate must be calibrated and frozen with the other release gates before release evaluation.

Validation uses synthetic records only, including changed input rejection, separate roles and packet identities, missing counterparts, timeouts, abandonment, zero times and immutable inputs. All 82 focused checks across the analyzer, existing independent/developer validators and portable packet module pass in both the working tree and a fresh source-only copy without vendor code, downloaded assets or models. Local evidence is `reports/paired-cleanup-analysis-clean-source-v1`; the checks are included in the Windows/Ubuntu source CI. These fixtures are not human evidence. Actual human ratings and measured cleanup times remain absent.
