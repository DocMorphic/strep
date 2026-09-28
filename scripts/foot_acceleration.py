"""Actual foot-centroid acceleration excess; a soft development objective.

This is not a physical acceleration limit or a naturalness certificate. Caps
are frozen from baseline tracks. Every acceleration center affected by one
coordinate update is included, including centers across support boundaries.
"""
import numpy as np


def _validate(track, caps, fps, weight):
    track = np.asarray(track, dtype=float)
    caps = np.asarray(caps, dtype=float)
    if track.ndim != 3 or track.shape[2] != 3 or len(track) < 3 or track.shape[1] < 1:
        raise ValueError('Expected frame/foot/XYZ centroids for at least three frames')
    if caps.shape != (len(track)-2, track.shape[1]):
        raise ValueError('One cap per interior acceleration center and foot required')
    if not np.isfinite(track).all() or not np.isfinite(caps).all() or np.any(caps < 0):
        raise ValueError('Finite centroids and nonnegative finite caps required')
    if not np.isfinite(fps) or fps <= 0 or not np.isfinite(weight) or weight < 0:
        raise ValueError('Positive fps and nonnegative finite residual weight required')
    return track, caps


def acceleration_caps(raw, prior, fps, tolerance=1e-5):
    raw, prior = np.asarray(raw, float), np.asarray(prior, float)
    if raw.shape != prior.shape or not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Matching baseline clocks and nonnegative tolerance required')
    dummy = np.zeros((max(0, len(raw)-2), raw.shape[1] if raw.ndim == 3 else 0))
    _validate(raw, dummy, fps, 1.)
    _validate(prior, dummy, fps, 1.)
    return np.maximum(np.linalg.norm(np.diff(raw, n=2, axis=0)*fps**2, axis=2),
                      np.linalg.norm(np.diff(prior, n=2, axis=0)*fps**2, axis=2))+tolerance


def foot_acceleration_pair(track, frame, candidate, jacobian, caps, fps, weight):
    track, caps = _validate(track, caps, fps, weight)
    candidate, jacobian = np.asarray(candidate, float), np.asarray(jacobian, float)
    if type(frame) is not int or not 0 <= frame < len(track):
        raise ValueError('Valid integer frame required')
    if candidate.shape != track.shape[1:] or jacobian.ndim != 3 or jacobian.shape[:2] != candidate.shape:
        raise ValueError('Candidate foot/XYZ positions and their parameter Jacobian required')
    if not np.isfinite(candidate).all() or not np.isfinite(jacobian).all():
        raise ValueError('Finite candidate and Jacobian required')
    residual, derivative = [], []
    for center in range(max(1, frame-1), min(len(track)-2, frame+1)+1):
        coefficient = -2. if center == frame else 1.
        acceleration = (track[center-1]-2*track[center]+track[center+1]
                        + coefficient*(candidate-track[frame]))*fps**2
        magnitude = np.linalg.norm(acceleration, axis=1)
        excess = magnitude-caps[center-1]
        active = excess > 0
        direction = np.zeros_like(acceleration)
        direction[active] = acceleration[active]/magnitude[active, None]
        residual.extend(np.maximum(excess, 0)*weight)
        derivative.extend(np.einsum('si,sip->sp', direction, jacobian)*coefficient*fps**2*weight)
    return np.asarray(residual), np.asarray(derivative)


def foot_acceleration_energy(track, caps, fps, weight):
    track, caps = _validate(track, caps, fps, weight)
    excess = np.maximum(np.linalg.norm(np.diff(track, n=2, axis=0)*fps**2, axis=2)-caps, 0)*weight
    return float(np.sum(excess**2))
