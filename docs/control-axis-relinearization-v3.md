# Collision relinearization at the motion-feasible full step

Verified result at 2026-10-07T00:22:40.402088+00:00.

The [storage continuation](balanced-rate-storage-repair-v1.md) yields a 44-choice stored-motion-feasible anchor, with maximum depth 4.887984609217764 mm and 30398 non-disjoint triangle records. This new study recomputes all ninety point/native derivative columns at that exact point using unchanged control-axis methods. Every original scene/contact/rate/static-reference/geometry bound remains. Four actual exports retain the complete original requested fractions.

| Fraction | Stored motion failures | Centered motion failures | Depth (mm) | Triangle records | Failed geometry conditions |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 6 | 4.97146946309 | 30146 | 1613 |
| 0.5 | 6 | 0 | 4.92367569654 | 30271 | 1611 |
| 0.25 | 0 | 0 | 4.89926764536 | 30346 | 1609 |
| 0.125 | 4 | 0 | 4.89366049984 | 30363 | 1609 |

Contacts have zero failures and original reference bounds pass for all four candidates. Every geometry gate fails. **All geometry scores regress from the anchor.** The quarter-step motion pass does not justify adopting a candidate that worsens the original depth-first ranking. Every raw candidate stays unretained and the original assets remain selected and unapproved.

The model retains 30450 original norm rows and 276491 scalar surface rows. A separate consumer exactly reproduces original norms/Jacobian, all ninety point-derivative columns, every finite-axis choice/gap/surface derivative, all actual exports/native worlds/centered counts and original static/rate/reference bounds. It uses a genuine original replay context and manual stored offsets/absolute choices, with no new model/axis/job/proxy/storage implementation imports or receipt relabelling.

Another consumer independently evaluates every selected original affine norm and scalar surface row, the original roundoff-enclosing control box, all partner-depth floors and the selected-point full/retained surface envelope. The selected surface direction has original affine native excess -3.253432362306632e-10, under the unchanged 1e-9 affine tolerance. Actual exports remain a separate strict motion gate. The minimum-norm solver phase returned MaxTime; the last verified surface phase remains selected. These checks do not establish whole-box dominance or solver phase optimality. Geometry archive transport is verified; collision predicates, continuous-time geometry and physics are not independently certified.

The existing objective minimizes deficit above the external 5 mm depth floor before surface excess. It therefore permits increasing depth that remains below that floor. The next [preferred-depth comparison](preferred-depth-restoration-v1.md) changes local optimization guidance toward zero penetration, keeping all original acceptance rules. This is one generated cube-skin experiment, not broad action/rig/seed or production-character quality evidence. All fourteen release arrays remain empty.

Ignored immutable receipts: producer `f4a0b02b091f602cc17d3f2bda38d6ec0f1e9000a08fe503d87d532b6e8e1698`; complete model/export replay `8dc432a26d9ec3cf44eb1a5af8cef8142b7309ea8665babbbf99532afc010fce`; selected affine-direction evaluation `3cf8c7e262ac96516b3b182f60f073d289a67369ae98fe21dceefe76d95b4850`.
