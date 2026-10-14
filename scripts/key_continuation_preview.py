"""Read-only, hash-bound preview descriptors for fully replayed continuations."""
import json
import math
import struct
from strep import read,sha256
from studio_key_continuation import folder_for,manifest,require,ID


def clip_metadata(path,index):
    size=path.stat().st_size
    require(20<=size<=64*1024**2,'Bounded preview GLB required')
    with path.open('rb') as stream:
        magic,version,total,length,kind=struct.unpack('<5I',stream.read(20))
        require(magic==0x46546c67 and version==2 and total==size and kind==0x4e4f534a
            and 0<length<=min(size-20,8*1024**2),'Self-contained GLB metadata required')
        document=json.loads(stream.read(length))
    animations=document.get('animations',[])
    require(type(index) is int and 0<=index<len(animations),'Recorded animation selection required')
    require(all('uri' not in b for b in document.get('buffers',[]))
        and all('uri' not in i for i in document.get('images',[])),'Embedded preview resources required')
    clocks=[]
    for sampler in animations[index]['samplers']:
        accessor=document['accessors'][sampler['input']]
        require(accessor['type']=='SCALAR' and accessor['componentType']==5126
            and type(accessor['count']) is int and accessor['count']>0,'Float scalar preview clocks required')
        a,b=accessor.get('min'),accessor.get('max')
        require(isinstance(a,list) and isinstance(b,list) and len(a)==len(b)==1
            and all(type(v) in (int,float) and math.isfinite(v) for v in (a[0],b[0]))
            and 0<=a[0]<=b[0],'Explicit finite preview clock bounds required')
        clocks.append((a[0],b[0]))
    require(clocks and max(v[1] for v in clocks)>min(v[0] for v in clocks),'Positive preview interval required')
    return dict(animation_index=index,animation_count=len(animations),preview_start_s=min(v[0] for v in clocks),preview_end_s=max(v[1] for v in clocks))


def review(job,completion):
    require(isinstance(completion,str) and ID.fullmatch(completion),'Explicit completion digest required')
    value=manifest(job);folder=folder_for(job)
    require(value['status']=='complete' and sha256(folder/'completion.json')==completion,'Selected continuation changed; refresh Studio')
    result=read(folder/'study/result.json');previews=[]
    for id,label,download,probe in [('source','Saved starting clip',value['downloads'][0],result['probes'][0]),
            ('candidate','Returned proposal',value['downloads'][1],result['probes'][-1])]:
        require(probe['label']==('start' if id=='source' else 'final') and probe['glb_sha256']==download['sha256'],'Preview differs from recorded export')
        relative=download['url'].split('/'+job+'/',1)[1];path=folder/relative
        metadata=clip_metadata(path,probe['output_animation_index'])
        require(sha256(path)==download['sha256'],'Preview changed during metadata read')
        previews.append(dict(id=id,label=label,kind='native_key_continuation',preview_url=download['url'],preview_sha256=download['sha256'],**metadata))
    require(all(previews[0][k]==previews[1][k] for k in ('preview_start_s','preview_end_s')),'Comparison requires identical native clocks')
    require(sha256(folder/'completion.json')==completion,'Completion changed during preview read')
    return dict(value,completion_sha256=completion,previews=previews)
