"""CPU reconstruction from actual imported bind matrices and unrenormalized weights."""
import numpy as np
from scipy.spatial import cKDTree
from imported_skin_evidence import compare_surface


class ImportedSkin:
    def __init__(self, positions, source_weights, names, inverse_binds, observed):
        check = compare_surface(positions,source_weights,names,inverse_binds,observed)
        if not check['passed']: raise ValueError('Passing imported-data correspondence required')
        imported = np.asarray(observed['positions'],float)
        bones = np.asarray(observed['bones'],int).reshape(len(imported),check['influences'])
        weights = np.asarray(observed['weights'],float).reshape(bones.shape)
        self.names = [b['bone'] for b in observed['binds']]
        order = [names.index(n) for n in self.names]
        effective = np.zeros((len(imported),len(names)))
        for column in range(bones.shape[1]):
            np.add.at(effective,(np.arange(len(imported)),np.asarray(order)[bones[:,column]]),weights[:,column])
        options = cKDTree(imported).query_ball_point(positions,1e-6)
        mapping = []
        for row,candidates in enumerate(options):
            if not candidates: raise ValueError('Source vertex missing from imported geometry')
            errors = np.max(np.abs(effective[candidates]-source_weights[row]),axis=1)
            mapping.append(candidates[int(np.argmin(errors))])
        self.mapping = np.array(mapping,int)
        self.bones = bones[self.mapping]; self.weights = weights[self.mapping]
        bind = np.tile(np.eye(4),(len(self.names),1,1))
        serialized = np.asarray([b['pose'] for b in observed['binds']],float)
        bind[:,:3,:3] = serialized[:,:3].transpose(0,2,1); bind[:,:3,3] = serialized[:,3]
        vertices = np.c_[imported[self.mapping],np.ones(len(self.mapping))]
        self.points = np.einsum('vkij,vj->vki',bind[self.bones],vertices)

    def vertices(self, serialized_bones, bone_names):
        found = np.asarray(serialized_bones,float)
        if len(set(bone_names)) != len(bone_names) or set(bone_names) != set(self.names) or found.shape != (len(bone_names),4,3) or not np.isfinite(found).all():
            raise ValueError('Complete finite observed bone matrices required')
        transforms = np.empty((len(self.names),3,4))
        ordered = found[[bone_names.index(n) for n in self.names]]
        transforms[:,:,:3] = ordered[:,:3].transpose(0,2,1); transforms[:,:,3] = ordered[:,3]
        # Match raw imported weights. Renormalization would hide quantization.
        return np.einsum('vkij,vkj,vk->vi',transforms[self.bones],self.points,self.weights)
