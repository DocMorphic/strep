# Acceleration direction under preserved-quality checks

The completed acceleration-penalty attempt reduced foot-acceleration excess while losing floor clearance and root smoothness. This diagnostic tests a fixed parameter path from the held-support attempt toward that failed proposal. It is not a new optimizer or a product correction.

The protocol was saved before evaluation: eight fractions (0,1/64,1/32,1/16,1/8,1/4,1/2,1), one fraction shared by every frame and all root/rotation-vector edits. Original parameterization and endpoint inputs are checked; both reconstructed endpoints match their existing decoded transforms within2e-6. No adaptive fractions, extra sweeps or threshold changes follow.

Every fraction is encoded and independently checked for original hard edit bounds and transform preservation. The direction guards retain floor<=5mm, root acceleration<=max(raw,original prior)+1e-5, rotation peak<=max(raw,held)+1e-4 degrees, and support max/p95<=max(original prior,held)+1e-6m/s. Squared acceleration-cap excess must improve over held support. These guards do not replace the original full comparison, which is retained for every fraction.

| Fraction | Acceleration excess energy | Floor (mm) | Root peak (m/s²) | Rotation peak (°/frame) | Guarded improvement |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 225.4282 | 2.349 | 4.4785 | 19.959219 | no |
| 0.015625 | 216.3965 | 2.831 | 4.5466 | 19.963312 | no |
| 0.03125 | 207.6563 | 3.311 | 4.6153 | 19.967404 | no |
| 0.0625 | 190.9966 | 4.894 | 4.7542 | 19.975577 | no |
| 0.125 | 161.3313 | 8.699 | 5.0373 | 19.991967 | no |
| 0.25 | 117.9393 | 16.403 | 5.6216 | 20.024828 | no |
| 0.5 | 67.7812 | 30.709 | 6.8402 | 20.090883 | no |
| 1 | 1.2316 | 57.559 | 13.0739 | 20.224075 | no |

No nonzero fraction passes all guards; none passes the original full development screen. The two smallest moves keep floor, root and support within the guarded limits and reduce acceleration energy, but increase the peak local rotation step. All eight peaks occur on `leg_joint_L_2`, ending at frame108. The1/64 increase is0.004093 degrees; this strict numerical regression alone is not evidence of perceptible damage. Larger moves also lose root or floor clearance.

`reports/support-acceleration-path-audit-v1.json` independently decodes all1,200 integer poses and every half-frame skin, recomputes floor/root/rotation/acceleration/support guards and identifies the peak. All checks agree with the retained probe results. No game-engine run or animator review was performed for these diagnostic blends, and no blend was selected or promoted.

The next useful direction test should account for this active rotation constraint while preserving floor and root limits, rather than simply shortening the same direction or changing acceptance tolerances. The current exact no-regression screen is a development comparison; perceptual tolerance still requires independent calibration. Broader release requirements remain open.
