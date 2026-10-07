# Stricter solver accuracy with original acceptance

Source validated at 2026-10-07T00:40:54.105185+00:00.

The [first preferred-depth comparison](preferred-depth-restoration-v1.md) rejected its initial solver point because the reported native residual exceeded the original phase tolerance. `scripts/native_partner_accurate_depth_restore.py` is a separately versioned variant requesting 1e-11 feasibility, absolute-gap and relative-gap solver accuracy. Historical methods and studies remain unchanged.

Original phase native checks and priority locks remain **1e-9**. Native norms stay hard, all original surface rows remain represented, and control/trust boxes, preferred zero-depth target, external 5 mm limit, contacts, source rates, static references and decoded export/geometry checks retain their meaning. Solver status alone cannot approve a point. Finite normalized phase solutions and projected control steps are saved even when subsequent native/priority validation rejects them, enabling independent recomputation of the failure. Later rejected phases retain the last verified candidate.

**61 source tests pass**, zero skips: the unchanged 29 preferred-target tests and 32 accuracy-variant tests. Actual small conic tests cover preferred-depth behavior, original-limit guidance, hard norms, complete surfaces, control projection and later-phase fallback. Injected `Solved` points with normalized excess 1.3244607357135744e-9 and 1.01e-9 are rejected under the unchanged 1e-9 check. Saved phase steps are separately evaluated against original vectors and caps in the tests. The suite is registered in Linux/Windows source checks; hosted success remains unverified.

A new explicitly typed matched driver reuses the complete independently replayed original model at the exact same 44-choice anchor with no new derivatives or changed fraction/resource budgets. Every actual export and complete geometry gate must be saved and independently checked; phase points must be independently evaluated, including failures. The new study has completed without a valid direction; see below. Stricter requested tolerances do not guarantee convergence, feasibility or better motion, and the real study may still fail. These source tests do not establish production anatomy, semantic realism, engine or human cleanup quality. All fourteen release evidence arrays remain empty.

## Completed accuracy comparison - 2026-10-07T00:52:40.519895+00:00

Requesting 1e-11 solver feasibility/gap accuracy does not resolve this case. The initial phase reports `Solved`, but an independent consumer recalculates **2.5096603652723088e-9** normalized native excess from the saved finite point and all original vector rows, above the unchanged 1e-9 check. It reproduces the native-only rejection and the absence of a selected direction. Later phases are not run; no clip is exported. Complete original cache/model arrays and source/replay lineage remain exactly bound. This is a numerical point rejection, not a feasibility or impossibility certificate.

A separate finite-ray diagnostic finds that a tiny retreat toward the original strictly passing anchor restores original affine caps. The next [bounded ray recovery](ray-depth-restoration-v1.md) retains the failed solver point and checks that alternate candidate without changing any cap or claiming solver optimality.

Ignored immutable receipts: producer `50c6417298739edabc06e7ee415d6e89b35cfd5684be6a1f18330f2ce453c817`; complete cache/no-export replay `398e16c0aadf4db4303cdaf0978d9f7286207006e8da9a2ee8b0b95bfbbc1a6b`; independent all-phase evaluation `c57da92ef3e4ca1a16a20a05e99c0e48a3811ff0195c65e775307182bf7b1197`.
