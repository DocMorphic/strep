# Symmetric native/contact proposal derivatives

`scripts/central_coupled_contacts.py` adds a separate symmetric proposal model. The previous forward implementation and its studies remain unchanged. It accepts declared rig channels and contact references; action names and anatomical joint labels do not restrict its scope.

```python
from central_coupled_contacts import CentralCoupledContactModel

# Capture original source-rate caps before adding complete geometry clocks.
model = CentralCoupledContactModel(problem, surface_policy, contacts_sha256,
                                  maximum_contact_rows=50000)
system, jacobian, details = model.linearize(
    controls, independently_decoded_worlds, trust=0.02, step=0.001)
```

Every native edit, displacement, positional/angular rate, point-contact and held-speed row remains hard-protected. Every surface orientation and facing-side condition also receives its own no-regression guard, while its original authored limit remains in the objective and final audit. Existing source caps, time step, tolerance and uniform population must remain unchanged.

For each control, the derivative uses the complete positive and negative continuous pose samples when both full requested offsets fit its box. Near a boundary it records a one-sided offset toward available room and subtracts its matching continuous origin. Independently decoded vectors remain the proposal anchor. Complete point identities, clocks, caps and scales must agree across samples. Only exact zero coefficients are omitted from sparse storage; no numerical threshold, row subset or incident-face subset is introduced. The explicit nonzero budget rejects overflow instead of returning a partial Jacobian. Facing gaps retain their existing exact affine halfspace-to-norm conversion inside the declared trust box.

This is a Python diagnostic API, not a Studio integration or a nonlinear feasibility certificate. The caller must serialize and independently decode any proposed clip, audit native/static permissions, remeasure every original native and contact condition, and check complete declared geometry before retaining an improvement. Neither a conic solver status nor a smaller sparse matrix grants quality or release approval.

## Source reconstruction diagnostic

The immutable source proxy returns original sampled world matrices at zero edit. Nonzero edits instead reconstruct local transforms through the hierarchy. An actual source control on node 14 has 52 nodes outside its descendant subtree. Their positive and negative reconstructed worlds agree exactly, while the original shortcut and either reconstruction differ in 1,262,195 components, with a peak of 1.7763568394002505e-15.

Across all 303,593 native vector rows for that one control, the forward column contains 854,325 nonzero components and the symmetric column 134,007. Full saved-vector arithmetic and unrelated-node ancestry replay independently, with input and implementation bindings checked. This does not independently regenerate every perturbed native pose. The maximum forward/symmetric derivative difference, 0.09040988566196007, also includes ordinary stencil differences on affected motion; it must not be attributed entirely to reconstruction noise.

Local immutable evidence: `reports/native-difference-origin-development-v1` and `reports/native-difference-origin-verification-v1`.

## Full same-source comparison

The comparison retains the original 36 controls, 2,552 motion/geometry clocks, 717 uniform rate times, 303,593 native rows and 30,990 authored surface rows. Including duplicated contact guards, the system contains 365,573 norm rows with a 334,583-row hard prefix. Every control uses both full symmetric offsets for native and surface derivatives. Original native vectors/caps/scales and complete residual populations match the earlier forward model. Facing-row affine conversion offsets may differ with the derivative, while the physical clearance and residual limits remain unchanged.

| Measurement | Forward | Symmetric |
| --- | ---: | ---: |
| Native stored derivative entries | 30,656,508 | 2,514,348 |
| Protected stored derivative entries | 34,347,054 | 4,159,824 |
| Model construction, one local measurement | 28.666860 s | 50.396645 s |
| Primary Clarabel phase | MaxTime, 24 iterations | Solved, 39 iterations |

The symmetric primary minimax phase returns a direction under the unchanged 30-second phase budget. Its secondary minimum-norm phase returns MaxTime, so the implementation retains the primary direction. There are 71,453 active cones and 12 fixed failed soft rows, consistent with the separately established frozen endpoint limitation. No candidate is exported or selected in this comparison. A solved affine proposal does not establish a usable corrected motion, and the original clip remains selected.

Construction takes longer because symmetric derivatives use two perturbations. These are individual local measurements, not universal timing guarantees. The comparison performs no new geometry audit: the unchanged source geometry has prior evidence, and no candidate exists to audit. Engine, self-collision, continuous collision and human quality are unverified here.

All 24 new focused tests pass; all 118 selected central/cache/coupled/reference tests pass from an isolated source copy without vendor code, models or downloaded characters. They cover world/object/partner contacts, complete held clocks, centroid incident surfaces, boundary fallback, decoded anchoring, population/limit mutation, resource overflow and original native/contact protection. The new suite is added to the existing Linux/Windows CI populations without removing checks.

Independent actual replay verifies the complete stored base populations, native caps, individual guard duplication and all affine facing-row conversions. It re-skins every loaded vertex and face at every contact clock for positive and negative samples of control zero, independently reconstructing all 10,330 orientation vectors and 20,660 facing gaps for that derivative column. The complete native column also matches the earlier saved symmetric arithmetic exactly. This verifies one derivative column, not all 36 independently; the other columns have source tests and preserved bindings. No candidate geometry or source geometry query is rerun.

Local immutable evidence: `reports/central-coupled-contacts-development-v1`, `reports/central-coupled-contacts-clean-source-v1` and `reports/central-coupled-contacts-verification-v1`. No new motion generation, training, Studio restart or human review is involved. The full project goal and all release gates remain open. The next correction study must use the separate endpoint-editable permissions, retain original source caps and authored limits, and audit any serialized candidates before selection.
