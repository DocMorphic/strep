# Clearance comparison and internal continuation

The 64-pair hand-clearance comparison reuses the independently replayed **90-control, 30,450-native-norm** model at the same 45-choice anchor. Both variants retain the original 1,707 native samples, 1,673 geometry times, reference budgets, source-rate caps, contacts, control/trust box and geometry policy. The 100-micrometre projected clearance at 0.34375 seconds is proposal guidance, not a new acceptance limit. No world derivatives are rerun.

| Guidance | Export fraction | Native failures | Contact failures | Tested-frame depth in mm |
| --- | ---: | ---: | ---: | ---: |
| Original norms | 1 | 6 | 1 | 5.040485 |
| Original norms | 0.5 | 5 | 0 | 4.924409 |
| Original norms | 0.25 | 2 | 0 | 4.864108 |
| Original norms | 0.125 | 2 | 0 | 4.833385 |
| Event key preserved | 1 | 10 | 0 | 5.007045 |
| Event key preserved | 0.5 | 1 | 0 | 4.905110 |
| Event key preserved | 0.25 | 0 | 0 | 4.853807 |
| Event key preserved | 0.125 | 3 | 0 | 4.828072 |

Both solver statuses are `AlmostSolved`; strict original-cap ray checks select fractions 0.9999980926513672 and 0.9999990463256836 of the raw proposals. Every export improves the one-sided projected deficit, and every reference/trust bound passes. All measured tested-frame depths worsen from the 4.802282354-mm anchor. The sole motion-feasible export is the event-key quarter step: its guide loss falls from **2.753322312 to 2.459991545**, but the minimum projected gap remains **-12.661717 mm**. The full geometry scan finds **4.865280708 mm** maximum vertex depth, **30,368 triangle records and 1,605 failed conditions**. It fails the unchanged geometry gates and depth-first ranking.

The complete independent consumer binds the original norm/Jacobian/event cache, rebuilds all 64 scalar guides and all 90 guide columns from every verified cached point stencil, reconstructs each strict ray prefix and replays every actual payload, native world, source/contact/reference result and peak query. The selected full geometry archive is checked for transport fidelity using shared geometric predicates. The raw normalized solver controls were not saved; the separate slack diagnostic is checked at represented raw steps with an explicit 1e-12 diagnostic tolerance. Both diagnostic differences are zero, while original native ray acceptance remains strictly zero-or-negative. Solver optimality and independent collision-predicate implementation remain unproved.

A separate relaxed pose experiment samples 17 points along one declared interpolation toward the previously separated pose. Vertex depth initially rises from **4.802282354 to 4.988584552 mm**, then reaches zero with no partner triangle records at the last two samples. All sampled five-degree/30-mm pose budgets pass. Independent matrix reconstruction agrees within **7.772e-16**, saved skin vertices reproduce exactly, all 64 projected gaps are checked with exact rational arithmetic and every partner/object query matches. This is one relaxed path at one frame: it does not establish feasible native curves, source rates, contact timing, continuous motion or the shape of all possible escape paths.

`scripts/native_unapproved_anchor.py` assembles a motion-feasible internal draft into a genuine next Job. It freshly verifies the complete decoded original native/rate/contact constraints, every original vector norm, strict reference budgets, represented control/trust box, static payloads, frozen keys and explicit one-neighbor storage choices. It copies the candidate, reopens the new Job and checks identical controls, worlds, residuals and reference results. Every non-anchor request field and absolute storage choice stays unchanged.

Geometry is not an eligibility condition for this **internal** seed. The next Job retains its original geometry policy, and the assembly never appends or selects a library clip, inherits transition approval or marks geometry, quality or release approved. This permits exploration beyond a locally worsening depth diagnostic while keeping final animation acceptance intact. The actual event-key quarter step is assembled and independently replayed this way, with all 30,450 native norms passing; its known collision failure remains explicit. The next curve solve requires fresh derivatives at this new point.

The CLI accepts `--job`, `--controls`, optional `--array`, one `--actor NAME=GLB` per edited actor and `--out` for a fresh directory. The original Job's external non-anchor role paths must already be absolute. Frozen actors retain their original source files. Existing pinned assets and runtime dependencies are required; the public repository does not bundle these generated study outputs.

**87 focused local tests pass, zero skips**: 12 new actual assembly/rejection cases and 75 existing guide/ray/key-support cases. Both Job formats preserve their original contracts and outputs remain unapproved. A real authored rotation that exceeds original source rates is rejected. The first run has 85 passes and two fixture failures: an unhandled v2 fixture tuple and a purported rate violation that was actually permitted. The corrected fixture uses a demonstrated static-rotation rate violation and retains the failed report. The new suite is registered in Linux/Windows source CI; hosted success is unverified.

All results concern generated fixtures. They do not establish production-rig behavior, broad action semantics, physics, engine playback or animator cleanup quality. Originals stay selected, all fourteen release arrays remain empty and the full-project goal stays active.

Ignored immutable result SHA256 values:

- clearance study: `94a37ec72573e1d0f8e50a0820e243c4c6441fe9f4ee7e1bb6e26aaaaaabcd16`
- clearance replay: `bc203d26c3fdefbdd54a8735e605eb67cfd6276fe3c102694219f91c2c3f6d87`
- relaxed path replay: `16472e6723ac4fe63bc165473bfa46d29b642836f0533b916e77f88038ddb20a`
- internal-anchor replay: `f38cc461b7a8a708c29a96b06fd8e10913714d0d565b24327e6baefc77c5f02c`
