"""Conservative radial escape guidance for a finite cylinder skin patch."""
import numpy as np
from grasp_orientation import unit
from sphere_approach import outward_clearance_shift


def cylinder_clearance_shift(points,geometry,position,rotation,direction,clearance):
    if geometry.shape!='cylinder':raise ValueError('Cylinder geometry required')
    if type(clearance) not in [int,float] or not np.isfinite(clearance) or clearance<0:raise ValueError('Finite nonnegative clearance required')
    points=np.asarray(points,dtype=float)
    if not len(points):raise ValueError('Nonempty skin patch required')
    distances=geometry.distance_gradient(points,position,rotation)[0]
    direction=unit(direction);local_direction=direction@rotation
    if abs(local_direction[1])>1e-10:raise ValueError('Escape direction must be radial in the cylinder frame')
    if distances.min()>=clearance:return 0.
    local=(points-position)@rotation;radius,height=geometry.dimensions
    eligible=local[np.abs(local[:,1])<height/2+clearance].copy()
    if not len(eligible):raise ValueError('Unsafe patch absent from conservative cylinder envelope')
    eligible[:,1]=0.
    # The expanded radial disk × expanded height contains the rounded cylinder
    # offset. Escape from this superset is conservative, not an exact shortest
    # translation. Interval union accounts for initially safe vertices entering.
    shift=outward_clearance_shift(eligible,np.zeros(3),local_direction,radius,clearance)
    actual=geometry.distance_gradient(points+shift*direction,position,rotation)[0]
    if actual.min()<clearance-1e-10:raise ValueError('Conservative cylinder escape failed')
    return shift
