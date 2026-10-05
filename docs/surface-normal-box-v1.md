# Necessary surface-normal displacement bounds

`scripts/surface_normal_box.py` adds a geometric diagnostic for explicit hand
surface contacts. It measures whether a fixed target direction is excluded by
specified coordinate displacement boxes around a saved mesh. It does not solve
a pose or derive vertex boxes from rig controls.

The existing point-contact and sampled-geometry checks can pass while authored
surface orientation fails. A failed local conic proposal does not establish
that the full permitted rig cannot satisfy that orientation. This diagnostic
keeps those claims separate and provides a necessary displacement test.

## Bound and assumptions

For each contact vertex group, retain every incident triangle once, with its
original winding. The unnormalized area-weighted normal is the sum of triangle
cross products. Every supplied vertex coordinate may change independently
within its declared radius. Radii can be uniform, per vertex, or per coordinate.
They must cover the entire mesh; only incident vertices contribute to the bound.

For triangle edges `u`, `v` and perturbations `du`, `dv`, the cross-sum change is
`cross(u,dv) + cross(du,v) + cross(du,dv)`. Componentwise absolute bounds enclose
all three terms. Sum every face enclosure and any explicit arithmetic reserve.
All decision arithmetic uses exact rational representations of binary floating
inputs. Integers outside the exact binary64 range and wider floating types are
rejected before conversion.

Let `m` be the cross sum, `d` the negative fixed target direction, and `q` the
minimum alignment cosine. A usable normal must satisfy
`dot(d,m) >= q * norm(d) * norm(m)`. The enclosure provides an upper bound `U`
on that dot product and a lower bound `L` on the squared cross-sum norm.
The whole box is excluded if `U < 0`, or if
`max(0,U)^2 < q^2 * dot(d,d) * L`. Equality does not exclude a box.
Certificates retain exact rational intervals, decision margins, complete
incident-face indices and input hashes.

Shared-vertex correlations are discarded, so the enclosure can be loose.
An inconclusive result is never a reachable-pose certificate. Zero, degenerate,
incoherent or inward-facing mesh normals receive no availability or anatomical
approval. This test does not constrain point positions, contact side, force,
penetration, timing or partner movement.

The default zero arithmetic reserve concerns exact real geometry of the supplied
vertices. A claim about a floating implementation requires a separately justified
reserve enclosing that implementation's cross-sum errors. The helper supplies
no such runtime error certificate. It also supplies no mapping from normalized
control trust radii or joint-origin displacement caps to vertex boxes.

## Saved development slice

Local evidence: `reports/surface-normal-box-check-v3`. Forty-eight checks covering
the new helper and existing point-reachability helper pass in a fresh source-only
copy. They include exact decision boundaries, complete incident populations,
caller-input immutability, arithmetic reserves, invalid inputs, degenerate sums
and exact containment of randomized perturbed triangles. These are synthetic
mathematical checks, not animator ratings or new motion trials.

The saved-data reduction chose the exact midpoint of the common authored hold
interval before inspecting orientation results: **3.0166666507720947 seconds**,
frame **1281** of the previously verified 2552-frame geometry archive. All ten
authored normal groups were retained. Their target directions use the saved
object rotation. Full selected arrays match their logical transport hashes;
the complete archive was not rehashed or re-queried in this reduction.

Eleven explicit uniform vertex radii were tested, from zero through 0.22 m,
yielding 110 cells. The diagnostic uses alignment cosine **0.96**, a relaxation
of the authored 15-degree angle condition: `cos(15°)^2 = (2+sqrt(3))/4`,
`sqrt(3) > 1.7`, and `0.96^2 < 3.7/4`. The authored policy is unchanged.

Two groups, point 2 of each hand's neighbour contact, are excluded at zero,
1 micrometre and **10 micrometres** per coordinate. At **0.1 mm** and larger
tested radii, these conservative bounds are inconclusive. Therefore, within this
single exact geometric slice, satisfying even the relaxed direction requires
more than 10 micrometres of change in at least one incident vertex coordinate.
The result is a small necessary lower bound, not a sufficient motion budget.

Those displacement boxes are hypothetical; they are not the real permission
set. The actual authoring permission includes twelve rotation tracks, each
allowing up to 45 degrees per rotation-vector component, and a 0.22 m
joint-origin displacement cap. That cap is not a vertex displacement cap.
No globally unreachable rig pose or full-clock exclusion was demonstrated.

The initial saved-data reader incorrectly assumed the object's rotation was
identity and stopped at an assertion. Its source and completed tests remain in
`reports/surface-normal-box-check-v1`. A fresh reader uses the saved rotation;
v2 and v3 reproduce the same complete 110-cell reduction. This was a reader
assumption failure, not a production geometry or engine failure.

The retained development motion still has **2066** surface-orientation failures
over its full contact clock. Existing engine/repair/replay jobs remain serial;
their frozen methods and raw results were not edited. No motion improvement,
physics, human review, training admission or release approval follows from this
diagnostic. The next repair must still be judged by complete closed-contact,
rate, geometry and engine results, rather than by this relaxed necessary test.
