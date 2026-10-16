"""Incremental framing keeps every value across tiny arbitrary input chunks."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_runtime_mode_stream as mode_stream
from native_runtime_mode_stream import records


@pytest.mark.parametrize('chunk',[1,2,3,7,64])
def test_unicode_strings_numbers_and_frame_order_survive_chunk_boundaries(tmp_path,chunk):
    value=dict(actors={'Char_模型':{'text':'quote " slash \\ newline\n 👍'}},
        frames=[{'index':i,'value':v} for i,v in enumerate([123456789,-1234567,-0.0,1.23456789e-120,True,None])],
        previews=[{'value':3.5}],flag=False)
    path=tmp_path/'mode.json';path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
    found=list(records(path,chunk_chars=chunk,maximum_value_chars=4096))
    assert {key:v for kind,key,v in found if kind=='field'}=={key:v for key,v in value.items() if key!='frames'}
    assert [(i,v) for kind,i,v in found if kind=='frame']==list(enumerate(value['frames']))
    assert [i for kind,i,_ in found if kind=='frame_count']==[len(value['frames'])]


@pytest.mark.parametrize('text',[
    '{"actors":{},"frames":[{"x":1e}]}',
    '{"actors":{},"frames":[{},]}',
    '{"actors":{},"frames":[],}',
    '{"actors":{},"frames":[{"x":1,"x":2}]}',
    '{"actors":{},"frames":[],"frames":[]}',
    '{"actors":{},"frames":[],"x":NaN}',
    '{"actors":{},"frames":[],"x":1e9999}',
    '{"actors":{},"frames":[] trailing}',
    '{"actors":{},"frames":[]} true',
    '{"actors":{},"frames":[{"x":"unterminated}]}',
    '{"actors":{}}',
])
def test_malformed_duplicate_truncated_or_nonfinite_values_reject(tmp_path,text):
    path=tmp_path/'bad.json';path.write_text(text,encoding='utf8')
    with pytest.raises(ValueError):list(records(path,chunk_chars=2,maximum_value_chars=1024))


def test_large_frame_array_yields_before_reading_tail_and_never_loses_frames(tmp_path,monkeypatch):
    path=tmp_path/'many.json';path.write_text(json.dumps({'actors':{},'frames':[{'i':i} for i in range(5000)],'tail':'done'}))
    original=open;consumed=[]
    class Observed:
        def __init__(self,*args,**kwargs):self.inner=original(*args,**kwargs)
        def read(self,size):
            assert size>0
            value=self.inner.read(size);consumed.append(len(value));return value
        def __enter__(self):return self
        def __exit__(self,*args):self.inner.close()
    monkeypatch.setattr(mode_stream,'open',Observed,raising=False)
    stream=records(path,chunk_chars=8,maximum_value_chars=64)
    assert next(stream)==('field','actors',{})
    assert next(stream)==('frame',0,{'i':0})
    assert sum(consumed)<256 and path.stat().st_size>50000
    count=1
    for kind,key,value in stream:
        if kind=='frame':assert key==count and value=={'i':count};count+=1
        if kind=='frame_count':assert key==5000
        if kind=='field':assert (key,value)==('tail','done')
    assert count==5000


def test_complete_header_value_budget_rejects_without_truncation(tmp_path):
    path=tmp_path/'large.json';path.write_text(json.dumps({'actors':{'text':'x'*1000},'frames':[]}))
    with pytest.raises(ValueError,match='budget'):list(records(path,chunk_chars=8,maximum_value_chars=64))
