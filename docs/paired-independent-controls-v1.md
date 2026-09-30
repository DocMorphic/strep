# Independent wrist controls for two-character edits

The existing hand experiments share a wrist displacement vector: actor A moves
by that vector and actor B moves by its negative. This fixes the wrist midpoint
and couples each actor's permitted adjustment to the other. General interaction
editing needs the option to move either actor alone or move both in a common
direction while still preserving the final contact pose.

`independent_hand_motion.py` adds a separate native-key control representation.
Each editable key has 14 values: A's scene wrist XYZ displacement, B's scene
wrist XYZ displacement, A/B elbow swivels, and A/B scene hand rotation vectors.
Displacements are metres; angles and rotation vectors are degrees. The adapter
uses the existing validated oriented editor for each actor and leaves endpoint
keys frozen. Scale and margin helpers retain each actor's original displacement,
swivel, hand-vector and adjacent guide-rate limits; a future optimizer must
enforce those margins. Decoded joint-motion constraints remain a separate
requirement for that solve; guide limits alone do not prove them.

`from_symmetric()` converts previous eleven-value keys without resampling or
changing their intended motion. Under oblique scene placements, tests verify
each independent wrist position and hand orientation in actual exported GLBs,
unchanged motion for the other actor, exact stored frozen keys and unchanged
shared sampler channels. Converting a symmetric candidate produces byte-for-byte
identical GLBs for both actors. Common-direction wrist movement is representable,
and the guide check rejects diagonal displacement exceeding either actor's
Euclidean budget.

The focused control suite passes 32 tests and the minimal public Python suite
passes 678 tests. This module is not yet connected to
the numerical optimizer or Studio. No independent-wrist experiment, fresh mesh
audit, engine audit or quality approval has occurred. Integration must declare
the new layout, map verified warm starts, constrain both actors' actual decoded
motion, and compare its output with the symmetric baseline on identical times.

The six-key symmetric study continues unchanged. Its complete imported method
snapshot still matches the working source; this new module is not imported by
that worker. Its result must be audited before choosing the next experiment.
All 14 release capabilities remain unapproved.
