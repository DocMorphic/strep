"""Fixed saved target-track necessities; never a joint-generation blocker.

Recorded world coordinates are held fixed. Their producer, skin/anatomy and
rig transforms are not recomputed; resampling a partner can change the targets.
"""
import hashlib
import json
import re
from pathlib import Path
from scene_contact_consistency import diagnose, source_point, point, number, squared_distance, distances_conflict, record
from strep import read, sha256

SCHEMA = 'strep-saved-reference-contact-consistency-v1'
MAXIMUM_TRACK_POINT_POPULATION = 262144
MAXIMUM_PAIR_FRAME_POPULATION = 262144


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def reference_tracks(scene, evaluation):
    """Project saved evaluations to complete target tracks, without pose arrays."""
    return dict(scene=scene,evaluation={key:evaluation[key] for key in ['scene_id','fps','frame_count','sources']} | dict(
        contact_tracks={name:track['target_world_m'] for name,track in evaluation['contact_tracks'].items()}))


def diagnose_reference(scene, supplied):
    if (not isinstance(supplied,dict) or set(supplied)!={'scene','evaluation'} or supplied['scene']!=scene
            or not isinstance(supplied['evaluation'],dict)):
        raise ValueError('Saved reference scene must match the complete authored scene')
    metadata=diagnose(scene)
    evaluation=supplied['evaluation'];count=scene['frame_count'];contacts=scene['contacts']
    if (set(evaluation)!={'scene_id','fps','frame_count','sources','contact_tracks'}
            or evaluation['scene_id']!=scene.get('id') or evaluation['fps']!=30 or evaluation['frame_count']!=count):
        raise ValueError('Saved reference clock or scene identity changed')
    sources=evaluation['sources']
    if not isinstance(sources,dict) or set(sources)!=set(scene['actors']):
        raise ValueError('Complete saved reference actor sources required')
    for name,actor in scene['actors'].items():
        if (not isinstance(actor,dict) or not isinstance(sources[name],dict) or set(sources[name])!={'path','sha256'}
                or sources[name]['path']!=actor.get('motion') or sources[name]['sha256']!=actor.get('source_sha256')
                or not isinstance(sources[name]['path'],str) or not sources[name]['path']
                or not isinstance(sources[name]['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',sources[name]['sha256'])):
            raise ValueError('Saved reference source identity changed')
    ids=[c.get('id') for c in contacts];tracks=evaluation['contact_tracks']
    if (any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids)
            or not isinstance(tracks,dict) or set(tracks)!=set(ids)):
        raise ValueError('Distinct complete saved reference contact tracks required')
    if len(ids)*count>MAXIMUM_TRACK_POINT_POPULATION:
        raise ValueError('Complete reference target-track population exceeds 262144 points; no thinning')
    parsed={}
    for contact in contacts:
        values=tracks[contact['id']]
        if not isinstance(values,list) or len(values)!=count:
            raise ValueError('Saved target tracks must cover the entire authored clock')
        parsed[contact['id']]=[point(v) for v in values]
        if contact['target'].get('space')=='world':
            expected=point(contact['target'].get('point_m'))
            if any(value!=expected for value in parsed[contact['id']]):
                raise ValueError('Saved world target track disagrees with its authored constant')
    pairs=metadata['overlapping_pairs']
    frames=sum(p['overlap_frames'][1]-p['overlap_frames'][0]+1 for p in pairs)
    if frames>MAXIMUM_PAIR_FRAME_POPULATION:
        raise ValueError('Complete reference pair-frame population exceeds 262144; no thinning')
    records=[]
    for pair in pairs:
        first,second=[contacts[i] for i in pair['contact_indices']];local=[source_point(c) for c in [first,second]]
        row={key:pair[key] for key in ['contact_indices','contact_ids','actor','joint','overlap_frames']}
        if None in local or 'tolerance_m' not in first or 'tolerance_m' not in second:
            row.update(status='unassessed',reason='Source points are not explicitly rigid joint offsets; mesh/region proxies are not substituted',frames=[])
        else:
            tolerance=sum(number(c['tolerance_m']) for c in [first,second])
            if any(number(c['tolerance_m'])<0 for c in [first,second]):raise ValueError('Nonnegative contact tolerances required')
            source=squared_distance(*local);observations=[]
            for frame in range(row['overlap_frames'][0],row['overlap_frames'][1]+1):
                target=squared_distance(parsed[first['id']][frame],parsed[second['id']][frame])
                observations.append(dict(frame=frame,target_separation_squared_m2=record(target),
                    fixed_reference_pair_conflict=distances_conflict(source,target,tolerance)))
            row.update(status='fixed_reference_pair_conflict' if any(r['fixed_reference_pair_conflict'] for r in observations) else 'fixed_reference_distance_not_contradicted',
                       source_separation_squared_m2=record(source),tolerance_sum_m=record(tolerance),frames=observations)
        records.append(row)
    return dict(schema=SCHEMA,scene_sha256=digest(scene),reference_tracks_sha256=digest(supplied),frame_count=count,
        same_joint_pair_population=metadata['same_joint_pair_population'],disjoint_pair_count=metadata['disjoint_pair_count'],
        declared_pair_frame_population=frames,overlapping_pairs=records,
        assessed_pair_frames=sum(len(r['frames']) for r in records),
        conflicting_pair_frames=sum(f['fixed_reference_pair_conflict'] for r in records for f in r['frames']),
        unassessed_pairs=sum(r['status']=='unassessed' for r in records),complete_declared_pair_population_retained=True,
        arithmetic='Exact rational comparison of saved numeric target values under ideal rigidity; rounding/producer accuracy is not recertified.',
        assumptions='All supplied target world tracks are held fixed, including partner/object references. Resampling or refitting them may change this condition.',
        scope='Saved fixed-reference necessary distances only; no joint-sampling infeasibility, anatomy, reach, collision, normals, dynamics or generated quality proof.',
        joint_generation_blocker=False,producer_correctness_revalidated=False,source_bytes_checked=False,
        source_pose_geometry_checked=False,feasibility_approved=False,quality_approved=False,release_approved=False)


def preview(bundle_path, output):
    output=Path(output)
    if output.exists():raise ValueError('Preserve prior reference diagnostic; select a new output')
    methods=Path(__file__).resolve().parent
    inputs={str(Path(p).resolve()):sha256(p) for p in [bundle_path,Path(__file__),methods/'scene_contact_consistency.py',methods/'strep.py']}
    bundle=read(bundle_path);scene=bundle['scene'];tracks=reference_tracks(scene,bundle['evaluation'])
    result=dict(schema='strep-saved-reference-contact-preview-v1',inputs_sha256=inputs,report=diagnose_reference(scene,tracks))
    if any(sha256(p)!=h for p,h in inputs.items()):raise ValueError('Reference diagnostic inputs changed during preview')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,ensure_ascii=False);stream.write('\n')
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('bundle',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();preview(args.bundle,args.output)
