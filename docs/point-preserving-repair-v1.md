# Point-preserving native repair

The preceding nonlinear repair reduces collision depth while increasing frame
98's failed right-hand distance from 5.085 to 11.144 mm. That result remains
failed. `pose_restoration_policy.py` makes point preservation the current runner
default: even an already-failed point row cannot worsen at a retained step.
Explicit `--point-policy tradeoff` retains the earlier search policy for
comparisons. Final point, normal, floor, body, root and finger limits are unchanged.

The complete mask permits only already-failed normal/object rows to trade in
`merit` mode when points are preserved. Passing rows always remain protected.
Floor, all three reference displacement populations, neighboring added speeds,
rotation budgets and unknown future row types are never made tradeoff eligible.
`rowwise` continues to protect every row. Neither policy approves a pose.

Every original inequality now has a unique recorded name, including all native
joint rotation rows. `row-diagnostics.json` records initial/final values, failures,
tight passing rows, allowed failed-row regressions and violations of source
protection. Its hash is bound in the result. The normalized diagnostic proximity
threshold identifies near-bound rows; it is not an acceptance allowance or an
infeasibility/stationarity certificate.

## Comparison

The source is the unchanged completed V17 study at
`reports/box-lift-authored-height-v1/`. Frame 98 uses the same controls, native
skin, fixed neighboring keys, original bounds, masked merit, nonlinear queries,
30 outer steps, 10 inner iterations, normalized trust box 0.03 and 300-second
pose budget as V4. It changes the point tradeoff mask. Frame 72's points already
stay passing throughout V4, so that identical protected behavior is not rerun.
The global owned-process guard remains 3600 seconds, 7 GiB tree RSS and at least
600 MiB available RAM; raw outputs are preserved separately.

The V5 supervisor completes in 30.578 seconds with 666,071,040 bytes peak tree
RSS. It retains the seed and stops with no guarded improvement. Point errors
stay 4.427 / 5.085 mm, normal errors 19.876 / 15.945 degrees, vertex depth
15.437 mm and maximum raw displacement 222.107 mm. The original grasp remains
failed. This establishes regression prevention, not a successful repair.

All eight recorded backoffs improve complete maximum/squared violation, but
their other constraints reject them. The full proposal violates both point
guards. Every smaller proposal worsens already-failed right-thumb-1/2 reference
displacement rows; the smallest backoff changes their normalized slack by about
-0.000010 / -0.000012. The inner solver reports its 10-iteration limit. This
evidence motivates a separate 50-inner-iteration comparison under the same
overall budgets, rather than relaxing a contact or body limit.

The V6 comparison completes in 118.063 seconds with 668,622,848 bytes peak tree
RSS. It also retains the seed. The inner solve stops with a positive directional
derivative in its line search. The full proposal misses the two exact point
guards by about 0.0000018 normalized slack; smaller backoffs regress protected
right-thumb displacement rows. A separate replay verifies all 131 saved records,
including hand point/normal and body/speed measurements. Neither a nearly passing
proposal nor a lower global merit score bypasses the original retention checks.

An optional `--point-proposal feasible --point-headroom 0.00001` asks the inner
proposal to restore both point rows to nonnegative slack with additional search
headroom. The headroom is a normalized solver margin; 0.00001 corresponds to
0.1 micrometres for point distance. It tightens proposal caps and never increases
an acceptance tolerance. The complete Boolean proposal-feasibility mask and
bounded finite per-row headroom vector are archived in both protocol and fit
result. Defaults retain the earlier preservation-only proposal for comparisons.
The final complete nonlinear retention policy still decides every backoff.

V7 applies that explicit contact-feasible proposal with the same 50-inner-step
and 300-second pose budget. Its supervisor completes in 207.782 seconds with
671,539,200 bytes peak tree RSS; the pose solve takes 196.922 seconds and hits
the 50-iteration inner limit. It retains the unchanged seed. The full proposal
violates the left point guard and a previously passing left-forearm clearance
row. Smaller backoffs again regress protected right-thumb reference rows.
A separate replay verifies all 224 saved records, including exact declared
proposal masks/headroom, complete skin, points/normals, all three body references,
neighboring speeds, diagnostics and original/archive/output hashes.

Together these comparisons preserve 385 independently replayed pose records and
zero accepted repair steps. The result is a functioning regression guard and
clearer failure evidence; the right-hand grasp still does not work. The next
proposal needs to address locally regressing body-budget directions and the
coordinated contact window. These local stalls do not prove that the requested
grasp is infeasible. A scene-guided source should also be compared if the
unchanged source cannot be repaired within the original bounds; it must remain
a distinct generation experiment with the baseline and its failures retained.

A separate NumPy replay verifies all 30 V5 pose records, input/archive/output and
diagnostic hashes, complete native vertex floor/prop depth, hand points and
triangle normals, all three reference displacements and fixed-neighbor added
speeds. It checks recorded retention decisions and the declared point mask.
No unretained inner query or backoff becomes a corrected motion.

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/my-fresh-preserved-study --frame 98 --failure-policy merit --point-policy preserve --proposal nonlinear --row-chunk 16 --solve-iterations 50 --seconds 300
```

## Source checks and scope

The fresh source copy without vendor payloads passes 162 distinct focused checks;
84 also pass in the separate runtime without Torch. The CI manifest now lists
405 model-free Python modules and 39 Node suites. New meaningful checks cover
failed-point protection despite improved collision merit, repair using another
control, complete diagnostic populations, exact masks and rejected invalid
requests, explicit proposal feasibility and finite bounded search headroom.
Third-party native motion/skin inputs remain excluded from GitHub.

No new model generation/training, full-clip correction, between-key/triangle
volume approval, rig transfer, engine import, human rating or cleanup result is
inferred. The full project goal still covers arbitrary actions, timed sequences,
scene/partner interaction, editing/style, rig transfer, transitions, engine
delivery and human validation. All fourteen release capabilities remain
unapproved.

The subsequent [tangent-protected proposal](tangent-protected-repair-v1.md)
retains one native correction that restores the right point target without
losing the left target. Orientation, penetration and displacement still fail;
the original V5/V6/V7 failures remain intact.
