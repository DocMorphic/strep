# Original-axis self-surface proposal bounds

The supported high-five v4 clears localized hand and partner checks but
introduces ten B shoulder crossing pairs. The fixed midpoint introduces
eleven pairs and fails contact. These measured failures are retained in
[native-hand-reference-v1.md](native-hand-reference-v1.md). Minimizing wrist
rotation alone is insufficient; the solver needs self-surface guidance.

`scripts/native_self_separation_cuts.py` accepts a complete original vertex
population, original triangle topology and explicit unordered triangle pairs.
For each pair it uses the existing `separation_axis` function on the original
triangles, then retains all nine vertex-pair inequalities on that fixed axis.
Both sides use the same actor's actual posed vertices and derivatives.
Shared vertices, zero rows and shared-edge pairs remain included.

The lower bound is `min(clearance, original axis gap)`. An original overlap
keeps its negative gap and is explicitly reported as unresolved. It never
becomes positive clearance or a valid source solid. Neither warm starts nor
subsequent proposals recenter the reference. Candidate vertices and their
complete Jacobian are evaluated against the stored axes and lower bounds.

Bounds are 250,000 vertices, 100,000 triangles, 4,096 distinct pairs and an
explicit maximum of 100,000 rows. Every pair requires nine rows; exhaustion
rejects the complete request rather than returning a subset. Derivative
evaluation allows 1–192 controls, with an explicit 128-MiB input-Jacobian and
estimated temporary-workspace budget. These estimates do not replace the
process memory guard or guarantee third-party peak allocations.

Twenty-eight local tests cover complete pair rows, both moving sides,
directional differences, translation cancellation, rigid reference
transforms, source overlaps, shared vertices, input mutation, malformed
identities and exhausted row/Jacobian budgets. The guarded test run takes
18.281 s at 89,415,680 sampled bytes; all 20 resource observations replay.
The source inventories now contain 552 Python/45 Node suites, with 116/five
in the contact subset. These are inventory counts, not complete-inventory
passes.

This helper only guides a solve for its explicit pairs. It does not discover
new intersections, prove nonlinear feasibility, certify a mesh/solid, or
approve an animation. Complete actual-surface checks must follow every
candidate, including newly introduced pairs and unedited source defects.
No physical acceptance threshold or original animation is changed.
