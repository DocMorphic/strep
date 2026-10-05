# Reserved neutral partner layouts

`benchmarks/release-partner-reservations-v1.json` binds the existing three-rig
catalog and all three directed pairings to explicit initial layouts. It uses
neutral geometry only; no reserved action, generated motion or correction
outcome selected these coordinates.

| Pairing | A → B | Rig-origin separation along Z | Initial surface-bound clearance along Z |
|---|---|---:|---:|
| pair-held-01 | rig-held-01 → rig-held-02 | 0.9 m | 0.6285037409535075 m |
| pair-held-02 | rig-held-02 → rig-held-03 | 1.1 m | 0.8214923694096008 m |
| pair-held-03 | rig-held-03 → rig-held-01 | 1.3 m | 1.0265562095825507 m |

The coordinate convention is Y up. A has identity rotation and negative Z
translation; B has a 180-degree Y rotation and positive Z translation. Their
local +Z axes oppose each other. This convention is explicit, but anatomical
facing has not been reviewed. Separation refers to asset origins, not necessarily
the Hips joint or body center. Each actor's Y translation grounds the minimum
of its complete decoded neutral vertex population on the plane Y=0.

`scripts/reserved_partner_fixtures.py` constructs portable packages. Each contains
unchanged character and profile bytes, license/provenance/packing attachments,
the two rigid placements, full neutral vertex observations and all nineteen
mapped joint origins. Joint origins are reference frames, not material skin
contact points. Every copied file is checked against the original construction
binding; rebinding a scene's local license hash cannot replace that provenance.

All **52,342** neutral vertex observations and **114** mapped role origins across
the six actors are retained. Complete initial bounds are separated by more than
the predetermined 0.5 m minimum. This conservative static separation concerns
the decoded neutral surfaces. It does not certify animated collision clearance,
physical support, contact reachability or an interaction.

The verifier reloads bundled assets and reconstructs every source vertex and
role position. Matrix arithmetic checks the producer's componentwise placement
arithmetic. The rig decoder and its skin-weight normalization are shared; this
is not a second independent glTF/skin implementation. Normal-pose construction
evidence from the earlier rig study remains separate from these new placements.

Thirty source-only checks pass locally and in a fresh source copy without models,
vendor files or downloaded character payloads. Synthetic tests cover relocated
packages after original inputs move, mutation/rebound-license rejection, complete
pair order/direction, complete arrays, grounding, initial overlap rejection,
scope fields and preservation of existing outputs. Actual construction is then
verified in a copied portable package. Repeat construction reproduces all scene,
asset, attachment and saved reduction bytes and all 24 numeric arrays exactly.
NPZ transport bytes need not repeat because ZIP metadata can differ.

Local evidence: `reports/release-partner-reservations-v2` and
`reports/reserved-partner-check-v1`. The initial complete v1 package and its
implementation remain preserved; v2 adds stricter original-attachment and scope
validation. No animation or engine import ran for these new pair layouts.

```powershell
python scripts/reserved_partner_fixtures.py build benchmarks/release-partner-reservations-v1.json benchmarks/release-rig-reservations-v1.json reports/my-fresh-partner-bundle
python scripts/reserved_partner_fixtures.py verify reports/my-fresh-partner-bundle
```

The generator requires the separately acquired reserved rig payloads and their
existing construction proof. The public repository contains recipes and source,
not those character payloads. Verification uses the package's own assets and
matching archived source; original machine-specific asset paths are not needed.

These fixtures still span one known topology/skinning family and two source
meshes. They do not establish independent artist-rig generalization. Keep them
outside motion tuning, or record exposure and retire/version the reservations.
Anatomical facing, explicit material hand patches, task-specific targets/timing,
motion/engine trials, method/baseline freeze and genuine human review remain
required. The full release fixture set and acceptance matrix remain incomplete;
`held_out_fixtures` is still unset and no release evidence is granted.
