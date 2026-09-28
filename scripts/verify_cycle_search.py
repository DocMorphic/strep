"""Recheck search reproducibility and locate candidate versus source defects."""
import json
from urllib.request import urlopen
import numpy as np
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_loop_search import validate,measure
from rig_contact_tracks import signals


def main():
    study=ROOT/'reports/cycle-selection-v1';outputs=[]
    for case in read(study/'cases.json')['cases']:
        search=read(study/(case['name']+'-search.json'));snapshot,pairs=validate(search['request']);folder,_,_,report,glb=snapshot
        rig=RigAsset.load(glb);sampler=AnimationSampler(rig.document,rig.binary,0);world=np.array([sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])]);masks,origin=signals(report)
        assert {(r['recipe']['start_frame'],r['recipe']['period_frames']) for r in search['candidates']}==set(pairs)
        scores=[]
        for row in search['candidates']:
            recipe=row['recipe'];a,p,k=(recipe[n] for n in ('start_frame','period_frames','blend_frames'));fresh,_,_=measure(rig,report['root_node'],world[a:a+p+k],recipe,masks,origin)
            assert abs(fresh['score']-row['score'])<1e-10;scores.append(fresh['score'])
        assert scores==sorted(scores)
        assert json.load(urlopen('http://127.0.0.1:8768'+search['report_url']))==search
        versions=[]
        for name,job in [('baseline',case['baseline_job']),('candidate',case['candidate_job'])]:
            f=ROOT/'reports/rig-jobs'/job;recipe=read(f/'loop.json');a,p,k=(recipe[n] for n in ('start_frame','period_frames','blend_frames'));row,_,_=measure(rig,report['root_node'],world[a:a+p+k],recipe,masks,origin)
            peak=row['metrics']['step_peak'];node=peak['node'];peak['bone']=rig.document['nodes'][node].get('name',str(node))
            if not peak['within_return_blend']:peak['source_frames']=[a+peak['from_frame'],a+peak['to_frame']]
            # Actual GLB and independently skinned verifier must agree with search diagnostics.
            checked=next(v for v in read(study/'verification.json')['checks'] if v['job']==job)
            assert abs(row['metrics']['step_max_deg']-checked['audit']['local_rotation_step_max_degrees'])<1e-4
            assert abs(row['metrics']['root_acceleration_max_m_s2']-checked['audit']['root_acceleration_max_m_s2'])<1e-5
            if name=='candidate':
                mesh=search['shortlist'][0]['mesh'];decoded=checked['variants'][0]
                assert abs(mesh['floor_depth_max_m']-checked['audit']['exports']['transfer']['floor_depth_max_m'])<1e-6
                assert abs(mesh['any_weight_authored_patch_speed_p95_m_s']-decoded['any_weight_authored_patch_speed_p95_m_s'])<1e-6
            versions.append(dict(version=name,job=job,recipe=recipe,metrics=row['metrics'],score=row['score'],decoded=checked['variants'][0]))
        outputs.append(dict(name=case['name'],candidates_reproduced=len(scores),versions=versions,source_glb_sha256=sha256(glb)))
    save(study/'selection-verification.json',dict(cases=outputs,scope='All finite-grid scores reproduced, immutable HTTP report matched, winning predicted diagnostics matched independently decoded exports. No semantic, naturalness or independent animator approval.'))
    print(json.dumps(outputs,indent=2))


if __name__=='__main__':main()
