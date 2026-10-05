"""Stored-key native secants with unchanged complete contact protection.

Native finite-difference probes include Float32 key storage. Contact secants
remain continuous. Discontinuous storage makes neither an error bound nor a
feasibility certificate; decoded motion and complete geometry decide retention.
"""
import numpy as np
from scipy import sparse
from coupled_native_contacts import CoupledContactModel
from central_coupled_contacts import contact_linearize
from native_scene_norms import NormRows, linearize as native_linearize
from native_contact_norms import protect_rows


class StoredNativeCoupledContactModel(CoupledContactModel):
    def linearize(self, value, decoded_worlds, trust, *, step=.001,
                  maximum_native_nonzeros=60_000_000):
        if (type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .01
                or type(trust) not in (int, float) or not np.isfinite(trust) or trust <= 0
                or type(maximum_native_nonzeros) is not int or maximum_native_nonzeros <= 0):
            raise ValueError('Bounded stored-key difference step, positive trust and nonzero budget required')
        self.check_caps()
        value = self.problem.edits.controls(value)
        residual = self.problem.constraints(value, decoded_worlds)
        if not np.isfinite(residual).all() or np.any(residual > 0):
            raise ValueError('Stored-native contact proposals require a feasible decoded native start')
        native, jac, native_identity = native_linearize(self.problem, value, step=step,
            maximum_elements=maximum_native_nonzeros, difference_source='stored',
            base_worlds=decoded_worlds, difference_scheme='central')
        np.testing.assert_allclose(native.residual(), residual, atol=1e-9, rtol=1e-12)
        extra, extra_jac, contact_identity = contact_linearize(self.contact, value,
            decoded_worlds, trust, step=step)
        before = self.contact.residual(decoded_worlds)
        np.testing.assert_allclose(extra.residual(), before, atol=1e-9, rtol=1e-12)
        combined = NormRows(np.r_[native.vectors, extra.vectors], np.r_[native.caps, extra.caps],
                            np.r_[native.scales, extra.scales])
        derivative = sparse.vstack([jac, extra_jac], format='csc')
        guarded, derivative, guard = protect_rows(combined, derivative, len(native.caps), before)
        self.check_caps()
        return guarded, derivative, dict(native=native_identity, contact=contact_identity, guard=guard,
            proposal_model='stored-native-central-continuous-contact-v1',
            hard_rows=guard['hard_rows'], complete_native_rows=len(native.caps),
            complete_surface_contact_rows=len(before), source_caps_unchanged=True,
            all_native_contact_positions_and_frame_speeds_protected=True,
            individual_surface_rows_protected=True, authored_limits_unchanged=True,
            native_difference_keys_quantized=True, contact_difference_keys_quantized=False,
            native_rotation_storage_policy=self.problem.edits.rotation_storage_policy,
            small_coefficients_discarded=False, finite_storage_secants=True,
            uniform_quantization_error_bound=False, nonlinear_feasibility_certified=False,
            full_geometry_in_proposal=False, independent_decode_and_full_geometry_required=True,
            quality_approved=False, release_approved=False)
