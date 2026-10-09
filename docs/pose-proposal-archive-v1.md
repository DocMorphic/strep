# Streamed native pose proposal reports

`guarded_pose_restoration.py --archive-proposals` writes complete linearization and start records as immutable per-iteration metadata/NPZ pairs. Inline reporting remains the default. This changes report transport, not the geometry, objective, proposal caps, backoff fractions or nonlinear/tangent acceptance decisions.

`pose_proposal_archive.py` preserves the report tree, including empty and mixed lists. Homogeneous numeric lists use the existing observation archive, without truncation or precision reduction. Each compact reference binds metadata, NPZ and its full shape/dtype/logical-byte receipt. Replay rejects changed files, escaped paths, unknown identities, duplicate references and unreferenced/missing arrays. No pickle is accepted. Files publish to fresh paths; failures preserve partial artifacts. Archive transport supplies no geometry or quality certificate.

The solver reports through an optional storage callback. It keeps current numerical arrays and the last accepted controls; previous large report payloads leave memory after publication. Native resume reads external records one at a time, binds all files and replays original nonlinear/tangent decisions. Legacy inline implementation sets remain accepted and validated. Fixtures cover both formats and reject changed streamed records or promoted initialization/query data.

## Measured comparison

The matched V17 experiment repeats V15's thirty-step request from the same fully bound V13 frame 98, with unchanged physical thresholds, trust `.03`, ten inner iterations, body proposal margin `.001` and 300-second local budget. Only report transport changes. V15's interrupted output remains immutable and is not promoted as a terminal study.

| Evidence | Inline V15 | Streamed V17 |
| --- | --- | --- |
| Supervisor outcome | Available-RAM guard, exit 15 | Complete, exit 0 |
| Supervisor elapsed | 149.140 s | 151.156 s |
| Peak process-tree RSS | 2,174,091,264 bytes | 805,683,200 bytes |
| Saved pose observations | 231, partial study | 231, terminal study |
| Nonlinear accepted steps | 27, partial replay only | 27, full nonlinear/tangent replay |
| Main terminal JSON | Unavailable | 1,578,649 bytes |
| Separate proposal NPZ payload | None | 13,788,180 bytes |

Every audit and native pose array in the 231-record overlap matches exactly. Independent NumPy replay verifies all original/predecessor/method/pose bindings, 168 proposal archive files, complete vector envelopes/cuts, all physical hand/normal/depth/floor/reference/neighbor populations, and all 27 accepted nonlinear/tangent decisions. Recorded derivatives remain recorded derivative evidence, not an independent full native derivative certificate.

V17 stops with no guarded improvement after 104.203 local seconds, 230 measurements, 47 unretained queries, 182 backoffs and 28 starts. Squared violation decreases from 10.685808 to 6.549961. Maximum box penetration falls from 11.108 to 7.613 mm; body displacement falls from 222.062 to 221.929 mm and still fails 220 mm. Both grip points pass at 4.968/4.954 mm. Both palm orientations worsen to 19.876/19.712 degrees under the declared failed-row tradeoff policy and still fail 10 degrees. Floor, root, rotation and neighbor-speed checks pass; the full pose remains failed.

Source-only validation passes 284 focused tests across thirteen modules; 174 pass without Torch. The CI manifest now declares 406 Python modules, partitioned 102/102/101/101, and 39 Node suites. Focused checks are not full hosted-CI or release approval.

## Reproduction and limits

With separately acquired native inputs, use an owned supervisor for this request:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-streamed-repair/frame-98 --frame 98 --iterations 30 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 10 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v13/frame-98 --body-proposal preserve --proposal-start geometry-descent --body-headroom .001 --archive-proposals
```

The 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged. V18 is a preserved prelaunch RAM rejection, with no worker or observations. After RAM recovered, V19's owned resume worker was stopped after 10.265 seconds at 561,823,744 available bytes, before any saved pose; peak tree RSS was 586,072,064 bytes. No unrelated process was stopped. Fixture resume and complete native archive replay pass; actual native continuation from a streamed terminal source remains unverified. Legacy ancestor JSON still contributes to resume memory; streaming new records does not erase that cost.

Recorded V17 terminal vectors admit first-order directions that protect both failed normal rows with search margins `1e-6` and `.001`, with merit slopes `-1.210438` and `-1.210008`. These proposals do not certify finite nonlinear retention. They justify testing an explicit normal-preservation policy after verifying native resume; the current runner's normal tradeoff policy is unchanged.

Next resume verified V17, prevent palm-angle regressions under an explicit proposal/retention policy, then extend correction to coordinated windows and full temporal/geometry/engine replay. No source clip or preview is replaced and no generation, training, retargeted import or human evidence is added here. All fourteen capabilities of the broad arbitrary-action, scene/partner, editing/style, rig-transfer, transition/export and human-validation goal remain unapproved.
