"""Complete object-query populations with recomputed temporary activations."""


def validate_chunk_frames(value):
    if type(value) is not int or not 0<=value<=256:
        raise ValueError('Object playback checkpoint chunk must be an integer in [0,256]')
    return value


def query_chunks(rotations,positions,skin,queries,distance,residual,mode,chunk_frames):
    """Keep every frame/vertex/object; concatenate in original clock order.

    Query trajectories and skin coefficients must stay constant during forward
    and backward. Each checkpoint closure binds its own sliced query tensors;
    loop variables must not be captured by reference for recomputation later.
    Non-reentrant checkpointing also supports ordinary autograd.grad callers.
    """
    import torch
    from torch.utils.checkpoint import checkpoint
    validate_chunk_frames(chunk_frames)
    if not chunk_frames:raise ValueError('Positive playback checkpoint chunk required')
    if (rotations.ndim!=4 or rotations.shape[-2:]!=(3,3) or not len(rotations)
            or positions.shape!=rotations.shape[:2]+(3,) or not queries):
        raise ValueError('Complete nonempty skeletal query clock required')
    if mode not in ('maximum','per_vertex'):raise ValueError('Known object constraint reduction required')
    frames=len(rotations)
    for op,orr,geometry,margin in queries:
        if (op.shape!=(frames,3) or orr.shape!=(frames,3,3)
                or op.requires_grad or orr.requires_grad):
            raise ValueError('Frozen complete object pose tracks required')
        if torch.is_tensor(margin) and (margin.requires_grad or (margin.ndim and len(margin)!=frames)):
            raise ValueError('Frozen complete object buffer tracks required')
    chunks=[]
    for start in range(0,frames,chunk_frames):
        interval=slice(start,min(start+chunk_frames,frames))
        payload=tuple((op[interval],orr[interval],geometry,
                       margin[interval] if torch.is_tensor(margin) and margin.ndim else margin)
                      for op,orr,geometry,margin in queries)
        def evaluate(r,p,objects=payload):
            vertices=skin(r,p)
            return torch.stack([residual(distance(vertices,op,orr,geometry,margin),mode)
                                for op,orr,geometry,margin in objects],0)
        chunks.append(checkpoint(evaluate,rotations[interval],positions[interval],
                                 use_reentrant=False,preserve_rng_state=False))
    result=torch.cat(chunks,dim=1)
    return list(result.unbind(0))
