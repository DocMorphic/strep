# Individual contact bounds during native repair

The `storage-vector` fitting path now protects every original point and held-speed
condition individually. Each passing condition must remain passing; each failing
condition cannot increase its normalized excess. This includes every declared
contact point and all twelve held-speed clock populations, without an action
whitelist, chosen frame subset or changed authored tolerance.

The original edit, displacement and source-rate prefix remains hard. Contact
norms are duplicated into that prefix with separate no-worsening caps at the
decoded baseline. Their original authored caps remain in the minimax objective
and final audit. No contact or source limit is loosened. A failing source prefix
cannot be recapped to enable contact repair.

The base vector population now comes from the current retained GLB's scalar
decoder. Its caps, scales and order must exactly match the original model.
Derivatives still use their matching continuous proxy origin; a decoder/proxy
offset is not divided by the finite-difference step. Saved export labels identify
the retained base after backoff, storage-cell probes or restoration.

Every trial is exported and decoded. Acceptance additionally checks the complete
individual contact residual population. A contact regression triggers optional
decoded restoration even when the source motion prefix already passes. Only
proposal guard margins are tightened; original contact norms stay unchanged.
Restoration failure leaves bounded backoff/storage probing available. Neither
solver success nor a lower aggregate error can override the decoded guards.

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json reports/new-held-repair --proposal-model storage-vector --iterations 2 --restoration-steps 3 --geometry-policy policy.json
```

This remains an experimental CLI path; Studio's fitting defaults are unchanged.
Plain scalar/vector modes retain their prior behavior. Surface-vector already
has separate oriented-contact protection and complete geometry acceptance.
Object geometry, contact normals, engine behavior and developer review are
additional checks, not conclusions drawn from this point/held-speed guard.

## Paired humanoid sphere study

Both trials keep the exact sphere candidate, permissions and original source
epoch: two right forearm/wrist rotation tracks, five-degree cumulative bounds,
3 cm joint displacement, 1.5–4.5 second edit window, original native keys,
18 control components, two primary iterations and up to three restoration solves.
The geometry policy checks all triangles against two objects at three explicit
clocks; it is not continuous collision evidence.

| Outcome | Original | Source-only guarded trial | Individually guarded trial |
| --- | ---: | ---: | ---: |
| Original native conditions failing | 53 | 53 | 53 |
| Worst right-hand hold speed, mm/s | 10.1976319 | 10.1969850 | 10.1976319 |
| Failed contact rows whose excess regresses | 0 | 27 | 0 |
| Retained primary steps | — | 1 | 0 |

All 53 original failures are right-grip speed conditions. Position conditions and
the original 275,761-row source prefix pass. The older trial retains a 1/16 step
because worst aggregate excess decreases, despite 27 individual regressions.
The new path uses 5,458 separate contact guards; all 281,219 original native
conditions become hard source/guard rows, while authored contact norms remain
in the objective. No candidate is retained. Original and final GLBs are identical.
This paired comparison changes both decoded anchoring and individual guards;
it does not isolate their separate effects or prove infeasibility.

Independent saved replay checks every control, byte-exact GLB export, original
cap array, complete decoded norm population and acceptance decision. It adds a
full sampled geometry audit to every probe: 10 exports/eight decisions for the
older trial and 23 exports/21 decisions for the guarded trial. Both final sampled
geometry checks pass, but held contact fails; originals stay selected. No grip,
animation-quality, training or release approval follows.

Ignored local evidence is under `reports/native-sphere-hold-development-v2` and
`reports/native-sphere-hold-development-v3`. Raw failures remain retained. Ten new
focused regression cases cover aggregate tradeoffs, passing/failing contact
bounds, decoded contact restoration, invalid configurations and decoder anchoring.

All 492 related model-free regression checks pass in the recorded local run.
