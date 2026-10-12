# Automatic export repair in the native surface fitter

The public `native_scene_fit.py` workflow now accepts an explicitly bound
corrected-key start and repairs otherwise feasible exports automatically. It
keeps the original rig, source-rate cap epoch and authoring bounds. The existing
fit behavior remains the default; this path requires explicit boundary
permissions and the one-neighbor storage policy.

## Inputs and use

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json output `
  --proposal-model surface-vector --geometry-policy geometry.json `
  --boundary-edit boundary.json --storage-repair-policy repair-policy.json `
  --storage-continuation corrected-start.json `
  --storage-repair-stages 8 --storage-repair-probes 16
```

The boundary file embeds the exact supplied permissions, with explicit start/end
policies. The repair policy binds that authoring request, permits at most one
absolute Float32 neighbor per component and limits the corrected population.
The optional start binds its original sources, controls, policy and exact actor
assets. A fresh fit can omit the start and use no seed corrections. Keep the
original `contacts.json`; using a corrected GLB as its new source would change
the motion limits. Select the same rotation-storage mode as the saved payload;
a mismatched payload is rejected. Existing authored joint-speed policies remain
supported and independently check every selected serialized-key neighbor.

## Proposal handling and evidence

A saved proposal that already passes native checks needs no search. A failed
proposal whose intended unrounded motion also fails stays failed. Only a
storage-failed proposal with a feasible intended curve enters the finite search.
Each proposal starts from the explicit seed corrections, without mutating the
original authoring object or granting new key/track freedom. If no fully passing
repair is found, return the original proposal and retain every attempted repair.
A native-passing repair still goes through complete declared geometry and any
additional surface-contact checks before optimizer retention.

Every inner search export archives exact actor files, original static/key-bound
audits, complete decoded poses/residuals/caps/scales and any independent
serialized-speed audit. The intended unrounded population is saved separately.
All raw native probe assets, arrays and JSON receipts have checked bindings,
including failed/nonselected probes. Large world arrays remain on disk instead
of being retained for every search candidate. These inner archives are motion
checks, not geometry approvals; complete geometry is checked on the returned
proposal by the outer fitter.

The request snapshots the boundary/policy/start and each bound start asset.
Every source/method snapshot remains checked. The final export receives fresh
full validation and a `final-storage-continuation.json` which reproduces its
actual corrected keys against the same original source. This state carries no
quality or geometry approval. Use that explicit state for continuation; legacy
resume rejects boundary/storage fits so it cannot drop their contracts.

## Validation scope

The initial ten-module regression run passes **215 tests**. After adding complete
unrounded observations, streaming candidate worlds and failed-evidence bindings,
the complete **33-case** new suite passes. This yields **218 distinct affected
checks** across the recorded executions; it is not a claim that all 215 were
rerun after those final changes. Tests include a genuine one-neighbor-only
serialization failure repaired on a real synthetic GLB, both with and without
zero authored joint-speed limits; complete public surface jobs; exact next-state
re-export; original caps/worlds; invalid/orphan policies/budgets; altered source
and failed probe evidence; unrelated speed-audit authoring; and legacy-resume
rejection. No checkpoint, acquired character, engine or human is needed for
these source fixtures. The declared inventory is 469 Python modules / 42 Node
suites; no new complete full-inventory pass is inferred.

The first actual public workflow trial completes under
`reports/kenney-kick-automatic-storage-fit-v1`, using the retained development
humanoid, original 72-control authoring/cap epoch, explicit 18-component start,
complete 2,017-time floor population and the same 5-mm allowance. It allows one
surface iteration and up to eight stages/16 probes per proposal. The full
fraction fails two intended-motion conditions and is never precision-repaired.
The half fraction passes before storage but has four saved native failures.
Its eight-stage search clears all four in 29 neighbor exports plus the start,
allowing the optimizer to retain fraction 1/2. Final evaluation reconstructs
the same repair deterministically. Together with the original start and full
fraction there are 62 raw native export records, including repeated states.

All 107,527 original native conditions pass in the final clip. Cap arrays and
the rate clock match the original source exactly; the final continuation state
re-exports byte-for-byte. The complete 2,017-time floor population still fails
at 231 times, with a **45.560871-mm peak**. This improves the 47.600935-mm start
by 2.040064 mm but is not a usable floor/contact or realism result. The job
finishes at 651.609 s execution, within the unchanged guard; all **658** resource
observations replay with matching bindings.

A separate complete scalar-key/native/geometry replay completes under
`reports/kenney-kick-automatic-storage-replay-v2`. It independently reconstructs
the component adjustments for all **62 raw exports**, reproduces every stored
channel, clock, complete world pose, original native residual/cap/scale and
failure count. All four intended-motion populations reproduce exactly. Root
error is zero at all 2,017 times. A new full final geometry query reproduces
every producer sample and the still-failed 45.560871-mm peak/231-time result.
Its execution finishes at 437.125 s; all **448** resource observations replay.
This shares source sampler/cap/geometry mathematics, not an independent physics
engine or human assessment. Its first driver failed
before numerical verification because it expected a final geometry report in
the probe directory; the public fitter correctly writes it under
`geometry-audit`. That failed 21-observation trace and driver remain preserved.
The corrected replay uses the actual output paths and finishes without refitting
or modifying producer outputs. Source tests and these development replays do
not establish held-out, engine or human quality. Originals
remain selected and all quality/training/release approvals remain false.
