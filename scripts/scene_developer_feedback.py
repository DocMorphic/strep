"""Import frame-specific developer observations bound to a scene and every actor.

This is unblinded, user-entered feedback, not independent review or approval.
"""
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from strep import ROOT, read, save, sha256, now
from gltf_tools import read_glb


def validate(data, bundle_path):
    bundle_path = Path(bundle_path).resolve()
    root = (ROOT/'reports').resolve()
    if not bundle_path.is_relative_to(root) or bundle_path.suffix != '.json':
        raise ValueError('Use a saved local scene bundle')
    keys = {'schema','created_at','reviewer_id','source','frame_range','notes','review_type',
            'independent_human','cleanup_test_performed','quality_approved'}
    if not isinstance(data,dict) or set(data)!=keys or data['schema']!='strep-scene-observation-v1':
        raise ValueError('Invalid scene observation schema')
    if data['review_type']!='non_blind_developer' or any(data[k] is not False for k in
            ['independent_human','cleanup_test_performed','quality_approved']):
        raise ValueError('Developer feedback cannot claim independence, cleanup timing or approval')
    for key,limit in [('reviewer_id',120),('notes',4000)]:
        if not isinstance(data[key],str) or not 1<=len(data[key].strip())<=limit:
            raise ValueError('Invalid '+key)
    try:
        if datetime.fromisoformat(data['created_at'].replace('Z','+00:00')).tzinfo is None:
            raise ValueError('Missing timezone')
    except (ValueError,TypeError,AttributeError) as exc:
        raise ValueError('Invalid observation timestamp') from exc
    scene=read(bundle_path)['scene'];actors=[]
    collection=None
    for folder in bundle_path.parents:
        if not folder.is_relative_to(root):break
        manifest=folder/'manifest.json'
        if manifest.is_file() and any(bundle_path.relative_to(folder).as_posix() in row.get('variants',{}).values()
                                      for row in read(manifest).get('scenes',[])):
            collection=folder;break
    if collection is None:raise ValueError('Scene is not listed in a saved collection')
    if type(scene['frame_count']) is not int or scene['frame_count']<1 or scene['fps']!=30:
        raise ValueError('Expected saved 30 fps scene')
    bundle_url='/files/'+bundle_path.relative_to(root).as_posix()
    for name,actor in sorted(scene['actors'].items()):
        relative=actor['preview_glb']
        if not isinstance(relative,str) or urlsplit(relative).scheme or '?' in relative or '#' in relative or '%' in relative or '\\' in relative:
            raise ValueError('Invalid actor asset path')
        clip=(collection/relative).resolve()
        if not clip.is_relative_to(collection) or clip.suffix!='.glb':
            raise ValueError('Actor asset escaped saved scene directory')
        doc,_=read_glb(clip)
        if any(row.get('uri') and not row['uri'].startswith('data:') for row in doc.get('buffers',[])+doc.get('images',[])):
            raise ValueError('Review requires embedded actor assets')
        actors.append(dict(actor=name,glb_url='/files/'+clip.relative_to(root).as_posix(),glb_sha256=sha256(clip)))
    if not actors:raise ValueError('Scene has no actors')
    expected=dict(collection_url='/files/'+collection.relative_to(root).as_posix()+'/',bundle_url=bundle_url,bundle_sha256=sha256(bundle_path),scene_id=scene['id'],frames=scene['frame_count'],fps=scene['fps'],actors=actors)
    if data['source']!=expected:raise ValueError('Feedback belongs to a different scene or actor version')
    span=data['frame_range']
    if not isinstance(span,dict) or set(span)!={'start','end_inclusive'} or any(type(v) is not int for v in span.values()) or not 0<=span['start']<=span['end_inclusive']<scene['frame_count']:
        raise ValueError('Frame range outside reviewed scene')
    return dict(valid=True,source=expected,independent_review=False,quality_approved=False,
                scope='Source-bound developer report; reviewer identity and observations are not independently verified. No release acceptance or cleanup-time evidence.')


def import_feedback(bundle,response,output):
    bundle,response,output=Path(bundle),Path(response),Path(output)
    if output.exists():raise ValueError('Preserve existing feedback import')
    data=read(response);result=validate(data,bundle)
    output.mkdir(parents=True)
    save(output/'observation.json',data)
    save(output/'validation.json',dict(at=now(),response_sha256=sha256(response),observation_sha256=sha256(output/'observation.json'),**result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(import_feedback(a.bundle,a.response,a.output))
