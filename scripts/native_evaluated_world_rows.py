"""Add displacement bands at every evaluated time, preserving all original rows.

This value-only adapter keeps SceneWorldRows unchanged. It does not inherit
that class: the old derivative partition assumes uniform displacement times
and must not silently accept the expanded population. Saved animations with
additional key times are rejected explicitly; no key is rounded or discarded.
"""
import copy
from pathlib import Path
import re

import numpy as np

from native_scene_world_rows import SceneWorldRows, MAXIMUM_ROWS
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import sha256


class EvaluatedWorldRows:
    def __init__(self, original, *, maximum_rows=MAXIMUM_ROWS):
        if type(original) is not SceneWorldRows:
            raise ValueError('An unchanged original SceneWorldRows snapshot is required')
        if type(maximum_rows) is not int or not 1 <= maximum_rows <= MAXIMUM_ROWS:
            raise ValueError('An explicit bounded complete row budget is required')
        problem = original._problem
        problem.scene.check_inputs()
        extra = np.setdiff1d(np.arange(len(original._times)), problem.rate_ids)
        added = len(extra) * sum(len(problem.scene.actors[name]['rig'].joints)
                                 for name in problem.edits.actors)
        rows = original._rows + added
        if rows > maximum_rows:
            raise ValueError('Complete evaluated-time row budget exceeded; no times discarded')
        self._original = copy.deepcopy(original)
        # These fields also preserve the original saved-file validator, including
        # exact duration, static payload, binary-prefix and fresh SHA checks.
        self._problem = self._original._problem
        self._times = self._original.times
        self._times.setflags(write=False)
        self._extra = extra
        self._extra.setflags(write=False)
        self._layout = list(self._original.layout)
        cursor = self._original.report['rows']
        for name in self._problem.edits.actors:
            count = len(extra) * len(self._problem.scene.actors[name]['rig'].joints)
            if count:
                self._layout.append(('evaluated_displacement', name, None, cursor, cursor + count))
                cursor += count
        assert cursor == rows
        self._report = dict(
            schema='strep-native-evaluated-world-rows-v1', rows=rows,
            original_rows=self._original.report['rows'], appended_rows=added,
            times=len(self._times), additional_displacement_times=len(extra),
            displacement_times_per_edited_actor=len(self._times),
            original_rows_byte_identical_prefix=True,
            saved_unregistered_key_times='reject; rebuild the evaluation clock explicitly',
            derivatives_included=False, native_parameter_conditions_included=False,
            surface_geometry_included=False, continuous_time_coverage=False,
            original_selected=True, quality_approved=False, release_approved=False)

    @property
    def times(self):
        return self._times.copy()

    @property
    def additional_times(self):
        return self._times[self._extra].copy()

    @property
    def layout(self):
        return tuple(self._layout)

    @property
    def report(self):
        return copy.deepcopy(self._report)

    def source_worlds(self):
        return self._original.source_worlds()

    def violations(self, worlds):
        scene = self._problem.scene
        scene.check_inputs()
        if not isinstance(worlds, dict) or set(worlds) != set(scene.actors):
            raise ValueError('Every original actor world population is required')
        copied = {}
        for name in scene.actors:
            array = np.asarray(worlds[name])
            expected = self._problem.source_world[name]
            if (array.dtype.kind not in 'fiu' or array.shape != expected.shape
                    or not np.isfinite(array).all()):
                raise ValueError('Complete finite matching actor worlds are required')
            if name not in self._problem.edits.actors and not np.array_equal(array, expected):
                raise ValueError('An actor without edit caps must remain unchanged')
            copied[name] = array.astype(float, copy=True)
        prefix = self._original.violations(copied)
        parts = [prefix]
        if len(self._extra):
            for name, permissions in self._problem.edits.actors.items():
                joints = scene.actors[name]['rig'].joints
                current = copied[name][self._extra]
                reference = self._problem.source_world[name][self._extra]
                # Match the original joint-major norm/cap arithmetic exactly.
                distance = np.linalg.norm(current[:, joints, :3, 3]
                                          - reference[:, joints, :3, 3], axis=2)
                caps = permissions['displacement']
                parts.append(((distance - caps) / caps).ravel())
        result = np.concatenate(parts)
        if result.shape != (self._report['rows'],) or not np.isfinite(result).all():
            raise ValueError('Incomplete or nonfinite evaluated-time conditions')
        scene.check_inputs()
        return result

    def evaluate_files(self, files):
        if not isinstance(files, dict) or set(files) != set(self._problem.edits.actors):
            raise ValueError('One explicit saved candidate per edited actor is required')
        # Reject candidate-only timestamps before the inherited evaluator samples
        # any pose. Its usual validator then checks every static/source invariant.
        for entry in files.values():
            if (not isinstance(entry, dict) or set(entry) != {'path', 'sha256', 'animation_index'}
                    or type(entry['animation_index']) is not int or entry['animation_index'] < 0
                    or not isinstance(entry['sha256'], str)
                    or not re.fullmatch('[a-f0-9]{64}', entry['sha256'])):
                raise ValueError('Explicit candidate path, SHA256 and animation index are required')
            path = Path(entry['path']).resolve()
            if sha256(path) != entry['sha256']:
                raise ValueError('Saved candidate changed')
            rig = RigAsset.load(path)
            reader = NativeSupportSampler(rig.document, rig.binary, entry['animation_index'])
            clocks = [channel[2] for channel in reader.channels]
            if any(not np.isin(clock, self._times).all() for clock in clocks):
                raise ValueError('Candidate contains unregistered exact key times; none may be skipped')
        result, report = SceneWorldRows.evaluate_files(self, files)
        report.update(original_rows=self._report['original_rows'],
                      appended_rows=self._report['appended_rows'],
                      evaluated_displacement_times=len(self._times),
                      scope='All original world rows plus displacement bands at every evaluated time. '
                            'Candidate keys must belong to that exact clock. Native permissions, geometry, '
                            'continuous motion, engines and human acceptance remain separate; no selection.')
        return result, report
