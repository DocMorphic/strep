# Refined trust radius and regularization diagnosis

The verified refined correction improved peak penetration by only 0.046526 mm. This experiment asks whether the small optimization step or its quadratic penalty explains the weak result. It does not generate, accept or publish another animation.

## Fixed evidence and separate variables

Input: `reports/scene-pair-refined-reserve-completed-v1`. Retain the same 168 controls, 4,287 surface witnesses, 32,271 solver norm rows, source-relative positional/angular caps, empirical export margins, protected native keys, surface limits and five-degree edit budget. The baseline reproduces its saved controls with **zero difference**.

The solver minimizes `peak / scale + regularizer * ||step / trust||²`. In metres, the quadratic coefficient is `scale * regularizer / trust²`. Increasing trust with a constant solver regularizer also weakens that coefficient. To separate the effects, the new runner scales the regularizer by the squared trust ratio. At each radius it also tests a coefficient reduced by 10,000 times. All variants keep scale 0.025 and unchanged acceptance tolerances.

## Results

All numbers below are affine peak predictions. Initial peak penetration is 22.568796 mm; the collision screen is 5 mm.

| Trust, degrees | Physical penalty | Predicted peak, mm | Hard norm failures | Usable affine proposal |
| --- | --- | ---: | ---: | --- |
| 0.1 | Original | 22.476548 | 0 | Yes |
| 0.1 | 1/10,000 | 22.475452 | 0 | Yes |
| 0.5 | Original | 22.410912 | 1 | No |
| 0.5 | 1/10,000 | 22.336481 | 0 | Yes |
| 1 | Original | 22.410912 | 0 | Yes |
| 1 | 1/10,000 | 22.305381 | 0 | Yes |
| 5 | Original | 22.410912 | 1 | No |
| 5 | 1/10,000 | 22.231453 | 0 | Yes |

Both rejected variants report `Solved` but exceed a motion-norm comparison tolerance; their maximum excesses are 1.362174e-6 and 1.871688e-6. Solver status alone does not override the unchanged checks.

The best prediction improves only 0.337343 mm and uses about 4.882221 degrees at a native edit row, close to the original five-degree budget. Reducing the penalty at the original radius adds only 0.001095 mm improvement. Neither small-step tuning nor penalty tuning supplies the needed clearance in this local model. This is not a proof of global nonlinear infeasibility: larger steps can invalidate the linearization, and no variant was exported or queried against full meshes.

## Where the source overlaps

The deepest saved source sample is at 1.675 s, sample 34. In both query directions, the deepest witness and its target triangle are weighted essentially entirely to `LeftForeArm`. These joints are already in the selected arm chains. This identifies forearm overlap rather than an unselected finger problem; skin labels alone do not establish anatomical or motion quality. Hash-bound attribution is retained in `peak-surface-attribution.json` beside the diagnostic results.

The next study should distinguish conservative fixed-witness restrictions from the actual per-time mesh-depth limits and assess whether changing the approach path can help. Actual mesh non-regression, original motion/contact protections and independent exported-motion checks remain required. Repeated tiny improvements must not be presented as a solved interaction.

## Reproduction and validation

```powershell
.venv/Scripts/python.exe scripts/study_refined_trust_limits.py reports/scene-pair-refined-reserve-completed-v1 reports/scene-pair-refined-trust-v1
```

Use a fresh output directory. The eight solves are complete. Inputs, margins, objective settings, controls, method snapshots and rejected attempts remain bound and unchanged. Twenty-one focused tests pass, including physical-penalty invariance, explicit penalty reduction and trust/budget validation. The prior published-comparison commit `748ce3c` passed [Windows/Linux source checks](https://github.com/DocMorphic/strep/actions/runs/36711670254); that run predates this diagnostic. All release gates remain unapproved.
