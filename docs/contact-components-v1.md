# Separate finger posture from arm correction

## Completed result

All seven states finished and passed independent sample/hash recomputation in `reports/contact-components-final-v1`. Raw and finger-only peak depth is21.622598 mm. With authored fingers, arm scales25/50/75/100 percent produce21.811430/22.688447/23.301546/24.422624 mm and10/11/12/14 failing development samples. Only the full arm correction obtains11 nearby region vertices in each direction; intermediate scales obtain none. Arm-only gives the same peak as full combined motion but15 failing samples. No tested blend passes the5 mm screen. The original and full-strength endpoints reproduce the independent decoded audit within the frozen tolerance.

The completed [approach probe](contact-approach-probe-v1.md) holds the entire event pose fixed and changes only the earlier arm path. Its selected worst forearm witness improves, but larger steps worsen another surface region. All three steps preserve event geometry and hard limits; none is selected or exported. The next correction must account for multiple collision witnesses and times jointly.

## Protocol and earlier interim

The accepted local partner-contact step still fails the full geometry screen and worsens raw collision. Before changing a solver or training a model, `probe_contact_components.py` measures which authored components contribute to that tradeoff.

The frozen request in `reports/contact-components-v1` specifies seven states at the existing30 development times: raw motion, authored fingers only, accepted arm controls with raw fingers, and authored fingers with arm controls scaled to25,50,75 and100 percent. It performs fresh full-mesh queries in both directions, preserving the32-point query cap. The event additionally measures the same declared hand regions. No state is selected for release or exported as an improved clip.

Input hashes bind the completed trial, independent full export audit, local poses, arm parameters and hand regions. The raw and full-strength endpoints must reproduce the independently decoded geometry within2 micrometres. Intermediate states have only the30-time diagnostic scope; they do not inherit the299-time endpoint audit. All fixed states remain in the result, including failures.

Preflight confirms that the authored local-pose arrays change only the19 declared finger nodes on each actor. It also establishes that the previous five-degree component neighborhood excludes zero arm correction in10 coordinates; the largest initializer component is8.23683 degrees. That neighborhood can improve its fitted initializer while being unable to return to the original arm pose. This alone does not prove that a wider search is better or that raw motion is acceptable.

The first three states are complete and independently recomputed by `summarize_contact_components.py`; see `reports/contact-components-interim-v1/comparison.md`. Raw motion has peak partner penetration21.622598 mm,9 of30 samples above5 mm and no event-region vertices within3 mm. Its maximum depth difference from the decoded audit is3.61e-16 m. Fingers alone retain that peak and failure count, with three per-frame raw-cap regressions. Arms alone increase the peak to24.422624 mm and failing samples to15, while bringing11 region vertices per direction within3 mm. The four combined states remain unfinished in this snapshot. Anatomy, contact labels, between-sample collision and human quality remain unapproved.

[Skin-weight attribution](contact-collision-attribution-v1.md) places the worst retained collision on both forearms. This motivates investigating approach paths, but does not select a new solution. The [interaction-model audit](interaction-model-audit-v1.md) records why the currently inspected Uni-Inter code is not a ready commercial replacement.
