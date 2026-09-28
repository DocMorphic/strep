# Where the retained partner collisions occur

`reports/contact-collision-attribution-v1/summary.json` joins the retained full decoded geometry results to skin weights and the candidate's saved nearest-triangle records. All consulted inputs have retained hashes. It performs no new distance query or motion correction.

The largest raw penetration is 21.622598 mm at frame 67, actor A vertex 6610, fully weighted to LeftForeArm. The largest candidate penetration is 24.422622 mm at frame 66.5, actor A vertex 6702, also fully weighted to LeftForeArm. The saved nearest target triangle at that candidate sample is fully weighted to the other actor's LeftForeArm.

Across directional samples exceeding 5 mm, the raw source's dominant skin label is forearm in 10 of 18 rows. The candidate has forearm-to-forearm labels in 20 of 28 rows. These counts represent directions and sample times, not unique collisions, vertices, elapsed duration or anatomical annotations. Other rows involve hands and fingers.

This supports testing the approach of the arms as the main collision hypothesis. Skin weights are only a proxy for anatomical location. The contact component experiment provides a separate intervention: completed finger-only results retain the raw peak and failing-sample count, while arm-only results improve event-region proximity and increase penetration. Remaining states must finish before drawing conclusions about the whole sweep. No pose is approved or promoted.
