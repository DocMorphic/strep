"""Same-frame matched trajectory study viewer with explicit target overlays."""
from strep import ROOT,read,save


def build(allow_partial=False):
    out=ROOT/'reports/trajectory-fit-v1';design=read(out/'design.json');cases=[]
    partial=not (out/'verification.json').exists()
    if partial:
        if not allow_partial:raise ValueError('Full study verification is not complete')
        data=[]
        for case in design['cases']:
            for mode in design['modes']:
                path=out/case/mode/'trajectory-verification.json'
                if path.exists():data.append(dict(read(path),case=case))
        save(out/'preview-verification.json',dict(cases=data,study_complete=False,quality_approved=False))
    else:data=read(out/'verification.json')['cases']
    for case in read(out/'design.json')['cases']:
        rows={r['mode']:r for r in data if r['case']==case}
        if set(rows)!=set(design['modes']):
            if partial:continue
            raise ValueError('Missing matched fit for '+case)
        report=read(out/case/'clearance/input/report.json');job=read(out/case/'clearance/request.json')['job']
        original=read(ROOT/'reports/rig-jobs'/job/'result.json')
        variants={}
        for key,label,mode,stage in [('input','Before correction','clearance','input'),('clearance','Surface clearance','clearance','candidate'),('candidate','Support + trajectory','trajectory','candidate')]:
            metrics=rows[mode]['metrics'][stage]
            variants[key]=dict(label=label,path=f'{case}/{mode}/{stage}/character.glb',metrics=metrics,support_tracks=metrics['contacts'])
        cases.append(dict(id=case,label=case,frames=report['frames'],root_node=report['root_node'],camera_height_m=.65 if case.startswith('jump') else .9,variants=variants,status='Experimental comparison. Support targets are unconfirmed model-derived drafts. Fixed source frames stay unchanged; floor, contact and action failures are reported. No production default or quality approval.',audit='verification.json',package='http://127.0.0.1:8768'+original['package'],studio='http://127.0.0.1:8768/studio?rig_job='+job))
    if not cases:raise ValueError('No verified matched comparison is ready')
    if partial:
        for case in cases:
            case['audit']='preview-verification.json'
            case['status']='Study still running: this matched case is verified; other cases and engine checks are pending. '+case['status']
    save(out/'review.json',dict(cases=cases,study_complete=not partial,quality_approved=False))
    page=(ROOT/'scripts/clearance-review.html').read_text(encoding='utf8')
    page=page.replace('Strep · Surface clearance study','Strep · Contact and trajectory fit').replace('Surface clearance on your character','Contact and motion smoothness together')
    page=page.replace('Same generated motion, different correction objectives. Compare foot clearance and sliding together. Failed raw pose guides and original frames outside the editable section remain unchanged.','Matched source-preserving inputs, fitted with either surface clearance or support targets plus motion acceleration. Compare the same frame across stages. Orange markers are requested support targets; blue markers are measured patch centers.')
    start=page.index('const rows=[');end=page.index(";$('metrics')",start)
    rows="""const rows=[['Whole-clip floor depth',v=>mm(v.metrics.floor.floor_depth_max_m)],['Editable floor depth',v=>mm(v.metrics.floor.editable_floor_depth_max_m)],['Editable between-frame floor depth',v=>mm(v.metrics.floor.editable_half_frame_floor_depth_max_m)],['Left predicted-foot speed p95',v=>speed(v.metrics.floor.feet.Left.predicted_support_horizontal_speed_p95_m_s)],['Right predicted-foot speed p95',v=>speed(v.metrics.floor.feet.Right.predicted_support_horizontal_speed_p95_m_s)],['Largest adjacent joint rotation',v=>v.metrics.floor.local_rotation_step_max_degrees.toFixed(2)+'°'],['Editable angular acceleration p95',v=>v.metrics.editable_angular_acceleration_rad_s2.p95.toFixed(1)+' rad/s²'],['Editable root acceleration p95',v=>v.metrics.editable_root_acceleration_m_s2.p95.toFixed(1)+' m/s²'],['Maximum draft support error',v=>mm(Math.max(0,...v.metrics.contacts.map(c=>c.error_m.maximum)))]]"""
    page=page[:start]+rows+page[end:]
    page=page.replace('Support-speed measurements use model predictions and foot-region centroids; they are unconfirmed and can contain very few samples. A lower floor error alone does not establish realistic motion.','Draft support patches and intervals are unconfirmed. Orange and blue contact markers appear only during each declared interval. Displayed foot speeds use the same inherited prediction masks in every stage. Numerical improvements do not establish action correctness.')
    page=page.replace('Case package','Original assets and licenses').replace('../godot-rig-clearance-v3/verification.json','../godot-trajectory-fit-v1/verification.json')
    if partial:
        page=page.replace('<a href="export-validation.json">glTF validation</a>','<span>glTF validation pending</span>')
        page=page.replace('<a href="../godot-trajectory-fit-v1/verification.json">Godot verification</a>','<span>Godot verification pending</span>')
    page=page.replace('Original character licenses and source files are retained in each case package. Grey material is preview-only. No independent animator approval.','Original authoring packages retain character licenses and raw motion. Current GLB links contain the selected comparison stage. Grey material is preview-only. No independent animator approval.')
    marker="""
const contactGroup=new THREE.Group();scene.add(contactGroup);const contactMarkers=[];
function updateContacts(f){
 const tracks=item.variants[$('stage').value].support_tracks,active=tracks.filter(c=>c.start_frame<=f&&f<c.end_frame_exclusive);
 while(contactMarkers.length<active.length){const target=new THREE.Mesh(new THREE.SphereGeometry(.014,12,8),new THREE.MeshBasicMaterial({color:0xf4a322,depthTest:false})),observed=new THREE.Mesh(new THREE.SphereGeometry(.010,12,8),new THREE.MeshBasicMaterial({color:0x167aff,depthTest:false})),line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]),new THREE.LineBasicMaterial({color:0xf4a322,depthTest:false}));for(const n of [target,observed,line]){n.renderOrder=10;contactGroup.add(n);}contactMarkers.push({target,observed,line});}
 contactMarkers.forEach((m,i)=>{const c=active[i];for(const n of [m.target,m.observed,m.line])n.visible=!!c;if(!c)return;const actual=c.positions_m[f-c.start_frame];m.target.position.fromArray(c.target_position_m);m.observed.position.fromArray(actual);const points=m.line.geometry.attributes.position;points.setXYZ(0,...c.target_position_m);points.setXYZ(1,...actual);points.needsUpdate=true;m.line.geometry.computeBoundingSphere();});
}
"""
    page=page.replace('function pause()',marker+'\nfunction pause()').replace("previousRoot=p;$('frame')","previousRoot=p;updateContacts(f);$('frame')")
    (out/'viewer.html').write_text(page,encoding='utf8')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--partial',action='store_true')
    build(parser.parse_args().partial)
