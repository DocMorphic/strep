"""Unique complete surface correspondence and raw imported skin reconstruction."""
import numpy as np
from imported_skin_evidence import compare_surface
from imported_skin_reconstruction import ImportedSkin


def unique_correspondence(compatible):
    compatible = np.asarray(compatible, bool)
    if compatible.ndim != 2 or not len(compatible) or compatible.shape[0] != compatible.shape[1]:
        raise ValueError('Matching nonempty source/imported surface populations required')
    solutions = []
    def search(remaining, used, assignment):
        if len(solutions) > 1: return
        if not remaining:
            solutions.append(assignment.copy()); return
        options = {r: [i for i in np.flatnonzero(compatible[r]) if i not in used] for r in remaining}
        row = min(remaining, key=lambda r: len(options[r]))
        for col in options[row]:
            assignment[row] = int(col)
            search(remaining-{row}, used|{int(col)}, assignment)
    search(set(range(len(compatible))), set(), {})
    if len(solutions) != 1: raise ValueError('Unique complete imported surface correspondence required')
    return [solutions[0][r] for r in range(len(compatible))]


class ImportedSupportSurfaces:
    def __init__(self, rig, surfaces):
        if not rig.primitives or len(surfaces) != len(rig.primitives) or any(p['joints'] is None for p in rig.primitives):
            raise ValueError('All source skinned surfaces must be imported')
        names = [rig.document['nodes'][n]['name'] for n in rig.joints]
        weights = []
        for p in rig.primitives:
            w = np.zeros((len(p['positions']), len(names)))
            for col in range(p['joints'].shape[1]):
                np.add.at(w, (np.arange(len(w)), p['joints'][:, col]), p['weights'][:, col])
            weights.append(w)
        checks = {}; compatible = np.zeros((len(surfaces), len(surfaces)), bool)
        for i, p in enumerate(rig.primitives):
            for j, surface in enumerate(surfaces):
                try: check = compare_surface(p['positions'], weights[i], names, rig.inverse, surface)
                except ValueError: continue
                if check['passed']: compatible[i,j] = True; checks[i,j] = check
        self.matching = unique_correspondence(compatible)
        self.skins = [ImportedSkin(p['positions'], w, names, rig.inverse, surfaces[j])
                      for p, w, j in zip(rig.primitives, weights, self.matching)]
        self.surface_checks = [dict(source_node=p['node'], source_primitive=p['primitive'],
            imported_surface=j, **checks[i,j]) for i,(p,j) in enumerate(zip(rig.primitives,self.matching))]
        if len(self.surface_checks) == 1:
            self.data_check = checks[0,self.matching[0]].copy()
        else:
            self.data_check = dict(passed=True, surfaces=len(surfaces),
                imported_vertices=sum(c['imported_vertices'] for c in self.surface_checks),
                source_vertices=sum(c['source_vertices'] for c in self.surface_checks),
                influences=sorted({c['influences'] for c in self.surface_checks}),
                maximum_rest_position_error_m=max(c['maximum_rest_position_error_m'] for c in self.surface_checks),
                maximum_bind_matrix_error=max(c['maximum_bind_matrix_error'] for c in self.surface_checks),
                maximum_effective_weight_error=max(c['maximum_effective_weight_error'] for c in self.surface_checks),
                maximum_weight_sum_error=max(c['maximum_weight_sum_error'] for c in self.surface_checks),
                unmatched_vertices=0, source_vertex_coverage=True)

    def vertices(self, bones, bone_names):
        return np.concatenate([skin.vertices(bones, bone_names) for skin in self.skins])
