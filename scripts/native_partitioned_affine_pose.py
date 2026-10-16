"""Wider native pose construction with the unchanged affine evaluation method.

Constructor partitions validate existing tracks; evaluation still propagates one
complete hierarchy/Jacobian, including ancestry across partition boundaries.
"""
import numpy as np
from native_affine_key_pose import AffineKeyPose

MAX_DERIVATIVE_BYTES=128*1024**2
MAX_ESTIMATED_WORKSPACE_BYTES=256*1024**2


class PartitionedAffineKeyPose(AffineKeyPose):
    def __init__(self,actor,time_s,nodes,degrees,*,constructor_block_nodes=16):
        nodes=list(nodes);degrees=list(degrees)
        if (not 1<=len(nodes)<=32 or len(set(nodes))!=len(nodes) or len(degrees)!=len(nodes)
                or any(type(n) is not int or n not in actor['rig'].joints for n in nodes)
                or any(type(v) not in (int,float) or not np.isfinite(v) or not 0<v<=30 for v in degrees)
                or type(constructor_block_nodes) is not int or not 1<=constructor_block_nodes<=16
                or type(time_s) not in (int,float) or not np.isfinite(time_s) or not 0<=time_s<=actor['sampler'].duration):
            raise ValueError('Explicit 1-32 distinct native joints, finite caps/time and 1-16 constructor block size required')
        size=3*len(nodes);skin=actor['skin'];vertices,influences=skin.nodes.shape
        derivative=vertices*3*size*8;world=len(actor['rig'].parents)*4*4*size*8
        gather=min(512,vertices)*influences*3*4*size*8
        estimated=3*derivative+2*world+2*gather
        if derivative>MAX_DERIVATIVE_BYTES or estimated>MAX_ESTIMATED_WORKSPACE_BYTES:
            raise ValueError('Complete native pose derivatives exceed explicit workspace budget; no controls or influences discarded')
        parts=[AffineKeyPose(actor,time_s,nodes[a:a+constructor_block_nodes],degrees[a:a+constructor_block_nodes])
            for a in range(0,len(nodes),constructor_block_nodes)]
        first=parts[0]
        for part in parts[1:]:
            np.testing.assert_array_equal(first.source,part.source);np.testing.assert_array_equal(first.local,part.local)
            if first.order!=part.order:raise ValueError('Constructor partitions disagree on source hierarchy')
        self.__dict__.update(first.__dict__)
        self.nodes=nodes;self.caps=np.concatenate([p.caps for p in parts]);self.size=size
        self.rotations=[v for p in parts for v in p.rotations];self.scales=[v for p in parts for v in p.scales]
        self.affected=np.logical_or.reduce([p.affected for p in parts])
        self.construction=dict(schema='strep-partitioned-affine-pose-v1',constructor_blocks=[p.nodes for p in parts],
            complete_controls=size,derivative_bytes=derivative,estimated_workspace_bytes=estimated,
            derivative_budget_bytes=MAX_DERIVATIVE_BYTES,workspace_budget_bytes=MAX_ESTIMATED_WORKSPACE_BYTES,
            evaluator='Unchanged AffineKeyPose.evaluate; complete coupled hierarchy, not independent block motion.',
            original_reference_preserved=True,geometry_approved=False,quality_approved=False,release_approved=False,
            scope='Explicit allocation estimates, not measured RSS or a guarantee about third-party temporary allocations. Use a guarded worker.')
