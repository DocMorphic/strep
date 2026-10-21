# Bounded correction-step proposals

`scripts/surface_step_projection.py` provides `project_steps` for two to eight
poses of root-translation and local rotation-vector corrections. It fixes the
first pose and moves each subsequent correction block toward its corrected
predecessor only when their difference exceeds the supplied step limit minus
the fitting reserve. Already-feasible blocks retain their exact values. Inputs
are copied; invalid dimensions, limits, reserves and nonfinite arithmetic reject.

This is a proposal method, not motion approval. It bounds correction parameters,
not total motion velocity, joint anatomy, physical forces or human realism.
Projection can break a contact: a regression explicitly demonstrates this and
requires the full constraint assessment to reject the result. Callers must
recheck all pose/contact/edit conditions and decoded interpolation, preserve the
unchanged prefix, and independently verify exports. No acceptance tolerance is
added by this helper. Positive fitting reserves provide room for serialization;
the serialized result still uses the original strict acceptance criteria.

## Actual failed-window comparison

`reports/kaykit-step-projection-v1` uses the retained rejected six-key get-up
candidate from `reports/kaykit-getup-backtrack-v1`, before the later successful
warm solve. The decoded candidate's maximum root/rotation correction steps are
25.093191 mm and 5.018350 degrees. Projection changes the root correction by at
most 0.157644 mm and a rotation correction by 0.021301 degrees. After export,
the local window passes with 4.111299 mm floor depth, 19.359384 mm contact error,
24.990002 mm root step and 4.999429 degrees rotation step. Every unselected key
is unchanged, including keys 0–73.

All 3,101 required samples of the resulting 79-pose prefix pass. Actual Godot
verification in `reports/kaykit-step-projection-engine-v1` covers eight batches
and 3,116 observations, with passing floor/contact and pose/skin checks. Maximum
skin disagreement is 0.029541 mm. This is a separate method comparison; it does
not replace the newer continuation checkpoint or establish a general success
rate, solver speedup, complete-clip quality or release approval.

The candidate SHA-256 is
`3cc913cec4977bbd876ec8d2d3e71c9e13f877ad234748d6c8e2dd7dd61e56b2`;
the engine result SHA-256 is
`aebb5f62642e50682c98506ec9900754b25803d793c87dcb3e461960961cb24a`.
Twenty tests pass, covering two-, six- and eight-pose windows,
fixed-first behavior, byte-exact unchanged blocks, unchanged inputs,
invalid requests, finite arithmetic and rejection of a newly broken contact.
Both CI inventories include them (648 full and 197 focused Python files).

The next experimental caller tries projection only when all sampled pose checks
pass and step limits fail, and retains it only after every window check passes
again. The following export/full-prefix audit remains mandatory. Studio does
not yet invoke this helper automatically.
