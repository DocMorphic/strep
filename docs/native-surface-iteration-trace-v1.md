# Interrupted surface-fit evidence

Surface fits now atomically save each completed primary iteration under
`optimization-iterations/01.json`, `02.json`, and so on. Every receipt binds
the immutable fit request hash and carries the same detailed iteration record
as the eventual optimizer result: geometry scores, rejected/retained probes,
proposal model and conic solver information. Measured restoration attempts
also record their margins and solver availability, including attempts returning
no step. A completed fit lists every receipt path and hash in
`surface_iteration_receipts`.

Interrupted fits retain their completed prefix. They do not receive a completed
fit result. An interrupted iteration has no completed receipt; individual
exports and probe/geometry records still remain separate. The terminal guard
record determines whether a worker is live, complete or stopped. Receipts do
not certify replay, collision, continuous-time behavior or animation quality.
Local solver retention does not select the asset: the original remains selected.

The callback receives a deep copy so changing a callback argument cannot rewrite
optimizer history. Changed requests, nonsequential iteration numbers and existing
receipts reject; recording errors propagate rather than silently losing evidence.
The writer uses the existing atomic JSON replacement behavior. Acceptance rules,
motion limits, sampling populations and numerical proposal decisions are unchanged.

All **224 affected tests pass**, including 13 new tests for request/hash binding,
mutation isolation, invalid sequence/overwrite rejection, simulated interruption,
unavailable restoration steps, error propagation and an actual serialized fit.
The completed check's 143 sampled resource observations and archived bindings
replay. Local evidence: `reports/surface-iteration-trace-source-checks-v1` and
the guard/resource records under `reports/central-hand-physical-v1`.

This change follows the [crawl restoration failure](kenney-crawl-plane-envelope-v2.md).
That older trial predates iteration receipts, so its missing solver details are
not reconstructed or invented. New actual trials still need their own motion,
resource, independent replay and human evidence. No release gate is approved.
