# Completed restored-scene import and boundary-rejected repair

The retained development clip's complete seven-stage engine pipeline finished
on **2026-10-05 at 00:53:18 UTC**. Local evidence:
`reports/restored-endpoint-contacts-engine-v2`. Wrapper SHA256:
`415e53f3b2fb81702ad638448a93327c3bfc32757aab5e18eaf90e877993e51a`.

All stages are complete: source contacts, source object export, common object
export, object engine import, actor engine import, combined scene audit and
saved engine replay. The character is the retained development actor with GLB
SHA256 `14aa55583a6422021879a5bf7c3a119d41581b40ca8e68793cd84bd82d0415c4`.
The object named `box` remains a sphere; a second moving prop is also a sphere.
This does not demonstrate rectangular box pickup or a partner interaction.

The **native-authoring** path passes pose, point-contact and declared sampled
geometry conditions at all **2552** original times. Imported skin position error
is at most **9.515027686229957e-05 m**, within the unchanged 1e-4 m representation
limit. Native object position errors are 6.173797040005355e-08 m for `box` and
4.202302900213686e-07 m for `moving-prop`.

Default glTF import remains a recorded failure: default point contacts fail, and
`box` has a 0.0004847563504775665 maximum basis-component error. Its position
error is 4.820018050509938e-05 m. Native resources preserve authoring clocks and
poses better in this study. Successful native-resource auditing must not be
reported as successful default GLB import.

The saved replay reproduces all imported skin/contact/object observations and
all complete geometry reductions exactly. It checks 5104 actor/object geometry
observations, with maximum recorded depth upper bound 9.818365069413695e-14 m.
The transport contains 15,313 arrays and 7,371,829,696 logical bytes. Replay SHA256:
`3abe81f1b385abfb9c1f5f87daabf79a07c9f9a3bb02e39b03b33f2a6ada1029`.
This engine replay reduces saved geometry; it does not independently rerun the
geometry query kernel. The earlier fresh native-geometry replay is separate.

These engine checks measure point contacts and declared sampled geometry, not
the remaining **2066 surface-orientation failures**. No GPU rendering, real-time
playback, object/object or self/continuous collision, physics, contact force,
runtime gameplay events or human quality is approved. The original remains
selected and all release-evidence arrays remain empty.

The serialized trust-box repair then finished on **00:54:24 UTC**. It assembled
all 365741 norm rows, protecting 334751 rows. The primary minimax solve reported
`Solved`; the optional minimum-norm phase reported `AlmostSolved`. Its returned
maximum control step was **0.005000000000007317**, exceeding the exact **0.005**
calibration box by **7.317063621670172e-15**.

The guard correctly rejected that step before any candidate export or closed
motion trial. The attempt retained zero new candidates and preserved the prior
best fallback. This is a numerical trust-box overshoot, not solver infeasibility
or a proof that the authored contact cannot be reached. Its independent replay
completed at **01:03:48 UTC**, reconstructing 4440 editable keys across all five
required closed populations and reproducing complete native/surface conditions,
empirical reserves and fallback decisions. It did not recompute derivative
columns or run new geometry, since no new candidate was exported. Proof SHA256:
`d4039d52fd782f2cbaba315cda6d82735e169d4584bcf53c875830e91abc64a6`.
The static reserved-object audit then completed at 01:03:50 UTC; its results are
in `docs/reserved-object-engine-results-v1.md`. All frozen methods and raw
results remain unchanged.

A subsequent saved-model diagnostic clips the one overshooting component into
the unchanged closed box and recomputes **all 365741 affine rows**. Both the raw
and projected steps still fail **nine protected rows** (eight native and one
protected contact row), with maximum normalized
excess **3.450674945781884e-06**. Local evidence:
`reports/projected-trust-step-affine-v1`. Clipping alone therefore does not repair
the full protected affine conditions. No control-origin addition, animation
export or geometry query was performed in this diagnostic.

The next repair must establish complete protected-row feasibility for a new
proposal, potentially rebuilding the local model around the actual retained
best pose, then perform all closed motion/contact/geometry/engine checks.
Projection changes a candidate and does not inherit the solver's feasibility
or merit claims. The trust radius and all source/authoring limits must remain
unchanged; neither this numerical failure nor a conservative local model proves
global physical infeasibility.
