# Exact preservation outside a local contact edit

Local contact fitting now restores the held seed's native root, joint-position, local-rotation and global-rotation arrays after reconstruction. The locked mask includes the adjoining edit-window endpoints, so interpolation outside the window uses the same keys. Every free fitted key remains byte-identical to the reconstruction output.

With a warm start, the held seed is the existing edited clip. Without one, it is the original clip. This prevents a second edit from reverting earlier work outside its selected window. The existing pre-restoration rotation/root checks still reject excessive solver drift; restoration does not conceal a failed localization constraint. The recipe separately records reconstruction drift and exact final preservation. Non-local fits retain their existing path.

This integrates the isolated preservation method from the [three-case repair experiment](preserved-export-repair-v1.md). It does not integrate that experiment's root-rate correction or turn its rejected crawling result into a pass.

## Validation

Seventy focused tests pass. They cover exact native copies, unchanged free keys, endpoint and fractional interpolation, invalid arrays/masks, correct warm-start selection, real local solver/reconstruction integration, historical archive integrity, existing checked-job invalidation, local spline constraints, initialization budgets and authored-point scaling.

A separate integration smoke test uses the real crawl-seed-22 character and the production local fitter. It runs one optimization stage with one requested iteration, once from the original clip and once from the existing fitted warm start. These abbreviated fits test preservation, not contact convergence.

| Check | Original seed | Edited warm start |
| --- | --- | --- |
| Locked native keys | 22, byte-exact | 22, byte-exact |
| Free fitted keys | Unchanged by restoration | Unchanged by restoration |
| Decoded outside-window observations | 80 | 80 |
| Maximum joint, basis and full-skin difference | Exactly zero | Exactly zero |
| Native NPZ round trip | Byte-exact pose arrays | Byte-exact pose arrays |
| BVH, GLB and eight skin influences | Pass | Pass |

The two fits used four and five objective evaluations respectively. Evidence, implementation copies, input hashes and exports are retained in `reports/contact-breadth-v1/production-held-v1/`. No new engine run, contact-quality approval, naturalness rating or cleanup time is claimed.

## Historical evidence survives method changes

The new read-only archive checker verifies completed contact studies against their saved implementation copies and artifact hashes. It checks declared case coverage, original inputs, fitted and repaired artifacts, engine captures/runtime copies, independent recheck records and aggregate counts. It does not import archived code or substitute the current solver. Original external inputs must still be present at their recorded locations.

```powershell
.venv\Scripts\python.exe scripts/verify_contact_archive.py reports/contact-breadth-v1 reports/contact-breadth-v1/batch-engine-followup-v2
```

Before and after integration, the checker verifies the same eight original cases, one contact-screen pass and 2,272 recorded engine observations. This is an integrity check of retained evidence, not a new engine replay or proof of authenticity. The existing current-code job verifier still rejects the old fit as stale, as it should; rerunning an old job under a changed implementation must not silently inherit its prior result.

## Remaining work

Exact held-pose preservation fixes reconstruction drift outside an edit. It does not prove boundary smoothness or match the objective's approximate pose calculation to final exported motion. Export-aware correction must still protect previously passing exported constraints between steps. Larger crawling/kicking pin failures still require joint-pose changes. The fixed eight-case failures remain unchanged, and every project release capability remains unapproved.
