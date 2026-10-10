# Broad development text–motion retrieval

The entire existing `breadth-v2-round-01-a` raw population now has a semantic diagnostic: **48/52 clips rank their intended description first; 52/52 rank it within the first three** among thirteen competing descriptions. This does not establish realistic animation or release approval. All fourteen project capabilities remain unapproved.

## Fixed population and methods

The batch comprises twelve action families, thirteen character tracks and four seeds per track: 1301, 2089, 3253 and 4099. It contains backpedaling, broad jumping, kneeling/recovery, a jab/cross/retreat, beckoning, grapevine dancing, tying a shoe, lifting a ground box, two handshake roles, stairs, freestyle swimming and exhausted walking. Every original raw clip is evaluated at its original 30 Hz clock, with 150–240 frames. No clip is cropped, regenerated, selected by outcome or admitted to training. These are already exposed **development** actions; no held-out action is used.

The optional [NVIDIA TMR-SOMA-RP-v1](https://huggingface.co/nvidia/TMR-SOMA-RP-v1) critic is pinned to revision `e427752ae3446dedba49e928c93ddc9f0e413401`. The [evaluator ledger](../benchmarks/text-motion-evaluator-v1.json) records the checkpoint, statistics and license hashes. Approximately 42.35 MB of encoder weights are acquired locally under the checkpoint's own license; neither those weights nor raw BONES recordings are published. This optional evaluator is separate from the existing four-model offline installer experiment.

`scripts/score_text_motion.py` reconstructs the verified checkpoint configuration, loads tensor-only weights with `weights_only=True`, evaluates the posterior mean in FP32 on CPU and uses the official SOMA representation/canonicalization. It supplies the original cached 4096-dimensional text features directly to the top text encoder. Those caches came from the experimental original-precision disk-offloaded encoder: full resident 8B equivalence remains unproven. No new Llama inference or text encoding runs here.

All 221 input/method bindings are checked before and after computation. Archived outputs contain all text/motion latents, the complete 52 × 13 score matrix, target ranks, competing descriptions and score margins. Scores use `(dot(unit motion latent, unit text latent) + 1) / 2`; they are not correctness probabilities. Exact ties retain best/worst ranks, and the reported counts use the conservative worst rank. This is motion-to-description retrieval over this declared set, **not the official benchmark's R-precision**.

## Results and limitations

All eleven non-partner tracks score 4/4 top-one matches. The initiating handshake role scores 1/4; the receiving role scores 3/4. The four misses rank the other handshake role first and their intended role second:

| Intended role / seed | Margin to the other role |
| --- | ---: |
| Initiating / 1301 | −0.000659684 |
| Initiating / 3253 | −0.002495569 |
| Initiating / 4099 | −0.000736640 |
| Receiving / 2089 | −0.000391073 |

The model card explicitly documents limited sensitivity to small details such as handedness. Its single-person embedding cannot certify two hands actually meet, a box is grasped, a foot is planted, the floor supports a swimmer, sequence beats occur at the requested times or an animator can use the result. In particular, high lift/handshake similarity does not override the project's failed scene-contact measurements. No critic threshold is calibrated, no physical test is relaxed and no human review is inferred.

`scripts/audit_text_motion_scores.py` independently replays all **676 scalar dot products**, rank/tie/margin/count arithmetic, the ordered complete population and unchanged source bindings. Maximum dot-product discrepancy is below `1e-12`; the receipt hash is `47121d9f4d4840ccf7d8f15dd5e3a30d9dfdbb5692741da0f53a9b6c4a35b6c1`. This audits the saved scores; it does not independently certify the representation, learned encoders or original text-encoder fidelity.

## Validation and retained failures

Eighteen model-free checks cover competing actions, repeated seeds, ties, opposite vectors, incomplete/nonfinite/nonunit inputs, changed source/embeddings/scores/ranks/counts and false approval. The complete local model run takes 17.188 execution seconds, with a sampled process-tree peak of 773,443,584 bytes. It uses an explicit bounded CPU estimate of 1 GiB plus 600 MiB reserve; full geometry/native studies retain their separate 2 GiB estimate. All 22 producer, six scalar-auditor and seven final test resource observations independently replay.

The first wrapper attempt incorrectly declares every clip as 150 frames; the second mishandles the unbatched latent return shape. Their failed protocols/logs remain intact. The successful fresh V3 protocol uses original per-track frame counts and explicit batched latents; its protocol hash is `af8bd0d207c5c5ceac3322b247bfcccce69e8b6d5270741106149b7b207b9372`, and its embedding hash is `e75188712877fcd4e2e45f9f367ec44d51ce99724ca0778934bf618960b3c58d`.

To repeat on a separately provisioned workstation, acquire the ledger's exact TMR revision and its license/statistics/encoder files; supply an immutable development protocol with original motion/text cache paths and SHA-256 bindings. Run `scripts/score_text_motion.py PROTOCOL FRESH_OUTPUT` through the resource supervisor, then audit the saved result through `scripts/audit_text_motion_scores.py PROTOCOL OUTPUT FRESH_RECEIPT`. Private development outputs and the local Hub metadata receipt are acquisition inputs, not bundled public assets. Preserve the full population and failed attempts when changing the protocol.

Next validate fine distinctions and action timing against developer ratings, then calibrate any semantic filter on a separate declared population. Keep the held-out evaluation frozen until that decision. Scene mechanics, rig transfer, transitions and timed cleanup remain independent release requirements.
