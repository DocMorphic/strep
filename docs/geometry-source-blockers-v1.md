# Protected source crossings in the scene transition

The retained generated scene has partner intersections in protected source phases. Bridge-only contact correction cannot clear these intersections while preserving the original phases and boundary tangents. The next correction needs a new source or scene edit scope; contact and penetration acceptance must remain explicit.

The diagnosis uses the completed Studio reserve proposal and its existing saved-resource reports. Both native and imported contact conditions passed previously, while geometry failed. These are generated closed-cube skins and arbitrary gesture clips, not production humanoid animation or a realistic high-five.

## Complete diagnostic populations

`native_geometry_failure_profile.py` classifies every saved condition against actor edit windows, additional protected spans, and fixed object/plane intent. An immutable failed condition has no editable actor at that sample. Potential editability does not prove a feasible correction.

The source audit derives the existing first/last key tangent guards from the selected native channels. Its classification therefore includes more protected samples than a window-only profile.

| Measurement | Native | Imported |
| --- | ---: | ---: |
| Complete geometry samples | 1,673 | 1,707 |
| Failed actor-pair samples | 1,590 | 1,624 |
| Failed conditions protected by window and tangent guards | 1,313 | 1,347 |
| Failed conditions with a potentially editable actor | 277 | 277 |
| Proper crossing records | 30,476 | 31,220 |
| Boundary or near-contact records | 26 | 26 |
| Coplanar or near-parallel records | 0 | 0 |
| Actor/object checks passing | 3,346 of 3,346 | 3,414 of 3,414 |

The two clocks remain separate; imported samples are not silently truncated to the native clock. The full saved native and imported reports are classified, but their full collision populations are not recomputed in this diagnosis.

## Source preservation and exact witnesses

Both actors retain byte-identical world matrices and placed skin vertices at all 1,313 protected native samples. Original clip libraries and binary payload prefixes survive, and source/candidate face indices agree. Scene placements, object motion, contact targets and geometry limits remain unchanged.

All actor faces, actor/object pairs and actor pairs are independently recomputed at `0`, `0.34375`, and the exact clip endpoint `1.2000000476837158` seconds. Source and candidate show the same intersections at these times. The native maximum vertex depth is `0.0051911611834522566 m` at `0.34375 s`, above the original `0.005 m` limit. The existing imported report peaks at approximately `0.005191321 m` at the same time.

`exact_triangle_crossing_witness.py` converts represented finite binary-float coordinates into rational numbers. For every saved proper-crossing record at the two explicitly requested times, it constructs a point strictly inside both triangles on nonparallel planes: six pairs at zero and twenty at `0.34375 s`. All 26 pairs are confirmed independently on source and candidate, giving 52 exact certificates. A separate receipt consumer checks positive barycentric weights, their sum of one, exact convex-combination equality to the same point, nonparallel planes, and binding to the saved skin triangles.

This proves those selected crossings for the represented triangles. Skinning and animation arithmetic have already rounded the coordinates. It does not certify continuous time, penetration depth, self-collision, every reported crossing, or clearance in boundary/coplanar cases. Exact construction matters because intermediate geometric constructions can themselves introduce rounding error; see the [CGAL robustness FAQ](https://www.cgal.org/FAQ.html). Python's [Fraction documentation](https://docs.python.org/3.10/library/fractions.html) describes exact conversion of represented floats. No CGAL dependency or upstream implementation was added.

## Reproduction and evidence

With the saved correction and engine report available locally, choose a fresh output directory:

```powershell
python scripts/native_geometry_source_blockers.py `
  reports/native-transition-contact-fit-jobs/reserved-bridge-v1/proposal `
  reports/geometry-source-blocker-audit-new `
  --witness-time 0 --witness-time 0.34375 `
  --imported-geometry reports/studio-transition-contact-engine-v1/engine/geometry.json
```

The command binds completed correction files, original input snapshots and current/archived numerical methods. It preserves full frozen observations, separate diagnostic profiles, representative geometry queries, rational witnesses, implementation archives and hashes. It uses the existing worker lock and one CPU numerical thread. It does not replay the optimizer or its external parent graph. Saved study inputs are local generated artifacts and are excluded from the public source snapshot.

The command exited zero. All 83 focused tests pass with zero skips, covering exact analytic crossing cases, unresolved outcomes, certificate tampering, malformed input, tangent guards, diagnostic scope, and existing geometry behavior. CI adds only the two new suites. An independent receipt consumer exited zero and confirmed observation populations, all 52 certificates and unchanged source/method bytes. No new engine, model sampling/training, browser, rendering/GPU, physics, production anatomical query or human review occurred.

| Local receipt | SHA256 |
| --- | --- |
| `reports/geometry-source-blocker-audit-v1/result.json` | `6fbe465f57159f1b3ec04f04310e8899bc6a6015e94241c144d120767d1f5a32` |
| `reports/geometry-source-blocker-independent-v1/result.json` | `e774a1a35ec526a4b0b1a6c9fb047b2b8df580eadd4a59e21fdb81975c96bd4b` |

The original negative geometry reports remain immutable. A broader edit scope can permit source motion or scene layout changes, but feasibility must then be measured against the original acceptance and preserved contact intent. This diagnosis does not establish infeasibility under every possible authoring choice. Production action, rig, object and partner validation and developer/animator cleanup remain open. All fourteen release evidence arrays remain empty, and the full-project goal remains active.
