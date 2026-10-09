# Repair a measured interval from its exact saved origin

The complete box-lift audit identifies frames 72–74 as the largest failure window. Its earlier 97–99 continuation preserves its immediate predecessor, but five rows regress against the original source. That continuation is not adopted as the whole-interval state. This repair path starts directly from the unchanged original source and selects its next bounded window from complete measured failures.

The original saved pose arrays define the representation baseline. Reconstructing a solver seed can alter float32 geometry; even dividing controls by their scale and multiplying back need not reproduce the original controls. The exact normalized seed maps back to the recorded original controls and arrays. New proposals are reconstructed, measured and audited separately. If no update passes, the final retained arrays remain the exact original source.

Each local proposal must pass the existing solver, tangent and saved-representation retention rules with every failed row protected. Limits, timing, references, intentional clearance, root bounds and rig budgets remain unchanged. The path uses the existing worst-first geometry proposal, bounded search-margin fallback and at most two candidate corrections per outer iteration; it does not relax acceptance limits or assume an initializer is a valid repair.

After fitting the measured window, the auditor repeats every requested contact key and both fixed exterior body edges. Adoption requires identical complete row identities, preservation of all original passing and failed rows, a nonincreasing maximum violation and improved squared violation. A locally retained candidate that fails this whole-interval check remains a rejected diagnostic proposal. The source clip and preview are never replaced.

Only four pose tracks are compared and retained. Root precision is preserved, while contact flags, heading and other omitted metadata are explicitly unapproved. Outputs include original/proposed/retained pose snapshots, full interval summaries, original-source diagnostics, local observations, archived proposals, exact-seed preflight and immutable input/method/output hashes.

```powershell
.venv/Scripts/python.exe scripts/repair_contact_interval.py reports/box-lift-authored-height-v1 reports/new-original-interval-repair --start 60 --end 121 --width 3 --iterations 8 --trust .03 --seconds 300 --solve-iterations 10
```

A fresh asset-free source fixture passes 488 focused checks across fifteen modules. Tests cover the seed roundtrip discrepancy, original array immutability, actual internal/exterior neighbors, no-improvement retention, whole-interval boundary loss, failed-row regression, invalid budgets and immutable failed studies. The new native tests are added to the CPU-native workflow; the model-free inventory remains 407 Python modules and 39 Node suites.

## Native result

The V1 run selects frames 72–74 from the complete original 62-key population. Eight local steps are retained in eight iterations; the fit stops at its iteration limit after 267.125 seconds, with 48 measurements, 49 saved observations, eight geometry initializers, fourteen candidate-correction proposals and no unretained nonlinear inner queries. The supervisor exits successfully after 353.781 seconds, with peak process-tree RSS of 1,199,337,472 bytes, under the unchanged 3,600-second / 7 GiB / 600 MiB available-RAM guards.

Dense and coupled preflight values are identical; maximum Jacobian difference is 8.882e-15. Dense/assembled times are 61.641/8.672 seconds. The original saved and reconstructed seed populations differ by up to 6.052e-6 normalized, confirming why the exact saved origin matters.

| Frame | Original penetration | Retained penetration | Original failing palm angle | Retained failing palm angle |
| --- | ---: | ---: | ---: | ---: |
| 72 | 25.715 mm | 21.312 mm | 24.080° | 22.063° |
| 73 | 25.370 mm | 21.558 mm | 23.334° | 21.374° |
| 74 | 25.081 mm | 22.181 mm | 22.789° | 21.435° |

Both working grip positions remain passing at all three edited keys, including frame 74's 4.988 mm maximum against the unchanged 4.990 mm working limit. The other palm normal remains passing, although its angle increases within the allowed limit. Floor, reference position/speed and rig/root passes remain intact at these keys. All three poses still fail clearance and the palm angles shown above.

The whole-interval comparison measures 22,720 rows for each of the original and proposed populations, including all 62 contact keys and exterior body frames 59 and 122. **No original passing row is lost and no original failed row regresses.** The full maximum normalized violation falls from 2.572636 to 2.564381, and squared violation from 3744.127018 to 3655.065891. The pose update is retained as a diagnostic interval state; the unchanged source clip and preview are not replaced.

Independent NumPy replay verifies 124 complete contact-pose audits plus four boundary frames across the full populations, and 49 local windows / 147 local poses / eight retained decisions / 90 proposal archive files. It checks exact original-seed preservation, native FK and eight-weight skin, complete saved/solver rows, physical measurements, recorded proposal vectors/cuts/caps/corrections, tangent/nonlinear/saved decisions and input/method/output hashes. Proposal derivatives and optimality are not independently certified.

The new failure-first order begins with **69–71**, then **60–62**, then **78–80**. The worst full-interval physical depth is now 25.633 mm at frame 71. All 62 contact keys still fail palm orientation and object clearance; grip failures remain 28/62 and body-reference position failures 9/62. There are still zero complete keyed or physical passes. The next step must bind this globally checked state, retain the original references and limits, and use its corrected neighboring key when repairing 69–71; starting each new window independently would discard previous repairs.

Protocol SHA-256: `bc7a51b28f5de49c669f3211bf9603bb3791818499cc3562cc49cc001fd59e77`. Result SHA-256: `ae7f3ba3ba24a440204f30f20b3498691f9815435fa82dc9c5e457958424cd2e`.

This is an experimental single-character native contact path. Complete keyed coverage does not certify between-key behavior, foot sliding, surface/self-collision, anatomy/dynamics, full-clip semantics, retargeting, metadata, engine imports or human quality. All fourteen release capabilities remain unapproved; the broad full-project goal remains active.
