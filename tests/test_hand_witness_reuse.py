import sys,shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,save,read,sha256
from hand_witness_reuse import QUERY_METHODS,rebuild_witnesses,load_queries


def fixture(folder):
    (folder/'implementation').mkdir();methods={}
    for name in QUERY_METHODS:
        shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name);methods[name]=sha256(folder/'implementation'/name)
    source=folder/'source.dat';source.write_bytes(b'source');required={str(source):sha256(source)}
    hands=[[10,20],[30,40]];queries=[]
    for a in [0,1]:
        queries.append(dict(sample=12,frame=0,source=a,target=1-a,vertices_checked=2,selected_witnesses=1,
            records=[dict(vertex=1,target_vertices=[1,2,3],barycentric=[1.,0.,0.],normal=[0.,0.,1.],gap_m=-.02)]))
    save(folder/'request.json',dict(inputs=required,implementation=methods,hand_samples=[12],sample_indices=[12,13,14]))
    save(folder/'source-queries.json',queries);save(folder/'witnesses.json',rebuild_witnesses(queries,hands,[12,13,14]))
    seal(folder);return required,hands


def seal(folder):
    result=dict(status='complete')
    for name,key in [('request.json','request_sha256'),('source-queries.json','source_queries_sha256'),('witnesses.json','witnesses_sha256')]:result[key]=sha256(folder/name)
    save(folder/'result.json',result)


@pytest.mark.parametrize('fault',[None,'source','population','rows','method','samples','hand_order'])
def test_query_reuse_requires_bound_population_and_reconstructs_global_ids(tmp_path,fault):
    required,hands=fixture(tmp_path)
    if fault=='source':(tmp_path/'source.dat').write_bytes(b'changed')
    if fault=='population':save(tmp_path/'source-queries.json',read(tmp_path/'source-queries.json')[:1]);seal(tmp_path)
    if fault=='rows':save(tmp_path/'witnesses.json',[]);seal(tmp_path)
    if fault=='method':
        request=read(tmp_path/'request.json');name=QUERY_METHODS[0];path=tmp_path/'implementation'/name
        path.write_text('# different method');request['implementation'][name]=sha256(path);save(tmp_path/'request.json',request);seal(tmp_path)
    if fault=='hand_order':hands[0].reverse()
    samples=[11] if fault=='samples' else [10,11,12]
    if fault is None:
        queries,files=load_queries(tmp_path,required,hands,samples)
        rows=rebuild_witnesses(queries,hands,[8,9,10,11,12,13,14])
        assert [r['vertex'] for r in rows]==[20,40] and [r['frame'] for r in rows]==[4,4]
        assert str(tmp_path/'source.dat') in files
    else:
        with pytest.raises(ValueError):load_queries(tmp_path,required,hands,samples)
