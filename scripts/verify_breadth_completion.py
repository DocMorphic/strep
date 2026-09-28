"""Complete-population integrity and numerical-screen summary, no quality grant."""
from strep import ROOT,read,save,sha256,now
from breadth_study import STUDY,validate_freeze,verify_complete,summarize
from build_soma_preview import ASSET


def run():
    if read(STUDY/'pipeline.json')['status']!='complete':raise ValueError('Study is not terminal complete')
    frozen=validate_freeze(STUDY);spec=read(STUDY/'protocol.json');results={};surfaces={};files=0
    for batch in frozen['batches']:
        trials=verify_complete(batch);surface=read(STUDY/'surface'/f"{batch['id']}.json")
        if surface['mesh_sha256']!=sha256(ASSET) or surface['method_sha256']!=sha256(ROOT/'scripts/audit_body_ground.py'):raise ValueError('Surface implementation changed')
        index={(t['request_id'],t['seed']):t for t in trials}
        if len(surface['trials'])!=len(index) or {(t['request_id'],t['seed']) for t in surface['trials']}!=set(index):raise ValueError('Missing/duplicate surface row')
        for row in surface['trials']:
            key=(row['request_id'],row['seed'])
            if row['source_sha256']!=index[key]['source_sha256']:raise ValueError('Surface measured another motion')
            if key in results:raise ValueError('Duplicate exported seed')
            results[key]=index[key];files+=len(index[key]['hashes'])
            if row['result'] is not None:surfaces[key]=row['result']
    report=summarize(spec,results,surfaces)
    if report['exported']!=report['planned_actor_clips']:raise ValueError('Incomplete population')
    if any(r['mesh_floor_screen'] is None for r in report['rows'] if r['flat_floor_screen_applicable']):raise ValueError('Missing applicable skin audit')
    if any(r['mesh_floor_screen'] is not None for r in report['rows'] if not r['flat_floor_screen_applicable']):raise ValueError('Inapplicable floor score')
    groups=[]
    for family in report['families']:
        rows=[r for r in report['rows'] if r['family']==family['family']];eligible=[r for r in rows if r['flat_floor_screen_applicable']]
        groups.append(dict(family=family['family'],actor_clips=len(rows),flat_floor_applicable=len(eligible),
            mesh_floor_failures=sum(r['mesh_floor_screen'] is False for r in eligible),
            joint_floor_failures=sum(r['joint_floor_screen'] is False for r in eligible),
            predicted_support_speed_failures=sum(r['predicted_foot_speed_screen'] is False for r in eligible),
            missing_scene_validation=sum(r['scene_validation']=='missing_required_context_validation' for r in rows)))
    result=dict(at=now(),protocol_sha256=sha256(STUDY/'protocol.json'),freeze_sha256=sha256(STUDY/'freeze.json'),
        verifier_sha256=sha256(__file__),planned_cases=report['planned_cases'],exported_actor_clips=report['exported'],
        export_artifact_hashes_verified=files,batches=len(frozen['batches']),families=groups,
        human_reviews=0,quality_approved=False,scope='Complete original population and existing numerical screens. No new semantic, scene, physical or full-population engine evidence. Development set, not untouched release holdout.')
    save(STUDY/'completion-verification.json',result)
    print(result,flush=True)


if __name__=='__main__':run()
