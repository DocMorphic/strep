"""Retain the best actually serialized feasible candidate across solver iterates."""
import numpy as np


class SerializedCheckpointSelector:
    def __init__(self, zero, evaluate, *, bound=.15, drift_tolerance=1e-6, improvement=1e-10):
        self.zero = np.asarray(zero, float).copy()
        if (self.zero.ndim != 1 or not len(self.zero) or not np.isfinite(self.zero).all() or np.any(self.zero)
                or not np.isfinite([bound, drift_tolerance, improvement]).all() or min(bound, drift_tolerance, improvement) < 0):
            raise ValueError('Zero source controls and finite nonnegative selection limits required')
        self.evaluate, self.bound, self.drift_tolerance, self.improvement = evaluate, bound, drift_tolerance, improvement
        self.cache = {}; self.records = []
        source = self._measure(self.zero)
        if not source['feasible']: raise ValueError('Source must pass actual serialized acceptance')
        self.initial_cost = source['objective']; self.best = dict(source, label='source', fraction=0.)
        self.controls = self.zero.copy()

    def _measure(self, controls):
        key = controls.tobytes()
        if key not in self.cache:
            cost, constraints, drift, _ = self.evaluate(controls)
            constraints = np.asarray(constraints, float)
            if (not np.isfinite(cost) or cost < 0 or constraints.ndim != 1 or not len(constraints)
                    or not np.isfinite(constraints).all() or not np.isfinite(drift) or drift < 0):
                raise ValueError('Finite nonnegative objective/drift and finite constraint margins required')
            minimum = float(constraints.min())
            self.cache[key] = dict(objective=float(cost), minimum_constraint=minimum, contact_matrix_drift=float(drift),
                feasible=bool(minimum >= 0 and drift <= self.drift_tolerance))
        return self.cache[key]

    def consider(self, value, label):
        value = np.asarray(value, float)
        if value.shape != self.zero.shape or not np.isfinite(value).all() or np.any(np.abs(value) > self.bound+1e-12):
            raise ValueError('Matching finite controls inside original component bounds required')
        attempts = []
        for factor in 2.**(-np.arange(9)):
            candidate = value*factor; row = dict(self._measure(candidate), fraction=float(factor))
            attempts.append(row)
            if row['feasible'] and row['objective'] < self.best['objective']-self.improvement:
                self.controls = candidate.copy(); self.best = dict(row, label=str(label))
        record = dict(label=str(label), proposed_controls=value.tolist(), serialized_attempts=attempts,
            best_label=self.best['label'], best_objective=self.best['objective'], quality_approved=False)
        self.records.append(record)
        return record
