"""Package supplied native rig clips for developer review; never invent ratings."""
import copy,math,shutil,uuid
from pathlib import Path
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from review_session import CATEGORIES
from portable_review_packet import package


def build(cases,output,archive,license_path):
    output,archive,license_path=[Path(p).resolve() for p in (output,archive,license_path)]
    if (output.exists() or archive.exists() or archive.is_relative_to(output)
            or output.is_relative_to(archive) or not license_path.is_file() or license_path.is_relative_to(output)):
        raise ValueError('Fresh separate packet/archive and supplied asset attribution required')
    if not isinstance(cases,list) or not 1<=len(cases)<=128:
        raise ValueError('Explicit bounded complete native review population required')
    checked=[];ids=set();bindings={str(license_path):sha256(license_path)}
    for case in cases:
        if not isinstance(case,dict) or set(case)!={'id','glb','sha256','animation_index','fps','segments','reference_node','review_context'}:
            raise ValueError('Complete explicit native clip/context binding required')
        identifier=case['id'];animation=case['animation_index'];fps=case['fps'];name=case['reference_node']
        if (type(identifier) is not str or not identifier or len(identifier)>120 or identifier in ids
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in identifier)
                or type(animation) is not int or animation<0 or type(fps) not in (int,float) or not math.isfinite(fps) or not 1<=fps<=240
                or type(name) is not str or not name or len(name)>120):raise ValueError('Distinct safe clip IDs and explicit native playback/reference selection required')
        ids.add(identifier);path=Path(case['glb']).resolve()
        if not path.is_file() or path.is_relative_to(output) or sha256(path)!=case['sha256']:
            raise ValueError('Existing unchanged native clip outside review output required')
        rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,animation)
        reference=[i for i in rig.joints if rig.document['nodes'][i].get('name')==name]
        if len(reference)!=1:
            raise ValueError('One uniquely named existing skin joint required for review framing')
        if any(item.get('uri') and not item['uri'].startswith('data:') for kind in ('buffers','images') for item in rig.document.get(kind,[])):
            raise ValueError('Self-contained native reviewer asset required')
        segments=case['segments'];context=case['review_context']
        if (not isinstance(segments,list) or not segments or any(not isinstance(s,dict) or type(s.get('prompt')) is not str or not s['prompt'].strip() for s in segments)
                or not isinstance(context,dict) or type(context.get('note')) is not str
                or type(context.get('flat_floor_screen_applicable')) is not bool):
            raise ValueError('Explicit action descriptions and visible scene/review limits required')
        unavailable=context.get('unavailable_categories',{})
        if not isinstance(unavailable,dict) or any(k not in CATEGORIES or k=='action' or type(v) is not str or not v.strip() for k,v in unavailable.items()):
            raise ValueError('Explicit valid unavailable review categories required')
        frames=int(math.ceil(reader.duration*fps-1e-5))+1
        if frames>20000:raise ValueError('Bounded reviewer playback samples required')
        bindings[str(path)]=sha256(path)
        checked.append((path,dict(id=identifier,path='clips/'+identifier+'.glb',sha256=case['sha256'],frames=frames,fps=fps,
            animation_index=animation,reference_node=name,reference_node_index=reference[0],duration_s=reader.duration,segments=copy.deepcopy(segments),review_context=copy.deepcopy(context))))
    output.mkdir(parents=True);(output/'clips').mkdir()
    for path,case in checked:
        shutil.copyfile(path,output/case['path'])
        if sha256(output/case['path'])!=case['sha256']:raise ValueError('Native reviewer copy changed animation/geometry bytes')
    shutil.copyfile(license_path,output/'LICENSE.txt');shutil.copyfile(ROOT/'scripts/human-review.html',output/'viewer.html')
    manifest=dict(schema='strep-review-packet-v1',packet_id=uuid.uuid4().hex,created_at=now(),review_type='developer',categories=CATEGORIES,
        native_asset_bytes_preserved=True,
        cases=[c for _,c in checked],instructions='Developer comparison of supplied native rig clips. Watch at normal speed and enter your own ratings. Case labels and original metadata are visible; this is not blind or independent review. Numerical motion/geometry passes do not establish realism. Record actual active editing time separately. No ratings or cleanup evidence are generated automatically.',
        quality_approved=False,release_approved=False)
    save(output/'manifest.json',manifest);result=package(output,archive)
    assert all(sha256(p)==h for p,h in bindings.items())
    result.update(manifest_sha256=sha256(output/'manifest.json'),source_bindings_sha256=bindings,
        all_native_clip_bytes_preserved=True,human_reviews_collected=0,independent_review=False,quality_approved=False,release_approved=False)
    return result
