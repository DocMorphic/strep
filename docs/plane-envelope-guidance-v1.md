# Complete plane envelopes for bounded correction

The surface solver now accepts `plane_guidance="minimum-envelope"` when using
`proposal_model="surface-vector"`. The default remains `all-vertices`.
The CLI option is `--plane-guidance minimum-envelope`. Guidance mode is recorded
in the fit request and result; a resumed job inherits its previous mode unless
an explicit mode is supplied. Original edit/motion limits and decoded acceptance
checks remain unchanged.

For an actor, a world plane and a declared sample time, the full plane condition
is equivalent in real arithmetic to a lower bound on the minimum signed distance
over **all** loaded vertices. Minimum-envelope guidance stores one scalar row
per actor/plane/time. Its stored vertex is a witness; each evaluation recomputes
the minimum over every vertex, including when the minimum changes. Clear times
also retain a row so a later proposal's new crossing remains visible.

The mode does not select a smaller mesh, remove sample times or omit already
clear plane conditions. Every iteration rebuilds the guide from decoded motion.
Every proposed step is exported, decoded and checked against the complete
geometry population and original native conditions. Nonsmooth minimum-distance
finite differences are a local proposal model, not a collision certificate or
an animator-quality decision. The original remains selected.

Plane guides now include unreferenced vertices. The existing decoded geometry
audit tests triangle-referenced vertices against planes, so the guide is more
conservative for meshes with unused points. All 1,029 vertices in the crawl
asset are triangle-referenced; the two populations coincide for this trial.
Object and partner guides retain their
existing complete queries; they are not collapsed by this mode. Geometry row
limits still reject overflow without returning a truncated population.

The model builds surface guidance before allocating the original vector
linearization, so row overflow can stop early. Surface Jacobian columns retain
every row and every exact nonzero in sparse storage, avoiding the previous
dense stacked copy. No derivative magnitude cutoff or altered tolerance is used.

The change passes **211 affected tests**, including 16 new envelope tests.
Tests cover arbitrary unit plane normals, equivalence with the full geometry
minimum, changing/previously clear minima, unreferenced vertices, full clock/vertex
coverage under a row limit, actual fit serialization and inherited resume mode,
legacy scene bounds and partner/object regressions. The first test version caught
a local name collision in partner queries; the failed method/test/resource record
is archived. The corrected version passes all suites and recorded resource replay.

Local evidence is in `reports/plane-envelope-source-checks-v2` and its guarded
job/resource records under `reports/central-hand-physical-v1`. This enables a new
[crawl correction attempt](kenney-ground-scenes-v2.md), whose previous explicit
per-vertex guide required 216,306 rows at 2,017 times. Actual motion improvement,
resource use, contact intent, physical balance, engine playback and human/cleanup
quality require their own evidence; no release approval follows from source tests.
