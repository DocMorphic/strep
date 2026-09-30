# Cylinder grasp: isolated hand shape and placement

Neither hand achieves the original clearance requirement in this diagnostic. Removing arm reach and body coupling does not produce a passing local hand under the original guide binding. This narrows the next investigation to local contact geometry; it does **not** prove the original grasp infeasible.

## Method

The starting finger edits come from the iterative control in [the matched trust-region comparison](cylinder-trust-comparison-v1.md). The native source, frame 96, original guide vertices **14712 / 16974**, authored regions, target positions and all original finger rotation-norm budgets remain unchanged. Only each hand's 19 finger edits vary. All other pose parameters are frozen in the unprojected shape artifact.

Each trial then places that shape rigidly at its target with a point displacement below **4.999 mm** and normal tilt below **9.999 degrees**, inside the original 5 mm / 10 degree windows. An unrestricted axial twist is retained explicitly: a finite cylinder does not have the sphere study's symmetry around the contact normal. Four declared starting twists (0, 90, 180, 270 degrees) are searched independently for each hand.

Clearance includes all **2,735 vertices per hand** whose positive skin influences lie entirely in that hand's subtree. Both authored contact regions and all their normal faces are verified to lie in those sets. Mixed wrist/forearm vertices are excluded, so this remains a relaxed necessary-condition diagnostic. There are no floor, body, partner, self-collision, reach, time, force or anatomical guarantees.

The objective maximizes a conservative smooth minimum of actual cylinder distance, with a 0.05 mm smoothing temperature. It does not optimize distributed contact. Every retained placement is independently measured for full-hand clearance, original region clearance, contact triangle, normal and guide error. The best exact visited minimum and the terminal point are saved separately, together with the unprojected skeleton and rigidly placed hand vertices. No skeleton artifact silently receives the relaxed wrist transform.

Each search requests L-BFGS-B `maxfun=240` and `maxiter=240`, with a 30-second resource guard. SciPy reports **241–242 evaluations** before stopping at its evaluation-limit condition; these are capped local searches, not converged optima. All eight complete in 2.797–2.985 seconds, with peak observed process RSS below 589 MB. No resource interruption occurs.

## Results

Signed minimum clearance must reach **+2 mm**; negative values are penetration. These are the best visited clearance variants, independently replayed from saved arrays.

| Hand | Starting twist | Minimum hand clearance | Worst vertex | Guide error | Region normal error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Left | 0° | −0.397 mm | 1426 | 4.999 mm | 9.999° |
| Left | 90° | −0.069 mm | 1426 | 4.999 mm | 6.950° |
| Left | 180° | −0.074 mm | 1426 | 4.999 mm | 7.019° |
| Left | 270° | −0.376 mm | 1426 | 4.999 mm | 9.999° |
| Right | 0° | −0.179 mm | 3630 | 4.997 mm | 9.998° |
| Right | 90° | −0.104 mm | 11406 | 4.999 mm | 9.998° |
| Right | 180° | −0.097 mm | 3630 | 4.998 mm | 9.998° |
| Right | 270° | −0.129 mm | 3630 | 4.996 mm | 9.967° |

Each best-clearance variant has a distributed triangle that meets the original gap, spacing, area, radius and centroid conditions. That does not rescue the grasp: the rest of the authored patch still penetrates. Worst vertices 1426 and 3630 lie inside the authored regions. Right 90° has its worst vertex outside the region, but the region itself also penetrates by about 0.097 mm. The largest finger edit reaches 99.82–100.00% of its original budget across the trials.

All **16** best/terminal variants fail complete local hand acceptance. None is sent to arm projection or promoted to an animation. The small negative distances should not be described as nearly meeting the screen: the required positive clearance is still roughly 2.07–2.40 mm away.

## Verification and next decision

The independent review reconstructs every shape from source-relative rotations, compares serialized motion arrays exactly, reconstructs rigid placement with NumPy/SciPy, checks the analytic cylinder distance separately, and remeasures all regions and selection rules. Inputs, method snapshots, output hashes, frozen parameters and hand-subtree masks replay. Directional objective checks have maximum error below 7.1e-9. Twenty-seven focused tests pass, including placement derivatives, antiparallel reference handling, cylinder twist sensitivity and exclusion of arbitrarily small positive external skin influences.

Evidence is retained in `reports/cylinder-hand-placement-v1` and `reports/cylinder-hand-placement-review-v1/verification.json`. Public source CI remains separate from Torch/asset-dependent local tests. There is no visual, anatomical, engine, motion-quality or human-review approval.

The next condition should explicitly test authored guide-point alternatives **inside the same palm region**, retaining original region geometry and numeric limits. Saturated guide displacement and persistent intraregion overlap motivate that sensitivity test; they do not establish that a new binding is correct. Alternative bindings must have separate provenance and eventual anatomical/developer review. Preserve this original-condition failure, avoid another unchanged whole-body solver budget, and attempt bounded wrist projection only after a complete local hand placement passes.

With the separately acquired assets and retained source studies, reproduce into a fresh directory:

```powershell
.venv\Scripts\python.exe scripts/study_regional_hand_placement.py reports/cylinder-pose-bounded-v1 reports/cylinder-trust-comparison-v1-lsmr reports/<new-hand-placement-study>
```

All fourteen project release capabilities remain unapproved.
