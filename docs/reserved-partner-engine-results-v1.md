# Reserved neutral partner import results

Pinned Godot 4.7.2 completed the [full neutral partner import audit](reserved-partner-engine-v1.md) on 2026-10-05. All three directed pairings and all six actor instances pass the original fixed limits. The audit covers **52,342 complete vertex observations, 390 bones and 114 mapped role origins**. It checks bone names/parents/world poses, complete skin bind/influence correspondence, triangles and mesh-space transforms, then reconstructs every imported neutral vertex from observed raw weights. Observed weights are not renormalized. The full saved-data reduction reproduces the result and every stored array; the next study's readiness check also verified that reduction.

| Pair / actor | Rig | Maximum joint position error (m) | Maximum full-skin position error (m) |
| --- | --- | ---: | ---: |
| 01 / A | 01 | 3.218e-7 | 8.191e-5 |
| 01 / B | 02 | 2.911e-7 | 7.783e-5 |
| 02 / A | 02 | 2.800e-7 | 7.935e-5 |
| 02 / B | 03 | 3.654e-7 | 8.124e-5 |
| 03 / A | 03 | 3.400e-7 | 8.294e-5 |
| 03 / B | 01 | 3.136e-7 | 8.491e-5 |

The limits remain **1e-5 m** joint position, **1e-5** basis component, **1e-4 m** full-skin position and **1e-7** mesh-space matrix component. The maximum observed basis component error is **6.557e-7**; mesh-space error is zero. Rounded table values are summaries of the saved full-precision records. These measurements describe CPU reconstruction of imported static skin and poses. They do not establish GPU appearance, animated contacts, collision, dynamics, anatomical facing, material hand targets or animator quality.

The import ran only after the original warm replay's exact outer/inner process handles both exited with code zero. That replay reproduced all seven closed populations, 6,216 edited keys and every numeric result in 2,552 fresh geometry samples. The import queue then saved its completed actual import and reduction receipt. Its own processes had already ended when the subsequent refinement was prepared; their OS exit codes were not separately captured. The next study therefore starts from checked completed receipts and a repeated complete saved-engine reduction, rather than claiming ownership of vanished process handles.

Local evidence:

- Actual import result: `reports/release-partner-reservations-engine-v1/result.json`, SHA256 `497745dfad63fc6aa89e04a93f20e91ed62013d3af5b955cfa762042c63a4578`.
- Completed serial import receipt: `reports/reserved-partner-engine-queue-v1/result.json`, SHA256 `0474d249f6191f188af2d80d72d5e86a95244efd3d347f160a050abed43e6f86`.
- Full warm replay: `reports/warm-endpoint-contacts-verification-v1/result.json`, SHA256 `41ed32f6436c7bbc070c5b17a8f773503418fdfa607e503132e6a49a15637d7d`.

The character payloads and Godot binary remain local. The reserved actors derive from two source meshes and one known skeleton/skinning topology with synthetic proportion changes; these are not independent artist rigs. No reserved motion prompt was sampled. Real human ratings and timed cleanup records remain zero, all fourteen release evidence arrays remain empty, and the full-project goal remains active.
