"""Visualize the isolated source-context transfer fix on paired inputs."""
from strep import ROOT,read,save


def build():
    out=ROOT/'reports/context-transfer-v1';verified={(r['case'],r['mode'],r['version']):r for r in read(out/'verification.json')['cases']};cases=[]
    for row in read(out/'comparison.json')['cases']:
        key=row['case']+'-'+row['mode'];variants={}
        for version,label in [('reference','Previous reference offsets'),('context','Preserve source bone motion')]:
            variants[version]=dict(label=label,path=key+'/'+version+'/character.glb',metrics=verified[row['case'],row['mode'],version])
        original=read(ROOT/'reports/rig-jobs'/row['source_job']/'result.json')
        cases.append(dict(id=key,label=row['case']+' · '+('raw generated input' if row['mode']=='raw' else 'previous pose-fitted input'),frames=row['frames'],root_node=row['root_node'],camera_height_m=.65 if row['case'].startswith('jump') else .9,variants=variants,status='Source non-pelvis translations and unmapped helper motion are preserved. Raw generation can still miss boundary poses; pose-fitted inputs come from the previous experimental correction. Floor, contact and semantic quality remain unapproved.',audit='verification.json',package='http://127.0.0.1:8768'+original['package'],studio='http://127.0.0.1:8768/studio?rig_job=20260927-004526-f9764f83'))
    save(out/'review.json',dict(cases=cases,quality_approved=False))
    page=(ROOT/'scripts/clearance-review.html').read_text(encoding='utf8')
    page=page.replace('Strep · Surface clearance study','Strep · Preserve source bone motion').replace('Surface clearance on your character','Keep the source character’s bone motion')
    page=page.replace('Same generated motion, different correction objectives. Compare foot clearance and sliding together. Failed raw pose guides and original frames outside the editable section remain unchanged.','Compare the same generated poses with reference offsets or the source clip’s animated bone translations and helper motion. This transfer fix is now used by prompt-based clip editing.')
    page=page.replace("key==='candidate'","key==='context'")
    start=page.index("const rows=[")
    end=page.index(";$('metrics')",start)
    page=page[:start]+"const rows=[['Source non-root translation error',v=>(v.metrics.nonroot_translation_error_m*1000).toFixed(6)+' mm'],['Unmapped local-transform error',v=>v.metrics.unmapped_local_transform_error.toExponential(2)],['Unblended anchor position error',v=>(v.metrics.unblended_anchor_position_error_m*1000).toFixed(3)+' mm'],['Whole-clip floor depth',v=>mm(v.metrics.whole_floor_m)],['Editable-section floor depth',v=>mm(v.metrics.editable_floor_m)],['Between-frame floor depth',v=>mm(v.metrics.half_floor_m)],['Largest adjacent joint rotation',v=>v.metrics.joint_step_max_degrees.toFixed(2)+'°']]"+page[end:]
    page=page.replace('Support-speed measurements use model predictions and foot-region centroids; they are unconfirmed and can contain very few samples. A lower floor error alone does not establish realistic motion.','Preservation is measured in local bone transforms. Anchor positions are measured before the splice restores boundary frames. This fixes lost source detail; it does not certify generated actions or physical contact.')
    page=page.replace('Case package','Original assets and licenses').replace('Original in Studio','Fresh Studio edit')
    page=page.replace('../godot-rig-clearance-v3/verification.json','../godot-context-transfer-v1/verification.json')
    page=page.replace('Original character licenses and source files are retained in each case package. Grey material is preview-only. No independent animator approval.','Original-asset links contain the source authoring packages and licenses. Current GLB downloads contain the displayed comparison stage. The fresh Studio edit has its own complete authoring package. Grey material is preview-only.')
    (out/'viewer.html').write_text(page,encoding='utf8')


if __name__=='__main__':build()
