# Full development retrieval protocol

The complete exposed breadth baseline is now assembled into one critic protocol: **390 original actor clips, 78 character-track descriptions, 72 cases, twelve families and five seeds per track**. It includes all twelve original four-seed/fifth-seed batches, not a favorable subset. The 1,064 bindings cover raw motion, original generation records, conditioning, model/statistics/license metadata, catalog and methods. The protocol hash is `00e941ca67b18a0981e145c7049db9f844a9b6b98742eaaf97b5ccd315e88587`.

This is a harder development comparison than the earlier [52-clip study](text-motion-retrieval-v1.md): descriptions from the same action family compete directly. The original catalog explicitly says checkpoint-training overlap is unknown and these are not untouched release examples. Release reservations remain separate; no new motion, text feature, held-out result or clean-human training example is created.

## Complete results

The fresh V2 retry completes **390/390 clips**: the intended description ranks first for **295/390 (75.64%)** and within the first three for **359/390 (92.05%)**. Ninety-five clips miss the top rank; fifty receive a top match from another family. These are retrieval disagreements, not ninety-five proven incorrectly animated clips. Distinguish generator errors from critic errors with genuine review.

| Family | Clips | Intended description top one | Top three | Top match stays in family |
| --- | ---: | ---: | ---: | ---: |
| Aerial/nonwalking | 30 | 15 | 23 | 22 |
| Combat | 30 | 19 | 27 | 27 |
| Dance/performance | 30 | 24 | 26 | 30 |
| Environment traversal | 30 | 19 | 24 | 22 |
| Everyday tasks | 30 | 26 | 28 | 26 |
| Gestures/expression | 30 | 28 | 30 | 30 |
| Ground/recovery | 30 | 27 | 29 | 27 |
| Locomotion | 30 | 29 | 30 | 29 |
| Object manipulation | 30 | 28 | 30 | 28 |
| Parkour | 30 | 19 | 27 | 23 |
| Partner interaction | 60 | 34 | 57 | 49 |
| Stylized/capability | 30 | 27 | 28 | 27 |

The original 52 clips now score **42/52 top one and 50/52 top three**, compared with 48/52 and 52/52 using only thirteen descriptions. Their shared text and motion embeddings are numerically identical (maximum difference zero). The stricter result comes from adding competing descriptions, not changing the checkpoint or those generated clips. Keep the candidate bank fixed when comparing models/corrections; do not tune the bank until a desired rate passes.

The independent scalar audit checks every **30,420 matrix cell**, complete ordered populations, ranks/ties/margins/counts and all 1,064 source bindings. Maximum scalar discrepancy is `5.551115123125783e-16`; receipt hash: `ef46b3af38155a64def0caf4b266e055a69bf07a28311864f1cd6452c5214bb6`. This does not independently certify the neural representation, original text-encoder fidelity, contact or real action correctness.

## Execution and preserved failure

The successful fresh V2 producer runs in 65.109 execution seconds after 15.203 admission seconds, with a sampled process-tree peak of 785,326,080 bytes. All 79 producer and seven scalar-auditor resource observations independently replay. It retains the bounded CPU 1 GiB estimate plus 600 MiB reserve.

The first fresh model supervisor stops when sampled available RAM falls to 565,153,792 bytes, before producing embeddings or a result. Its incomplete pipeline and failed guard remain intact. All 25 failed resource observations independently replay as the `available_ram_guard` stop. The terminal supervisor is authoritative over that worker's stale `running` label. The successful retry uses separate output/guard paths and the same immutable complete-population protocol. No reserve, physical threshold, clip population or candidate description is reduced. Full contact/geometry auditors still retain their separate 2 GiB estimate plus reserve.

Twenty-seven focused source checks pass, including all 390 × 78 synthetic retrieval cells, exact ties, changed evidence, original-method snapshot validation and arbitrary-family/multi-batch provenance. The protocol preparer refuses missing/failed generation, changed motion/cache/clock and duplicate batches rather than silently removing denominator rows. These are software/provenance fixtures, not actual 390-clip quality measurements. All nine source-test resource observations independently replay.

## Reproducible preparation

Provision the exact optional [evaluator ledger](../benchmarks/text-motion-evaluator-v1.json) and original development outputs separately. `scripts/prepare_text_motion_study.py --development --catalog CATALOG --batches BATCH_1 BATCH_2 ... --output FRESH_PROTOCOL` binds every requested seed in every batch. For this study, use the original `reports/breadth-baseline-v2/protocol.json` catalog and the twelve `breadth-v2-round-01-a/b` through `breadth-v2-round-06-a/b` batch directories under `reports/action-jobs/`.

The critic supports up to 128 descriptions and 512 clips, processing one complete <=300-frame motion at a time at 30 Hz. It uses single-description, unprofiled requests; longer sequences or resolved style conditioning require separately declared evaluation protocols. These limits apply to this optional critic and do not define a whitelist for animation generation. Numerical scores still do not establish object/partner contact, timing details, physics, import quality or cleanup time.

The producer now saves exact original Python method bytes under each output's `implementation/` directory. The scalar auditor can validate those bytes against the original protocol when a later source update changes the live file; it still refuses changed motion, models and other data. The earlier 52-clip study's original methods were preserved before this update, and a fresh audit replays all 676 saved scores using two original method snapshots. No earlier motion, embedding, score, protocol or result is overwritten. Tests also reject a corrupt snapshot.

Next review disagreements in aerial motion, traversal, parkour and partner roles using complete object/partner context. Compare against genuine developer ratings before selecting a semantic threshold. Good object/partner retrieval does not override failed contact mechanics. All release approvals remain false.
