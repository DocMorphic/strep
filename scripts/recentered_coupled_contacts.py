"""Restore rejected native proposals against the preceding feasible contact anchor.

The rejected pose is a derivative origin, never a new cap or contact baseline.
Complete saved-curve and geometry audits still decide whether to retain motion.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows, linearize as native_linearize
from native_contact_norms import protect_rows
from coupled_native_contacts import CoupledContactModel
from central_coupled_contacts import contact_linearize


def reference_rows(current, gaps, baseline, baseline_gaps):
    """Encode original side-gap guards in the current affine norm coordinates."""
    gaps, baseline_gaps = [np.asarray(a, float) for a in (gaps, baseline_gaps)]
    if (not isinstance(current, NormRows) or not isinstance(baseline, NormRows)
            or gaps.shape != (2*len(baseline.caps),) or baseline_gaps.shape != gaps.shape
            or not np.isfinite(np.r_[gaps, baseline_gaps]).all()
            or len(current.caps) != 3*len(baseline.caps)):
        raise ValueError('Complete current and baseline contact norm/gap populations required')
    n = len(baseline.caps)
    if (not np.array_equal(current.caps[:n], baseline.caps)
            or not np.array_equal(current.scales[:n], baseline.scales)
            or np.any(current.caps[n:] < 1.)
            or not np.array_equal(current.scales[n:], np.full(2*n, .005))):
        raise ValueError('Original contact orientation limits and zero-clearance side encoding required')
    np.testing.assert_allclose(current.vectors[n:, 0], current.caps[n:]-gaps, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(current.vectors[n:, 1:], np.zeros((2*n, 2)))
    old_offsets = current.caps[n:]
    offsets = np.maximum(old_offsets, baseline_gaps+1.)
    vectors = np.r_[current.vectors[:n], np.c_[offsets-gaps, np.zeros((2*n, 2))]]
    reference_vectors = np.r_[baseline.vectors, np.c_[offsets-baseline_gaps, np.zeros((2*n, 2))]]
    caps = np.r_[baseline.caps, offsets]
    adjusted = NormRows(vectors, caps, current.scales)
    reference = NormRows(reference_vectors, caps, current.scales)
    np.testing.assert_allclose(adjusted.residual(), current.residual(), atol=1e-10, rtol=0)
    return adjusted, reference, dict(reference_side_offset_expansions=int((offsets != old_offsets).sum()),
        maximum_reference_side_offset_increase_m=float((offsets-old_offsets).max()),
        affine_side_derivatives_unchanged=True, physical_clearance_and_scales_unchanged=True,
        reference_is_previous_feasible_motion=True)


class RecenteredCoupledContactModel(CoupledContactModel):
    def linearize(self, value, decoded_worlds, baseline_value, baseline_worlds, trust, *, step=.001):
        self.check_caps()
        value, baseline_value = [self.problem.edits.controls(a) for a in (value, baseline_value)]
        for a in (value, baseline_value):
            if np.any(a < self.problem.lower) or np.any(a > self.problem.upper):
                raise ValueError('Current and previous controls must stay inside original component boxes')
        for worlds in (decoded_worlds, baseline_worlds):
            if (set(worlds) != set(self.problem.source_world)
                    or any(np.shape(worlds[n]) != original.shape or not np.isfinite(worlds[n]).all()
                           for n, original in self.problem.source_world.items())):
                raise ValueError('Complete matching finite current and baseline world populations required')
        before_native = self.problem.constraints(baseline_value, baseline_worlds)
        if np.any(before_native > 0):
            raise ValueError('Restoration requires a previously feasible native anchor')
        native, native_jac, native_identity = native_linearize(self.problem, value,
            step=step, difference_source='continuous', difference_scheme='central', base_worlds=decoded_worlds)
        current_native = self.problem.constraints(value, decoded_worlds)
        np.testing.assert_allclose(native.residual(), current_native, atol=1e-9, rtol=1e-12)
        extra, contact_jac, contact_identity = contact_linearize(self.contact, value, decoded_worlds, trust, step=step)
        baseline, baseline_gaps, baseline_identity = self.contact.sample(baseline_worlds)
        _, gaps, current_identity = self.contact.sample(decoded_worlds)
        if (baseline_identity['identity'] != current_identity['identity']
                or current_identity['identity'] != contact_identity['identity']
                or contact_identity['conversion']['clearance_m'] != 0.):
            raise ValueError('Original complete contact identities and clearance must stay unchanged')
        extra, reference, encoding = reference_rows(extra, gaps, baseline, baseline_gaps)
        before_contact = self.contact.residual(baseline_worlds)
        np.testing.assert_allclose(reference.residual(), before_contact, atol=1e-9, rtol=1e-12)
        combined = NormRows(np.r_[native.vectors, extra.vectors], np.r_[native.caps, extra.caps],
                            np.r_[native.scales, extra.scales])
        derivative = sparse.vstack([native_jac, contact_jac], format='csc')
        guarded, derivative, guard = protect_rows(combined, derivative, len(native.caps),
                                                   before_contact, reference=reference)
        self.check_caps()
        return guarded, derivative, dict(native=native_identity, contact=contact_identity,
            guard=guard, reference_encoding=encoding, hard_rows=guard['hard_rows'],
            complete_native_rows=len(native.caps), complete_surface_contact_rows=len(before_contact),
            current_native_failed_rows=int((current_native > 0).sum()), previous_native_feasible=True,
            source_caps_unchanged=True, original_contact_anchor_preserved=True,
            rejected_pose_becomes_new_baseline=False, full_geometry_in_proposal=False,
            all_native_contact_positions_and_frame_speeds_protected=True,
            individual_surface_rows_protected=True, independent_decode_and_full_geometry_required=True,
            quality_approved=False, release_approved=False)
