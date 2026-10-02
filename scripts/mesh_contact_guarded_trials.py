"""Sample bounded segment steps, optionally rescuing floor with a root lift.

The smallest uniform control-space lift is tried only within the same original
limits. Every retained point still needs independent exact constraint checks.
"""
import numpy as np


class GuardedMeshTrials:
    fractions=(1.,.5,.25,.125,.0625,.03125,.015625,.0078125)

    def __init__(self, coupled, margin, playback=None):
        self.coupled=coupled;self.margin=margin;self.playback=playback
        f=coupled.fitter;root=f.spec['root_node']
        self.root_weights=np.concatenate([np.sum(weights*f.descendants[root][nodes],axis=1)
                                          for nodes,points,weights in f.skin.parts])
        self.lift_direction=np.zeros(coupled.shape);self.lift_direction[:,1]=1.
        self.lift_direction=self.lift_direction.ravel()
        self.frame_lift=coupled.basis.sum(axis=1)

    def observe(self, controls):
        c=self.coupled;f=c.fitter;values=c.parameters(controls)
        floor=[];contact=[];lift=0.;rescuable=True
        allowed=-f.spec['screen']['floor_depth_m']*(1-self.margin)
        for frame,x in enumerate(values):
            points=f.skin.vertices(f.pose(frame,x)[0]);height=points[:,1]
            floor.append(1+float(height.min())/f.spec['screen']['floor_depth_m'])
            bad=height<allowed
            if np.any(bad):
                slope=self.root_weights[bad]*self.frame_lift[frame]
                if np.any(slope<=1e-12):rescuable=False
                else:lift=max(lift,float(((allowed-height[bad])/slope).max()))
            for target in f.active[frame]:
                ids=f.spec['patches'][target['patch']]['vertices']
                contact.append(1-float(np.linalg.norm(points[ids].mean(axis=0)-target['target_position_m']))/f.spec['screen']['contact_error_m'])
        if self.playback is not None:
            playback_floor=self.playback.values(controls);floor.extend(playback_floor.tolist())
            if playback_floor.min()<self.margin:
                extra=self.playback.lift(controls,self.margin)
                if extra is None:rescuable=False
                else:lift=max(lift,extra)
        return np.asarray(floor),np.asarray(contact),(lift+1e-8 if lift>0 and rescuable else None)

    def candidates(self, origin, endpoint):
        c=self.coupled
        for fraction in self.fractions:
            point=origin+(endpoint-origin)*fraction
            if not np.isfinite(point).all():continue
            motion=float(c.inequality_values(point).min())
            if motion < -1e-8:
                yield point,dict(kind='segment',fraction=fraction,lift_m=0.,motion_min=motion),None
                continue
            floor,contact,lift=self.observe(point)
            yield point,dict(kind='segment',fraction=fraction,lift_m=0.,motion_min=motion),(floor,contact)
            if floor.min()>=self.margin-1e-8 or lift is None:continue
            rescued=point+self.lift_direction*lift
            motion=float(c.inequality_values(rescued).min())
            observation=self.observe(rescued)[:2] if motion>=-1e-8 else None
            yield rescued,dict(kind='floor_lift_segment',fraction=fraction,lift_m=lift,motion_min=motion),observation
