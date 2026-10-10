# Completed contact search-step comparison

The fresh 0.10 branch completes the comparison begun in [the interrupted two-branch run](contact-search-comparison-v1.md). Both complete alternatives are independently measured and have exactly matching saved origins, original limits, references, row population, selected frames 102–104, completed V11 schedule and per-fit budgets. The original interrupted run remains unchanged. No model generation, checkpoint changes or training occur.

The fresh worker replays the original recovered motion, rather than starting from the newer 0.03 correction. It retains two local backoffs and completes the whole original 62-key interval with all 22,720 rows. No original passing row is lost and no protected original failed row regresses. Its native guard completes in 1,023.782 execution seconds with a sampled peak of 1,122,123,776 bytes; all 1,068 resource observations independently replay.

Four predeclared auditors run in fresh Torch-free processes, binding 4,282 required source/artifact files. They reconstruct 74 local records/222 native poses, two retained steps, three margin attempts, six correction proposals and 36 proposal archive files. Complete source/proposed geometry and retention reconstruct all 22,720 rows, exterior keys, original bounds and previous parameters. The fourth auditor checks matched starting arrays including precision, every compared protocol field, complete row labels/initial slacks, separate schedules and retained-score arithmetic against the already completed 0.03 replay. The guard completes in 81.984 execution seconds with a sampled peak of 316,841,984 bytes; all 430 resource observations independently replay. The full 2 GiB estimate plus 600 MiB reserve remains unchanged.

| Measurement | Search trust 0.03 | Search trust 0.10 |
|---|---:|---:|
| Per-fit soft budget | 300 s | 300 s |
| Actual local fit time | 162.078 s | 305.781 s |
| Retained local steps | 1 | 2 |
| Stop | Linear start unavailable | Time/measurement budget |
| Complete physical contact passes | 0/62 | 0/62 |
| Complete keyed contact passes | 0/62 | 0/62 |
| Worst normalized interval violation | 2.484240303 | 2.484240303 |
| Squared normalized interval violation | 3086.784413 | 3088.391594 |
| Worst selected-frame penetration | 21.509 mm | 21.276 mm |

The budgets match, but consumed local times differ because one branch stops early. SLSQP may overshoot its soft deadline during a native call; the separate hard supervisor remains in force. Startup and total worker times are not a matched runtime comparison.

The larger step improves selected maximum penetration and some hand orientations slightly more, but has a worse aggregate violation score. A separate post-replay comparison of the two measured retained row populations finds:

- Larger relative to smaller: one passing row lost, 64 protected regressions and no newly passing rows. These consist of two normal rows and 62 object rows; the lost passing row is `object:box:RightHandIndex4:frame-104`.
- Smaller relative to larger: no passing row lost, 25 protected regressions and one newly passing row.

**Neither alternative dominates. Keep the already verified 0.03 continuation and its complete schedule.** The larger result remains a separately valid diagnostic branch relative to their original recovered parent; its original retention decision is not rewritten. It cannot replace the 0.03 state under the current preservation policy. This single development fixture/window is not evidence for changing global search defaults or selecting a radius for every action.

Both branches attempt the same new window. Coverage remains **14/21 unique attempted windows with seven remaining**, rather than advancing twice. Full physical and keyed contact passes remain **0/62**. Left-hand orientation errors still exceed the unchanged 10° limit, and selected surface penetration remains about 19–22 mm. No solved lifting/contact, between-key, dynamics, event/scene metadata, engine or human-quality certificate follows.

Both alternatives now have editable baseline/candidate body GLBs. Source mesh/materials/eight weights and all 180 keys at 30 fps are retained; fixed-skeleton reconstruction differs from saved joints by at most 1.302 micrometres and serialization position differs by at most 0.102 micrometres. Upstream licenses and immutable independent replay/input bindings accompany the exports. These are body-only assets; scene objects, events, intermediate-time contacts, dynamics, engine playback and human quality remain uncertified. The larger-alternative export first defers for 600.922 seconds without a child, with all 595 resource observations replayed. A fresh attempt completes in 12.890 execution seconds, sampled peak 124,125,184 bytes and 39 replayed observations. Both attempts preserve the full original admission policy and their separate records.

Key private receipts under `reports/contact-trust-comparison-v2/`:

- Complete stage: `386a4bfd0b2eb4571f5eac819844705f84a8c23f4c435592f31753a62058733e`.
- Complete branch/schedule: `6208d10625b7c97e1a1819b7acd663979fa52f95f10d934c9f9737be4a43c47c`.
- Independent local replay: `3aefa5dccec25925d6075c66a93a5a19821e2e49701065e290eef838928ec169`.
- Independent interval replay: `d53c28c283088a480688dfa7edf644bfff7357753c6d48af5ce6e108af60325d`.
- Four-process audit execution: `2e74db272e841bd17b79008653b1b08bbdba17206c4bc3955f8c03acb8227a21`.
- Independently matched retained comparison: `b88d7395113ec8a1ea4765cdaacf3de5a9fc08a53733e3df638d92af264c7c86`.
- Post-replay alternative row comparison: `316e8da81671761bd17a677631ba4ded3f4df711eecde47708c4777f728e01c8`.
- Native resource replay: `1e9306470fb811ebfe65d8685b7ac554379e9b40e899f05c4162004c2c6bcb4b`.
- Audit resource replay: `2af1093d94c43189a372f23a303b3c404c7938ea71ad43a2f28917813abe8817`.
- Larger-alternative editable body export verification: `a4e83eefbbd5ad39efda6626c76301674e926df58bd0e5c7ef7261a5247f2fce`.
- Successful export resource replay: `320e7dda648fa85a4234d1f0ddd021630b30f89f7ea7f179f8b45b4ada809e91`.

The 102 focused source checks remain passed; code is unchanged since their validation. All twelve jobs in [hosted CI run 38016622368](https://github.com/DocMorphic/strep/actions/runs/38016622368) succeed on source head `7bb7086`, including the native CPU suites on Linux and Windows. Later documentation changes have separate CI status. All fourteen release capabilities remain unapproved, the inventory retains 19 gaps and genuine ratings/cleanup trials remain absent. Continue remaining coverage from the 0.03 state, diagnose constraint/correction tradeoffs and pose-conditioning failures, and advance broader actions, scenes/partners, rigs, editing/style, transitions, engines, dynamics and real review under the same active full-project goal. A larger search step alone has not solved this interaction.
