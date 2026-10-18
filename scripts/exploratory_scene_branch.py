"""Explore rejected numerical states without advancing a fixed final guard."""
import copy
import numpy as np
from sequential_scene_step import SceneStepGuard


class ExploratorySceneBranch:
    def __init__(self,final_guard):
        if type(final_guard) is not SceneStepGuard:raise ValueError('An explicit original SceneStepGuard is required')
        self._gate=copy.deepcopy(final_guard)
        self._controls=self._gate.controls;self._margins=self._gate.margins
        self.observations=0

    @property
    def controls(self):return self._controls.copy()

    @property
    def margins(self):return self._margins.copy()

    @property
    def required_rows(self):return self._gate.required_rows

    @property
    def protected_rows(self):return self._gate.protected_rows

    def _report(self,names,margins,controls):
        final=self._gate.assess(names,margins,controls)
        return dict(schema='strep-exploratory-scene-branch-v1',final_retention_gate_pass=final['accepted'],
            all_supplied_rows_nonnegative=final['all_original_numeric_rows_pass'],
            all_fixed_required_rows_pass=not bool(np.any(self._gate.required_rows & (np.asarray(margins)<0))),
            all_fixed_protected_rows_pass=not bool(final['lost_protected_row_indices']),
            original_control_balls_pass=final['all_original_control_balls_pass'],
            final_guard_report=final,exploratory_observations=self.observations,
            accepted_guard_advanced=False,candidate_selected=False,quality_approved=False,release_approved=False,
            scope='Complete caller-bound numerical observations at an exploratory point. The copied final guard, its original controls, masks and progress target never advance. A retention gate pass is separate from all supplied rows passing and from animation approval. Asset/source binding and nonlinear observations remain caller obligations.')

    def observe(self,names,margins,controls):
        report=self._report(names,margins,controls)
        if not report['original_control_balls_pass']:raise ValueError('Exploratory controls exceed original author balls')
        self._controls=np.array(controls,dtype=float,copy=True);self._margins=np.array(margins,dtype=float,copy=True)
        self.observations+=1;report['exploratory_observations']=self.observations
        return report

    def assess(self):return self._report(self._gate.names,self._margins,self._controls)
