"""Fixed diagonal scaling of the existing bounded vertical root coordinate.

This changes optimizer coordinates, not the lift range or initial decoded pose.
Metre units apply locally at initialization; later derivatives can differ.
Not yet connected to the scene solver or approved by an animation experiment.
"""
import math
import torch


class BoundedRootCoordinates:
    def __init__(self, initial_lift, limit):
        if (not isinstance(initial_lift, torch.Tensor) or initial_lift.ndim != 1
                or initial_lift.numel() == 0 or not initial_lift.is_floating_point()
                or initial_lift.requires_grad or not torch.isfinite(initial_lift).all()):
            raise ValueError('Finite constant floating frame-wise initial lifts required')
        if type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0:
            raise ValueError('Positive finite root limit required')
        self.limit = float(limit)
        # Exactly the legacy initialization, including its numerical inset.
        unit = (initial_lift / self.limit).clamp(1e-4, 1-1e-4)
        self.reference_logit = torch.logit(unit).detach().clone()
        # Use the decoded unit, so the local chain rule also reflects logit
        # rounding. The scale is frozen, not recomputed during line search.
        decoded_unit = torch.sigmoid(self.reference_logit)
        self.scale = (self.limit * decoded_unit * (1-decoded_unit)).detach()
        if not torch.isfinite(self.scale).all() or (self.scale <= 0).any():
            raise ValueError('Initial root derivative is not representable in this dtype')

    def initial_parameters(self):
        return torch.zeros_like(self.reference_logit)

    def __call__(self, parameters):
        if (parameters.shape != self.reference_logit.shape
                or parameters.dtype != self.reference_logit.dtype
                or parameters.device != self.reference_logit.device
                or not torch.isfinite(parameters).all()):
            raise ValueError('Finite root parameters matching the reference layout required')
        latent = self.reference_logit + parameters/self.scale
        return self.limit * torch.sigmoid(latent)

    def record(self):
        return dict(version='fixed-initial-root-jacobian-v1', limit_m=self.limit,
            scale_m_per_logit=self.scale.cpu().tolist(),
            reference_logit=self.reference_logit.cpu().tolist(),
            initial_lift_m=self(self.initial_parameters()).cpu().tolist(),
            scope='Same sigmoid lift range and legacy starting pose. Fixed scaling gives unit lift derivative at initialization only. No optimization or motion-quality evidence.')
