"""Exact, immutable proposal-report transport; no solver or quality decisions."""
from pathlib import Path
import math
import numpy as np
from native_observation_archive import ObservationArchive,verify,write_receipt
from strep import read,sha256

SCHEMA='strep-pose-proposal-archive-v1'


class ProposalArchive:
    def __init__(self,directory):
        self.directory=Path(directory).resolve()
        (self.directory/'proposals').mkdir(exist_ok=False)

    def __call__(self,kind,record):
        if (kind not in ['start','linearization','correction'] or type(record.get('iteration')) is not int or record['iteration']<1
                or (kind=='correction' and (type(record.get('attempt')) is not int or record['attempt']<1))):
            raise ValueError('Explicit proposal kind and iteration required')
        stem=f"{kind}-{record['iteration']}"+(f"-{record['attempt']}" if kind=='correction' else '');path=self.directory/'proposals'/f'{stem}.npz'
        metadata=path.with_suffix('.json');count=0
        def leaves(value):
            for item in value:
                if isinstance(item,list):yield from leaves(item)
                else:yield item
        with ObservationArchive(path) as archive:
            def encode(value):
                nonlocal count
                if isinstance(value,dict):
                    if any(not isinstance(k,str) for k in value):raise ValueError('String report keys required')
                    return dict(kind='dict',items={k:encode(v) for k,v in value.items()})
                if isinstance(value,list):
                    try:array=np.asarray(value)
                    except ValueError:array=np.asarray([],dtype=object)
                    types={type(v) for v in leaves(value)}
                    if len(types)==1 and types.issubset({bool,int,float}) and array.dtype.kind in 'biuf' and np.isfinite(array).all():
                        name=f'array_{count}';count+=1;archive[name]=array
                        return dict(kind='array',name=name)
                    return dict(kind='list',items=[encode(v) for v in value])
                if type(value) not in [bool,int,float,str,type(None)] or (type(value) is float and not math.isfinite(value)):
                    raise ValueError('Finite plain JSON report values required')
                return dict(kind='scalar',value=value)
            tree=encode(record)
        identity=dict(attempt=record['attempt']) if kind=='correction' else {}
        write_receipt(metadata,dict(schema=SCHEMA,kind=kind,iteration=record['iteration'],**identity,tree=tree,
            quality_approved=False,release_approved=False))
        return dict(archive_schema=SCHEMA,kind=kind,iteration=record['iteration'],**identity,metadata=metadata.relative_to(self.directory).as_posix(),
            metadata_sha256=sha256(metadata),archive_sha256=sha256(path),receipt_sha256=sha256(Path(str(path)+'.receipt.json')))


def load_record(directory,reference):
    """Replay one report at a time; legacy inline reports need no conversion."""
    if 'archive_schema' not in reference:return reference,{}
    if reference['archive_schema']!=SCHEMA or reference.get('kind') not in ['start','linearization','correction']:
        raise ValueError('Known complete proposal archive required')
    root=Path(directory).resolve();metadata=(root/reference['metadata']).resolve()
    if not metadata.is_relative_to(root/'proposals') or metadata.suffix!='.json':raise ValueError('Local proposal metadata required')
    path=metadata.with_suffix('.npz');receipt=Path(str(path)+'.receipt.json')
    bindings={metadata:reference['metadata_sha256'],path:reference['archive_sha256'],receipt:reference['receipt_sha256']}
    if any(sha256(p)!=h for p,h in bindings.items()):raise ValueError('Proposal archive binding differs')
    verify(path);document=read(metadata)
    if (document['schema']!=SCHEMA or document['kind']!=reference['kind'] or document['iteration']!=reference['iteration']
            or document['quality_approved'] is not False or document['release_approved'] is not False):
        raise ValueError('Proposal metadata identity differs')
    if reference['kind']=='correction' and (type(reference.get('attempt')) is not int or reference['attempt']<1 or document.get('attempt')!=reference['attempt']):
        raise ValueError('Bound correction-attempt identity required')
    seen=set()
    with np.load(path,allow_pickle=False) as saved:
        def decode(node):
            kind=node['kind']
            if kind=='dict':return {k:decode(v) for k,v in node['items'].items()}
            if kind=='list':return [decode(v) for v in node['items']]
            if kind=='scalar':return node['value']
            if kind!='array' or node['name'] in seen:raise ValueError('Unique complete proposal array references required')
            seen.add(node['name']);return saved[node['name']].tolist()
        record=decode(document['tree'])
        if seen!=set(saved.files):raise ValueError('Complete proposal array population required')
    if (record['iteration']!=reference['iteration'] or (reference['kind']=='correction' and record.get('attempt')!=reference['attempt'])
            or any(sha256(p)!=h for p,h in bindings.items())):
        raise ValueError('Proposal changed during replay')
    return record,{str(p):h for p,h in bindings.items()}
