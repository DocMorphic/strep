"""Exact covers of common-direction/threshold triangle-gap comparisons.

Group by identical opposite-side vertex neighborhoods; do not combine
unrelated regions or add cross-pairs. This is combinatorial transport, not
collision detection or motion approval. Callers retain all original references.
"""
import hashlib
import struct
import numpy as np

MAXIMUM_PAIR_REFERENCES = 16384
MAXIMUM_VERTEX_ID = 2**31-1


def triangle_gap_groups(left_vertices, right_vertices):
    """Factor P paired index-triples into exact complete bipartite groups.

    With one shared direction and threshold, a triangle gap is nine scalar vertex
    comparisons. Each returned group contains left/right vertex IDs whose full
    Cartesian product is a subset of exactly those original comparisons. The
    group products are disjoint and their union equals the original relation.
    Duplicate references remain in the input count/digest, without duplicating
    equivalent inequalities. Callers must partition differing point sets,
    evaluation times, normals or thresholds before grouping. None is inferred.
    """
    raw=[np.asarray(value) for value in (left_vertices,right_vertices)]
    if any(value.dtype.kind not in 'iu' for value in raw):
        raise ValueError('Integer triangle vertex references required')
    a,b=raw
    if (a.ndim!=2 or a.shape[1:]!=(3,) or not 1<=len(a)<=MAXIMUM_PAIR_REFERENCES or b.shape!=a.shape):
        raise ValueError('Complete matching bounded paired index-triples required')
    if any(np.any(value<0) or np.any(value>MAXIMUM_VERTEX_ID) for value in raw):
        raise ValueError('Nonnegative vertex IDs within the declared integer budget required')
    a,b=[value.astype('<i8',copy=True) for value in raw]
    digest=hashlib.sha256(b'strep-triangle-gap-references-v1\0'+struct.pack('<Q',len(a))+a.tobytes()+b.tobytes()).hexdigest()
    left={};right={}
    for av,bv in zip(a.tolist(),b.tolist()):
        for u in av:
            for v in bv:
                left.setdefault(u,set()).add(v);right.setdefault(v,set()).add(u)
    def partition(neighbors):
        grouped={}
        for vertex,others in neighbors.items():grouped.setdefault(tuple(sorted(others)),[]).append(vertex)
        return [(tuple(sorted(vertices)),opposite) for opposite,vertices in grouped.items()]
    left_groups=partition(left);right_groups=[(opposite,vertices) for vertices,opposite in partition(right)]
    chosen=left_groups if len(left_groups)<=len(right_groups) else right_groups
    groups=[dict(left_vertices=left,right_vertices=right) for left,right in sorted(chosen)]
    edges=sum(len(values) for values in left.values())
    if sum(len(g['left_vertices'])*len(g['right_vertices']) for g in groups)!=edges:
        raise ValueError('Complete exact relation coverage required')
    return dict(pair_references=len(a),pair_references_sha256=digest,vertex_relations=edges,
                left_neighborhood_groups=len(left_groups),right_neighborhood_groups=len(right_groups),
                grouped_by='left' if len(left_groups)<=len(right_groups) else 'right',groups=groups,
                scope='Exact common-direction vertex-comparison relation only; no added or dropped comparisons, geometry or quality approval')
