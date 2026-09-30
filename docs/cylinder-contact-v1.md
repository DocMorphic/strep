# Measured cylinder grasp failure

The first real-character cylinder grasp study is complete and rejected. Export and playback work, but both hands fail the combined contact conditions at every sampled contact time. The candidate reduces penetration and right-hand anchor error while worsening the previously accurate left anchor and increasing peak joint acceleration. It is retained for review, not promoted as a usable animation.

## Reproducible condition

`scripts/study_cylinder_contact.py` runs the existing Studio region-fitting workflow on the retained six-second, 180-frame development character clip from `object-release-v2/seed-11-original/palm.json`. This actor was previously corrected for a box; it is not a new Kimodo sample or cylinder-conditioned generation. Its source NPZ and GLB are copied unchanged and hash-verified.

The 0.4 m box becomes a closed cylinder with radius 0.2 m and full height 0.4 m. Both original local grips `[+/-0.2, 0.1, 0]` remain valid side-surface points. Object rotations and trajectory velocities are preserved. The continuous floor-placement bound requires a constant **3.448412 mm** upward translation to guarantee the authored 2 mm floor clearance. This is an authored condition, not cylinder physics.

The contact windows remain frames **60–120 inclusive**. The normal Studio suggested palm patches are used with 5 mm guide-anchor tolerances and the unchanged regional limits: 2 mm clearance, 3 mm contact gap, 6 mm witness spacing, 25 mm² triangle area, 5 mm centroid error, 20 mm target radius and 10-degree normal tolerance. The saved source and candidate are evaluated against exactly these same new conditions; changing from point-only contact to these patches is not claimed to preserve the original box task.

The standard Studio v14 path runs three stages of 40 iterations, balanced regional loss, bounded finger/body edits and frozen sampled object inequalities. No method or threshold is tuned after seeing the result. The solver sees 1,433 skin vertices; the independent export audit sees all **18,056 vertices** at **717 key/quarter-frame samples**. Each hand has 241 contact samples, covering the declared closed interval. Contact quality after frame 120, such as the transition to a release event at 121, is not established by those contact counts; full-clip clearance remains measured.

Fitting/export took **87.94 seconds**; the complete supervised fit/audit job took **117.27 seconds**. Peak observed process-tree memory was about **1.074 GiB**, below the 3 GiB guard. The original files, method snapshots, request, inputs, candidate, logs and failures remain saved.

## Results

| Decoded export measurement | Source in new condition | Candidate |
| --- | ---: | ---: |
| Left anchor maximum error | 0.975 mm | 6.268 mm |
| Left anchor samples within 5 mm | 241/241 | 180/241 |
| Right anchor maximum error | 104.033 mm | 14.957 mm |
| Right anchor samples within 5 mm | 4/241 | 0/241 |
| Left patch maximum penetration | 14.292 mm | 12.409 mm |
| Right patch maximum penetration | 33.283 mm | 11.486 mm |
| Left palm maximum normal error | 12.083° | 11.605° |
| Right palm maximum normal error | 37.815° | 19.576° |
| Combined hand-contact failures | 482/482 | 482/482 |
| Whole-body/object maximum penetration | 58.877 mm | 36.358 mm |
| Full-skin clearance failures | 434/717 | 375/717 |
| Minimum skin-floor height | 1.870 mm | 1.892 mm |
| Peak joint speed | 1.280603 m/s | 1.277832 m/s |
| Peak joint acceleration | 27.444606 m/s² | 39.104896 m/s² |

The source-relative rotation/root bounds pass. Maximum local rotation change is 7.777819 degrees, within the applicable body/finger limits. The constant root lift is 0.021994 mm. Root XZ coordinates and predicted foot-contact labels are byte-exact. These are edit/integrity facts, not anatomy or support-quality approval.

The input and candidate pass **822 actual Godot shared-clock pose observations** (411 each). Four authored events per variant preserve forward/reverse ordering; automatic playback, callback mutation rejection and unload checks pass. Maximum actor matrix-element error is below 6.73e-7, object error below 1.93e-7. Event delivery does not certify physical contact. Cylinder physics is still unavailable.

## What the diagnosis changes

The candidate's left hand has a valid distributed triangle witness in **241/241** contact samples and passes its normal limit in **227/241**, but its complete authored patch meets clearance in **0/241**. The right hand has witnesses in **113/241**, passes normal in **221/241**, and also meets patch clearance in **0/241**. Thus a few touching vertices or a better anchor do not make the whole hand fit the prop.

The deepest exported collision is at frame **96.25**, vertex **1268**, dominated by the `LeftHandRing4` skin weight. This vertex is omitted from the fixed optimization sample. However, included vertices still penetrate by **34.647782 mm** versus the full-skin maximum of **36.358213 mm**. Replaying the selection reproduces exactly 1,433 vertices, and its keyframe clearance violation agrees with the recorded solver residual within 1e-8 m. Missing samples contribute to the error, but increasing sample coverage alone cannot eliminate a large constraint violation already visible to the optimizer.

Do not rerun this unchanged condition with merely a larger iteration budget. Next isolate pose feasibility for the penetrating hand/patch under the existing edit bounds, then compare a correction that addresses whole-hand clearance while preserving already-good anchors and motion rates. Feasibility is currently unknown; these measurements do not prove the request impossible. Cylinder release and wider object/partner work remain separate open tasks.

## Review and evidence

After refreshing Studio, open the Scenes entries **“Cylinder grasp · measured development · Input”** and **“Cylinder grasp · measured development · Candidate”**. Both use the same cylinder condition. The candidate is labelled as needing correction. Direct Handler and allowed-file checks verify collection registration, eight saved assets/packages and editable saved contacts; no browser, network or visual-rendering check was used.

Local evidence:

- `reports/scene-region-jobs/cylinder-contact-v1`: immutable source/request snapshots, fit, independent dense audit, candidate and Studio manifest.
- `reports/scene-region-jobs/cylinder-contact-v1-input`: preserved original bundle, actor copies, authored cylinder input and baseline evaluation.
- `reports/scene-region-jobs/cylinder-contact-v1/engine-review`: input/candidate portable packages and actual engine output.
- `reports/cylinder-contact-review-v1`: verification and collision-diagnosis scripts, hash-bound results and direct route checks.

The source repository includes the study driver and this result summary; model, character and generated reports remain excluded. Reproduction requires the retained local development assets:

```powershell
.venv\Scripts\python.exe scripts/study_cylinder_contact.py reports/scene-region-jobs/<new-study-name>
```

No held-out prompt/seed reservation was consumed, no checkpoint was changed, and no release capability was approved. Naturalness, independent review, cleanup time, dynamic reactions and force/balance remain unverified. The full-project goal remains active.


Follow-up: the [single-pose diagnostic](cylinder-pose-witness-v1.md) at frame 96 also fails independent contact acceptance. The local solver termination does not establish infeasibility; its isolated output is retained without replacing the clip.
