# Root dynamics in completed support fits

`reports/support-root-diagnostic-v1.json` independently decodes both GLBs for all seven completed cases and recomputes root acceleration and its correction component. It binds the verification reports, clips and fit summaries. All seven fits retain substantial last-sweep changes0.0556–0.1111 in mixed root/rotation parameter units; stationarity is unproven. This is evidence to investigate convergence, not proof that extra iterations would fix the motion.

The gesture rig01 peak moves from raw frame22,0.4333m/s² to candidate frame1,1.8455m/s². At frame1, raw acceleration is[0.1861,-0.09436,0.04076]m/s²; correction adds[-0.01256,1.92094,0.15799]. Vertical root edits over frames0,1,2 are51.874,47.967,46.195mm. At frame148 the correction adds0.96179m/s² vertically. Both ends show changes even though drafted support spans the whole clip. This is distinct from the measured internal support-release reference jump.

The old root-curvature residual uses the second difference of correction parameters with weight10, without fps². At30fps this corresponds to a residual scale10/900 for correction acceleration. It neither caps actual root acceleration nor proves a physical trajectory. The new queued actual-foot penalty may interact with root motion but has not been shown to fix this boundary defect.

Keep the original six-sweep result and all failures. Any subsequent root/convergence correction needs full-clip root and foot dynamics, original edit budgets, contact/floor preservation and engine verification. The isolated exact sparse skin kernel is available to reduce the cost of those future experiments; it has not changed the live studies.


The eighth whole-support result adds beckon-left rig02(Quaternius): original root peak0.70030m/s² at22 becomes1.13255 at1 while support hover improves85–86mm to1.35/2.89mm and peak drift falls below0.61mm/s. Independent interimv8 verifies300engineposes and retains all24 population rows. The boundary pattern therefore appears in a second rig family; no additional root-diagnostic decode is claimed here beyond its independent stored verification/traces. Constant-root refit has so far been tested only on rig01.
