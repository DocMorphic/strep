# Preserve clear component samples before another correction

The [complete export trace](component-export-regressions-v1.md) found two originally clear recovery samples that became colliding in the previous correction. The new `ComponentSeparationGuards` model covers every one of the 98 originally positive component samples on the unchanged original geometry clock. It is a separate type from the existing full-mesh `SeparationGuards`; component coverage cannot inherit the full-mesh partition label.

## Complete guard rows and declared coverage

`scripts/native_component_separation_guards.py` requires two complete convex components, original ordered source vertex IDs, local faces, strictly increasing times and complete same-point point derivatives. It chooses a complete component support axis independently at every supplied time and retains every ordered vertex pair. A nonpositive sample, invalid topology, missing columns or resource overflow rejects the entire population. There is no returned subset.

Each frame's required positive margin is the requested clearance capped by its starting minimum pair gap. The original 10 nm surface tolerance supplies the requested clearance in this fixture. The model therefore does not exclude its starting point when the initial separation is smaller than the requested margin. `observe` evaluates the declared fixed-axis rows against actual component points; it does not choose a more favorable axis after a step or approve other geometry.

All 98 component samples have 64 rows, giving 6,272 auxiliary hard rows. Source vertices 56–63 and faces 84–95 are authenticated as complete original connected components with unit skin weights on node 8 for both fixture actors. The label is a source binding, not a production anatomical inference. Complete winding, convexity and support candidates are checked rather than replacing the component with an axis-aligned box.

Existing full-mesh guards remain bound separately: 3,132 rows over the complete 519,840 triangle/time-pair partition at the original ten guide times. The auxiliary component model covers no other source components, self/object pairs or times between the declared samples. The full original scene gate still decides collision acceptance.

## Fresh derivative capture at the same anchor

Keep the independently verified 54-choice storage-corrected anchor and all original source payloads, caps, clocks, contact, reference, control and trust bounds. The derivative clock is the union of the ten original guide times, all 98 positive component times and the previous selected export's shifted worst-support time, 0.8947917073965073 s. Two positive times were already among the ten guides, so the union has 107 times, with 97 additional times.

All 180 central proxy observations of the original 90 controls are freshly evaluated at offsets +0.001 and -0.001. Each observation captures both complete eight-vertex components at all 107 times from complete source skins. Its entire 30,450-row native vector population and original caps/scales match the authenticated same-point native stencil. All old ten-frame component points and all 90 derivative columns match their prior full-mesh capture exactly. New component derivatives are not inferred from the old ten-frame point archive.

The additional worst-support time is captured with its complete points, derivatives and support report. It is not labelled positive or added to the positive guard population. No changed candidate curve, export, conic solve or fresh collision query is produced in this capture.

## The new checks catch the observed regression

Evaluate all 6,272 declared fixed-axis rows against the saved actual stored worlds of the previous selected original-quarter export. Exactly 32 rows fail, in the two previously identified recovery samples:

| Time, s | Failed guard rows | Best selected component support gap, mm |
| --- | ---: | ---: |
| 1.1906250417232513 | 16 | -0.226238026 |
| 1.1916667222976685 | 16 | -0.091578904 |

Maximum fixed-axis guard excess is 0.229190877 mm. This excess and the best-axis support gaps use different axes; neither is Euclidean penetration depth. No other originally positive sample fails these declared fixed-axis guards. This checks that the new population detects the measured regression, not that it solves the already colliding portion of the animation.

## Verification and next step

Thirty-two focused tests pass without skips, including unequal complete components, all pair/time identities, exact translation derivatives, capped margins, actual observations, incomplete/invalid geometry and budget rejection. A separate original-context reader manually reconstructs the anchor, all 180 observations, every 107-time point and 90 derivative columns, all original caps/scales, complete source memberships, all 98 full 348-direction populations and 6,272 guard rows/metadata. It reproduces the previous export's 32 failures and the shifted peak without calling the producer's Job, centering, component-support or component-guard APIs. Shared skinning and Float64 arithmetic remain explicit; this is not an independent collision kernel or a nonlinear enclosure.

Next integrate the separately typed auxiliary hard rows into a new correction solver version alongside the existing full-mesh guards, use the freshly captured shifted peak, and measure actual stored native conditions and every declared guard. Account for the prior measured legacy-triangle error rather than treating its affine ceiling as an actual certificate. Preserve every result and require the original complete scene gate for any changed candidate. This capture has not selected or approved a new animation.

Raw observations and provenance remain under ignored `reports/`. All fourteen release evidence arrays remain empty and the full-project goal stays active. This fixture does not establish arbitrary-action semantics, production rig transfer, engine import, animator review, cleanup time or release approval.
