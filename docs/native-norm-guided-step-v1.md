# Pose guidance under original motion bounds

`scripts/native_norm_guided_step.py` fits an explicit affine pose target while keeping every supplied original vector-norm constraint hard. This provides a candidate direction for lifting the [single-frame hand pose](hand-collision-localization-v1.md) into a curve with coupled rate and contact bounds.

The caller supplies complete original vectors, caps, scales and their Jacobian; a guidance residual and Jacobian; original control bounds; and a local trust limit. The quadratic objective reduces guidance error. Optional homogeneous rows constrain native key-parameter contributions; these rows do not guarantee a preserved rotation pose or contact.

The method requires a strictly passing original anchor and uses the existing pinned Clarabel solver. Only passing rows with exactly zero derivative are omitted from its cone construction. Every original row is checked again by the unchanged finite-ray validator. A returned step must have nonpositive original affine norm excess, satisfy the represented control/trust box and strictly reduce guidance error. Optional parameter rows use a separate 1e-9 proposal tolerance. Original export and contact limits remain unchanged.

Solver failure, nonfinite or incorrectly shaped points, and finite proposals outside the allowed proposal box return explicit rejection metadata. A finite outside-box point is retained in that metadata. A passing ray is a feasible affine candidate, without a claim of solver optimality.

Local validation has **60 passing tests and zero skips**: 19 guidance tests, 25 existing finite-ray tests and 16 native-key support tests. They cover unreachable guidance under hard caps, coupled parameter equations, complete norm checks, fixed-row omission, invalid anchors/inputs, absent improvement and invalid solver points. The new guidance suite is registered in the existing Linux and Windows source workflow; this local result does not establish hosted CI success.

The full fresh 90-control trajectory study is pending. These numerical tests do not demonstrate exported collision reduction, source-rate/contact validity after decoding, engine import, production-rig quality or human approval. Every returned record leaves quality and release approval false, and all fourteen release evidence arrays remain empty.
