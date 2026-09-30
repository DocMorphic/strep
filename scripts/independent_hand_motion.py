"""Independent per-actor wrist offsets on existing oriented native-key edits.

Each editable key uses 14 controls: A/B scene wrist XYZ offsets in metres,
A/B elbow swivels in degrees, then A/B scene hand rotation vectors in degrees.
Endpoints stay frozen. This representation adds freedom, not quality approval.
"""
import numpy as np
from oriented_terminal_hand import OrientedTerminalMotion
from oriented_guide_domain import control_scales,margins as oriented_margins


def actor_controls(controls,count,actor):
    values=np.asarray(controls,float)
    if actor not in [0,1] or type(count) is not int or count<1 or values.shape!=(14*count,) or not np.isfinite(values).all():
        raise ValueError('Fourteen finite controls per key and one actor required')
    rows=values.reshape(count,14);mapped=np.zeros((count,11))
    # The underlying editor applies the old symmetric sign to B; cancel it so
    # both public wrist vectors mean their own positive scene displacement.
    mapped[:,:3]=rows[:,3*actor:3*actor+3]*(1 if actor==0 else -1)
    mapped[:,3+actor]=rows[:,6+actor]
    mapped[:,5+3*actor:8+3*actor]=rows[:,8+3*actor:11+3*actor]
    return mapped.ravel()


def from_symmetric(controls):
    values=np.asarray(controls,float)
    if values.ndim!=1 or not len(values) or len(values)%11 or not np.isfinite(values).all():
        raise ValueError('Complete finite eleven-control native rows required')
    rows=values.reshape(-1,11)
    return np.c_[rows[:,:3],-rows[:,:3],rows[:,3:]].ravel()


def scales(native,limits):
    old=control_scales(native,limits).reshape(-1,11)
    return np.c_[old[:,:3],old[:,:3],old[:,3:]].ravel()


def margins(controls,native,limits):
    # Retain the original per-actor wrist, swivel, hand and adjacent guide
    # budgets. Common-direction motion does not borrow the other actor's cap.
    return np.concatenate([oriented_margins(actor_controls(controls,len(native)-2,actor),native,limits) for actor in [0,1]])


class IndependentHandMotion:
    def __init__(self,rig,chain,native,times,protected,placement,actor):
        self.model=OrientedTerminalMotion(rig,chain,native,times,protected,placement,actor)
        self.actor=actor;self.count=len(native)-2

    def evaluate_vector(self,controls):
        return self.model.evaluate_vector(actor_controls(controls,self.count,self.actor))

    def export_vector(self,controls,path):
        return self.model.export_vector(actor_controls(controls,self.count,self.actor),path)


SYMMETRIC_LAYOUT='symmetric-wrist-v1'
INDEPENDENT_LAYOUT='independent-wrists-v1'


def layout(name):
    """Explicit persisted interpretation shared by search and return replay."""
    if name==SYMMETRIC_LAYOUT:return 11,OrientedTerminalMotion,control_scales,oriented_margins
    if name==INDEPENDENT_LAYOUT:return 14,IndependentHandMotion,scales,margins
    raise ValueError('Unknown oriented hand control layout')
