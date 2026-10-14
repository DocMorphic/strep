# Contact reserve for native-key pose initialization

The actual crawl export in [affine contact initialization](native-affine-contact-initializer-v1.md) misses its 5-mm authored touch limit by 4.582 nanometers after quaternion serialization. Its isolated continuous pose passes, so accepting only solver feasibility would misreport the exported asset. The native-key initializer now supports an explicit solver reserve while retaining the original decoded acceptance limit.

This extends the pose initializer. The existing `native_contact_reserve.guided_problem` adapter for norm-based scene optimization remains unchanged; its existing tests are preserved.

## Request and validation

Add this optional field to the source-bound `strep-native-key-contact-initializer-v1` request:

```json
{"contact_reserve_m": 0.0005}
```

The default is zero, preserving previous behavior. A supplied value must be a finite nonnegative number; Boolean values, strings and nonfinite values reject. A positive reserve requires at least one contact affected by the selected actor and must be strictly smaller than every affected authored position tolerance, including incoming partner targets. Zero remains allowed for exact-zero tolerances or scenes with no affected contacts. This is one scalar margin applied to all affected pose-position targets; no per-target selector or Studio control is introduced here.

For a target tolerance `L` and reserve `r`, the solver requires the point error to lie inside radius `L-r`, with the original `L²` row normalization. Individual and centroid points, world/object targets and incoming/outgoing partner contacts keep their original coordinates and reductions. Rotation/displacement bounds, the floor reserve, root constraints, original animation clocks and source-rate caps remain unchanged. The reserve does not constrain hold velocity, surface normals, balance or continuous collision; those need their own complete checks.

The result records the explicitly supplied reserve. The fresh bound auditor verifies it against the original request and reconstructs every pose with the same margin. The original scene intent remains unchanged: complete decoded contact evaluation still uses `L`, never `L+r`. A solver margin is a numerical allowance, not a guarantee for every possible transform or rig. An exported clip outside its authored tolerance still fails.

## Validation

The targeted batch passes **50 checks in 119.52 seconds**, covering the new reserve behavior and existing native-key/affine initialization. New cases reject invalid/oversized reserves, check incoming partner intent, verify the complete finite-difference Jacobian, solve an actual surface target and export quaternion keys, and replay the full public producer with the explicit reserve. A changed result reserve is rejected even when its result digest is supplied afresh. Existing zero-reserve/default and boundary/checkpoint cases remain passing. The guard completes in 135.953 seconds, peak sampled process-tree RSS 126,599,168 bytes, and all 135 resource observations replay.

During preparation, the new tests initially used a filename already occupied by the existing norm-reserve suite. After the numerical worker finished, the existing file was restored byte-for-byte and the new tests were moved without content changes to `tests/test_native_key_contact_reserve.py`; the exact validated test bytes are archived locally. All **20 existing norm-reserve checks pass in 0.61 seconds** separately; their guard completes in 17.250 seconds with all 19 observations replayed. Both source inventories validate without duplicate paths: 507 Python/45 Node files, and 71 Python/5 Node files in the focused contact/rig suite. Inventory validation is not execution of every listed file.

The fixed CPU profile retains the 512 MiB runtime cap plus 600 MiB free-RAM floor and 15-second admission stability. Model/full-body jobs keep their separate resource policy. Local generated evidence remains under ignored `reports/native-contact-reserve-validation-v1`, `reports/native-contact-reserve-validation-v2` and `reports/crawl-native-contact-reserve-v1`.

## Actual crawl integration

The development experiment declares a 0.5-mm reserve inside the unchanged 5-mm ground-touch tolerance. It retries only native key 12 from the original source with the prior 40-iteration budget, replaces that key in the rejected seven-key integration, and preserves all other 476 key controls. The original full source clock and four rate cap arrays remain bound to the unchanged transfer; no previously corrected clip becomes a source-rate reference.

The isolated reserved pose converges in 21 iterations. The actual quaternion export passes contact at **4.499998800 mm**, inside the unchanged 5-mm authored tolerance. Its maximum joint displacement is 189.131 mm and its maximum rotation uses 63.380% of the existing 30-degree permission, both within the unchanged bounds. Root matrices remain exact, the final world pose remains exact, all other 476 controls remain exact, and all four original rate cap arrays match.

| Complete decoded observation | Previous integration | With explicit reserve |
| --- | ---: | ---: |
| Ground-touch error | 5.000004582 mm, fail | 4.499998800 mm, pass |
| Failed floor times / population | 8 / 2,829 | 8 / 2,829 |
| Peak floor depth | 5.446870 mm | 5.399995 mm |
| Original rate failures / population | 377 / 123,630 | 377 / 123,630 |

The clip remains **rejected**. The 377 motion-rate failures retain counts 89 positional speed, 85 positional acceleration, 120 angular speed and 83 angular acceleration. The remaining floor failures occur between native keys. A passing authored surface touch is not planted support, naturalness, balance, partner coordination or a usable complete clip. Equal failure counts do not prove per-row nonregression, and the failed proposal is not selected.

The study completes in 85.672 seconds, peak sampled process-tree RSS 230,440,960 bytes; all 86 resource observations replay with their archived bindings. The output GLB SHA-256 is `2348d7f3dbe3702eb3ade979f49acea248aa32366e291f519390ce198ba44999`. This is a complete shared-method development check, not a fresh independent replay or human-quality result. There is no inference, training, held-out evaluation, engine execution or new human review. Next work must couple neighboring keys while preserving original constraints, then continue broader scene/partner/style/rig/engine and release evaluation. All fourteen capability/calibration gates remain unapproved and the entire-project goal remains active.
