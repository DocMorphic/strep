"""Reuse immutable source queries only under matching inputs and geometry code."""
from pathlib import Path
from strep import ROOT,read,sha256
from bound_evidence import bind_inputs


QUERY_METHODS=['build_guarded_pair_witnesses.py','convex_partner_surface.py','hand_surface_screen.py',
               'rig_asset.py','rig_clip_import.py','paired_surface_witness.py','paired_approach_basis.py','gltf_tools.py']


def rebuild_witnesses(queries,hands,sample_ids):
    lookup={int(s):i for i,s in enumerate(sample_ids)};rows=[]
    for query in queries:
        source,target,sample=query['source'],query['target'],query['sample']
        if source not in [0,1] or target!=1-source or sample not in lookup:raise ValueError('Matching opposite-actor source query required')
        if query['vertices_checked']!=len(hands[source]) or query['selected_witnesses']!=len(query['records']):raise ValueError('Source hand population differs')
        for row in query['records']:
            vertex=row['vertex']
            if type(vertex) is not int or not 0<=vertex<len(hands[source]):raise ValueError('Valid hand-local vertex ID required')
            rows.append(dict(**{**row,'vertex':int(hands[source][vertex])},frame=lookup[sample],sample=sample,source=source,target=target))
    return rows


def load_queries(folder,required,hands,hand_samples):
    folder=Path(folder).resolve();result=read(folder/'result.json');request=read(folder/'request.json')
    if result['status']!='complete':raise ValueError('Completed source-witness study required')
    files={str(folder/'result.json'):sha256(folder/'result.json')}
    for name,key in [('request.json','request_sha256'),('witnesses.json','witnesses_sha256'),('source-queries.json','source_queries_sha256')]:
        if sha256(folder/name)!=result[key]:raise ValueError('Source witness artifact changed')
        files[str(folder/name)]=result[key]
    files.update(bind_inputs(required,request['inputs']))
    for name,digest in request['implementation'].items():
        path=(folder/'implementation'/name).resolve()
        if path.parent!=folder/'implementation' or sha256(path)!=digest:raise ValueError('Source witness snapshot changed')
        files[str(path)]=digest
    for name in QUERY_METHODS:
        if request['implementation'].get(name)!=sha256(ROOT/'scripts'/name):raise ValueError('Source query method differs')
    queries=read(folder/'source-queries.json');expected=[(s,a,1-a) for s in request['hand_samples'] for a in [0,1]]
    if [(q['sample'],q['source'],q['target']) for q in queries]!=expected:raise ValueError('Complete ordered donor query population required')
    if not set(request['hand_samples']).issubset(set(map(int,hand_samples))):raise ValueError('Donor samples outside requested hand clock')
    if rebuild_witnesses(queries,hands,request['sample_indices'])!=read(folder/'witnesses.json'):
        raise ValueError('Donor witnesses do not reconstruct from source queries')
    return queries,files
