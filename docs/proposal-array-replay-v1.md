# Proposal replay without expanding numeric arrays

Native replay previously loaded each numeric proposal array as Python lists and then converted it back to NumPy for computation. Large Jacobians and margin records therefore incurred boxed numeric objects in addition to their numerical storage. `load_record(..., array_values=True)` now returns independently allocated, read-only arrays for archived homogeneous numeric lists. Interval and window replay use this mode; the default API still returns JSON-compatible lists, and legacy inline reports remain untouched.

Both modes verify all three metadata/archive/receipt bindings before and after loading, the complete transport receipt, kind/iteration/correction identity, unique array references and complete array population. Proposal arrays must represent finite numeric lists, as produced by the writer; scalar, complex and non-finite array payloads are rejected even if a caller reseals their transport receipts. There is no sampling, downcasting, truncation, numerical tolerance change or weakened retention gate. A strict boolean option is required before either archive access or legacy return.

Array mode preserves stored dtype, shape and logical bytes. Read-only flags discourage accidental mutation; they are not a security boundary. A caller can deliberately change its detached allocation, but cannot modify the saved archive or another load through it. Empty, mixed-type and ragged lists retain their original tree structure, with numeric sublists represented as arrays where the archive stored them.

## Validation

All **55** focused NoTorch proposal tests pass. They exercise exact nested values/types, signed zero and adjacent/subnormal float bits, integer bounds, detached reloads, streamed solver records and decisions, invalid modes, altered metadata/archive/receipt, duplicate/missing/extra array references, resealed non-JSON numeric payloads and mutations during verified loading.

A fresh source-only fixture passes **435 checks across 14 modules**, including those 55 checks and native contact/window replay, history reuse and repair. It contains copied Python source/tests without vendor assets or input motion archives. Torch is used for CPU fixture math; this broader suite is not described as NoTorch. The guard exits zero in 99.563 seconds, with 665,067,520 bytes sampled peak process-tree RSS. Independent resource replay verifies all 97 observations, admission, binding and exit accounting. The initial attempt started before snapshot preparation had finished and failed for a missing source-bindings file; that setup failure remains recorded. The successful fresh attempt begins after snapshot completion. Earlier history-reuse suite interruptions also remain unchanged.

## Native archive transport probe

Separate fresh NoTorch processes load the same **11** complete V7 proposal records: three starts, four linearizations and four corrections. They contain **653 arrays / 127,715,163 logical bytes**, with **33** bound metadata/archive/receipt files. Full tree structure and numeric dtype/shape/byte digests match across modes; every input/source/artifact binding is rechecked. No solver is rerun or motion changed.

| Mode | Sampled peak process-tree RSS | Total record-load time |
| --- | --- | --- |
| Python lists | 214,122,496 bytes (204.2 MiB) | 1.904 s |
| Read-only arrays | 79,937,536 bytes (76.2 MiB) | 1.357 s |

This single sequential probe observes a **62.7%** reduction in sampled peak memory. Each hydrated record is held for 1.1 seconds to expose it to the unchanged one-second RSS sampler. Both guards exit zero; independent resource replay verifies 30 and 26 observations respectively. Finite sampling, allocator behavior and changing host load limit this comparison. Load times exclude digest comparison and record holds. It is a transport measurement, not a native solver speed result or a reason to reduce full-fit/audit estimates.

Source snapshot SHA-256: `832578ed90df5027e51002b537494540064ff98655dadcd609573fd81331aec4`. Native stage result SHA-256: `1bd99e5533f64d4a8b5cf09ed7c02e59c29d70606d858619c9a48cc2a323b113`. Frozen source, test results, both profile workers/guards, full per-record digests and `profile-parity.json` stay under ignored `reports/proposal-array-replay-v1/`. Lists and arrays guard protocol SHA-256 values are `4d05d22047c4a3dff174d8c547f858ac2afe1c7be226b1e3bf630e99fef18f11` and `5970910e6778f7d1de7c2752d0aa8920b8c79907a4a46ee0c8215974663bc51b`.

The separately completed [V7 independent geometry replay](contact-interval-batch-v2.md) now establishes its first stage as the latest verified state. Physical and keyed passes remain 0/62. Further contact windows, between-key behavior, scene/partner support, rig transfer, editing/style, transitions, engine and actual human review remain required. All fourteen release capabilities remain unapproved. Full native fits/audits keep their 2 GiB estimate plus 600 MiB reserve; source tests retain their separate 1 GiB estimate. No original clip/preview replacement, training or quality/release approval results from this transport change.
