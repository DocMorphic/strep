# Experimental collision-query acceleration

A small matched benchmark tests conservative candidate filtering around the existing Trimesh 5.1.0 backend. It does not replace production collision checks or reduce their intended vertex/time population.

The installed source and [Trimesh proximity documentation](https://trimesh.org/trimesh.proximity.html) show that signed distance combines closest-surface queries with sign determination. A local profile of the fixed diagnostic subset attributes 0.986 of 1.131 seconds of signed-distance time to inside/outside ray tests, about 87%. Optimizing only closest-face candidates barely changes total query latency.

Two experimental filters retain the library's narrow-phase calculations:

- A triangle-centroid bounding sphere rejects faces that cannot beat the nearest-vertex distance. The filter retains the library's squared-distance ambiguity band and candidate ordering, with outward numerical padding.
- An infinite-line/triangle-AABB slab test rejects ray candidates that cannot intersect. It deliberately retains possible hits behind the ray origin; Trimesh retains responsibility for forward-hit rules, intersection deduplication, bidirectional parity and fallback directions.

Each query uses a private mesh/tree proxy. No installed package, original mesh, active worker or production import is patched. The ray adapter is explicitly limited to Trimesh 5.1.0 because it relies on its per-ray tree-query ordering, which is checked at runtime.

## Small matched result

The fixed subset contains **128 points at two development times in both actor directions**, mixing eight source collision witnesses with 24 spaced hull candidates per case. Reference and filtered query order alternate by 16-point chunk. All 128 signed distances match exactly, with zero sign or 5 mm classification disagreements.

| Quantity | Original candidates | Retained candidates |
| --- | ---: | ---: |
| Closest-face candidates | 23,220 | 5,646 |
| Ray/face candidates over 150 rays | 559,664 | 609 |

Measured query time is **0.4604 seconds versus 0.2555 seconds**, approximately 1.80 times faster on this small subset. Shared tree/proxy construction took another 0.5214 seconds and is reported separately; this is **not an end-to-end speedup measurement**. Timing is also subject to caching and other local processes.

The broad sample population, edge/tie cases and memory behavior still require validation before adoption. Exact agreement on 128 points does not establish all-frame equivalence. Source geometry is not made watertight or free of self-intersections by this filter, and vertex depths remain distinct from continuous collision detection.

[Open3D's CPU distance API](https://www.open3d.org/docs/latest/python_api/open3d.t.geometry.RaycastingScene.html) was also considered. It uses float32 query coordinates and has its own signed-distance assumptions. Given the current micrometre comparison tolerances, changing both numerical representation and backend would require a separate validation study. No new geometry dependency was installed.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts/benchmark_proximity_filter.py reports/scene-pair-refinement-geometry-v1 reports/<new-query-benchmark> --filter-rays
```

Local records `proximity-candidate-filter-v1` and `-v2` retain the closest-face-only experiment and profiler; `-v3` includes both filters. Ten tests pass locally. Six pure bound tests join model-free CI; four real Trimesh/Rtree comparisons skip when those optional dependencies are absent. Production geometry continues to use the original implementation.
