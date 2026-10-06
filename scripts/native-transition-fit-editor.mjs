const clone=x=>structuredClone(x),key=x=>JSON.stringify(x),hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),name=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const prefix='/files/native-transition-fit-jobs/';
export function stagedBridgeCorrection(review){
 if(review?.status!=='complete'||!name(review.id)||!hash(review.result_sha256)||!hash(review.candidate_result_sha256)||review.original_selected!==true||review.native_roots_only!==true||
  ['studio_selection_changed','quality_approved','training_admitted','release_approved','engine_playback_verified'].some(k=>review[k]!==false))throw Error('A source-bound separate bridge candidate is required.');
 const draft=clone(review.draft),game=clone(review.game_tracks),request=review.authoring_request;
 if(draft?.schema!=='strep-studio-native-scene-v1'||draft.object_edit!==null||game?.schema!=='strep-native-scene-game-tracks-v1'||request?.schema!=='strep-studio-native-transition-fit-v1'||!Array.isArray(review.downloads)||!hash(request.source?.result_sha256))throw Error('Candidate scene or source request changed.');
 const expected=['stage-draft.json','stage-game-tracks.json','candidate/result.json','candidate/contacts-audit.json','candidate/geometry.json','candidate/fit/result.json','candidate/permissions.json','candidate/geometry-policy.json','candidate/fit/source-rate-caps.npz','candidate/tracks/root-motion.json','candidate/tracks/events.json'];
 for(const [i,[actor,a]]of Object.entries(draft.scene.actors).entries()){
  const file=`candidate/actors/${i}.glb`;expected.push(file);
  if(!/^[A-Za-z0-9_-]{1,64}$/.test(actor)||a.glb!==`${prefix}${review.id}/${file}`||!hash(a.sha256)||!Number.isInteger(a.animation_index)||a.animation_index<1||!Number.isInteger(review.original_animation_counts?.[actor])||a.animation_index!==review.original_animation_counts[actor]||!Number.isInteger(game.actors?.[actor]?.root_node))throw Error('Appended bridge clip binding changed.');
 }
 if(Object.keys(game.actors).sort().join()!==Object.keys(draft.scene.actors).sort().join()||!Array.isArray(game.markers)||game.markers.some(m=>m.confirmed!==false)||!review.checks||['native_motion_and_contacts','native_contact_audit','actor_transition_conditions','whole_scene_geometry'].some(k=>!(k in review.checks))||Object.keys(review.checks).some(k=>!['native_motion_and_contacts','native_contact_audit','actor_transition_conditions','whole_scene_geometry','inherited_shared_floor'].includes(k))||Object.values(review.checks).some(v=>typeof v!=='boolean')||typeof review.all_declared_samples_pass!=='boolean'||review.all_declared_samples_pass!==Object.values(review.checks).every(Boolean))throw Error('Candidate decisions or unconfirmed timings changed.');
 const seen=new Set();for(const d of review.downloads){if(!expected.includes(d.label)||seen.has(d.label)||!hash(d.sha256)||review.files_sha256?.[d.label]!==d.sha256||d.url!==`${prefix}${review.id}/${d.label}`)throw Error('Candidate download changed.');seen.add(d.label);}
 if(seen.size!==expected.length||Object.keys(review.files_sha256).length!==expected.length)throw Error('Complete bridge downloads required.');
 for(const [i,a]of Object.values(draft.scene.actors).entries())if(review.files_sha256[`candidate/actors/${i}.glb`]!==a.sha256)throw Error('Candidate character receipt changed.');
 if(review.candidate_binding?.folder!==`native-transition-fit-jobs/${review.id}/candidate`||review.candidate_binding.result_sha256!==review.candidate_result_sha256)throw Error('Continuation binding changed.');
 return {draft,game,downloads:clone(review.downloads)};
}
export function createNativeTransitionFitEditor({document=globalThis.document,api,post,getDraft,setDraft,queueGameTracks}={}){
 const el=n=>document.getElementById('nativeTransitionFit'+n);let inspected=null,selections={},tracks=[],review=null,epoch=0,busy=false,resume=null;
 const source=()=>({folder:el('Folder').value.trim(),result_sha256:el('Hash').value.trim()}),status=t=>{el('Status').textContent=t;};
 const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 const number=(id,lo,hi,integer=false)=>{const t=el(id).value.trim(),v=Number(t);if(!t||!Number.isFinite(v)||v<lo||v>hi||(integer&&!Number.isInteger(v)))throw Error('Invalid '+id);return v;};
 function options(id,values){el(id).replaceChildren(...values.map(([value,label])=>{const x=document.createElement('option');x.value=value;x.textContent=label;return x;}));}
 function channel(){return inspected?.actors[el('Actor').value]?.tracks[Number(el('Track').value)];}
 function showTracks(){const a=inspected?.actors[el('Actor').value];options('Track',(a?.tracks??[]).map((t,i)=>[String(i),`${t.name} · ${t.path}${t.eligible?'':' · '+t.reason}`]));const selected=selections[el('Actor').value];tracks=clone(selected?.tracks??[]);if(selected){el('Knots').value=selected.knots_s.join(', ');el('Protected').value=key(selected.protected_s);el('Displacement').value=String(selected.maximum_joint_displacement_m*1000);}el('Track').onchange();}
 function invalidate(){epoch++;inspected=null;selections={};tracks=[];review=null;resume=null;el('Build').disabled=true;el('Apply').disabled=true;}
 el('Folder').oninput=invalidate;el('Hash').oninput=invalidate;
 el('Track').onchange=()=>{const t=channel();el('Bound').value=t?.path==='translation'?'20':'5';el('Units').textContent=t?.path==='translation'?'Translation change limit in millimetres.':'Rotation change limit in degrees.';};el('Actor').onchange=showTracks;
 function summary(){el('Selections').replaceChildren();for(const [n,a]of Object.entries(selections)){const p=document.createElement('p');p.textContent=`${n}: ${a.tracks.length} channels, ${a.knots_s.length} control times, ${a.maximum_joint_displacement_m*1000} mm joint limit`;el('Selections').append(p);}}
 el('Inspect').onclick=guard(async()=>{if(busy)throw Error('Wait for this request.');invalidate();const token=epoch,s=source(),r=await post('/api/native-transition-fit-catalog',s);
  if(token!==epoch||key(source())!==key(s))throw Error('Transition selection changed; load again.');
  if(key(r.source)!==key(s)||r.schema!=='strep-studio-native-transition-fit-catalog-v1'||r.quality_approved!==false||r.release_approved!==false||!Array.isArray(r.bridge_interval_s)||r.bridge_interval_s.length!==2)throw Error('Transition catalog changed.');
  inspected=clone(r);const [a,b]=r.bridge_interval_s;el('Knots').value=[a,(a+b)/2,b].join(', ');options('Actor',Object.keys(r.actors).map(n=>[n,n]));showTracks();summary();el('Build').disabled=false;
  el('Bridge').textContent=`Editable bridge ${a}–${b} s. Its boundary motion remains protected.${r.floor?' The original whole-clip floor remains binding.':''}`;
  status('Source checks: '+Object.entries(r.source_checks).map(([n,v])=>`${n} ${v?'pass':'fail'}`).join(', '));
 });
 el('Add').onclick=guard(()=>{if(resume)throw Error('Continuation keeps its original channel bounds.');const t=channel();if(!t?.eligible)throw Error('Choose an eligible native bridge channel.');const max=number('Bound',.000001,t.path==='rotation'?45:220)/(t.path==='translation'?1000:1);const entry={node:t.node,path:t.path,maximum_change:max};tracks=tracks.filter(x=>x.node!==t.node||x.path!==t.path);tracks.push(entry);status(`${tracks.length} channels selected; save this character’s bounds.`);});
 el('SaveActor').onclick=guard(()=>{if(resume)throw Error('Continuation keeps its original bounds.');if(!inspected||!tracks.length)throw Error('Load a transition and select channels.');const knots=el('Knots').value.split(',').map(x=>Number(x.trim())),[a,b]=inspected.bridge_interval_s,protected_s=JSON.parse(el('Protected').value);
  if(knots.length<3||knots.length>12||knots[0]!==a||knots.at(-1)!==b||knots.some((v,i)=>!Number.isFinite(v)||(i&&v<=knots[i-1]))||!Array.isArray(protected_s))throw Error('Control times must be ordered inside the complete bridge.');
  selections[el('Actor').value]={window_s:[a,b],protected_s,knots_s:knots,tracks:clone(tracks),maximum_joint_displacement_m:number('Displacement',.001,220)/1000};summary();});
 el('RemoveActor').onclick=guard(()=>{if(resume)throw Error('Continuation keeps its original actor bounds.');delete selections[el('Actor').value];tracks=[];summary();});
 function request(){const label=el('Label').value.trim();if(!label||label.length>160)throw Error('Choose a variant name.');if(resume){const r=clone(resume.request);r.iterations=number('Iterations',1,16,true);r.label=el('Label').value.trim();r.resume_from=clone(resume.binding);return r;}
  if(!inspected||key(inspected.source)!==key(source())||!Object.keys(selections).length)throw Error('Load the intended transition and save character bounds.');
  const count=Object.values(selections).reduce((sum,a)=>sum+a.tracks.length*(a.knots_s.length-2)*3,0);if(count>96)throw Error('At most 96 complete control components.');
  const geometry={clock:{mode:'explicit',times_s:clone(inspected.times_s)},limits:{penetration_m:number('Penetration',0,100)/1000,depth_resolution_m:1e-6,surface_tolerance_m:1e-8},planes:inspected.floor?{floor:{normal_world:[0,1,0],offset_m:inspected.floor.height_m}}:{}};
  return {schema:'strep-studio-native-transition-fit-v1',source:clone(inspected.source),label,actors:clone(selections),geometry,iterations:number('Iterations',1,16,true),maximum_pose_vertex_queries:number('Budget',1,1000000,true),resume_from:null};
 }
 async function refresh(){const r=await api('/api/native-transition-fit-jobs');options('Jobs',r.jobs.map(j=>[j.id,`${j.id} · ${j.status}`]));return r;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this request.');const r=request();busy=true;el('Build').disabled=true;try{const job=await post('/api/native-transition-fits',r);await refresh();el('Jobs').value=job.id;status('Separate bridge correction started. Refresh and review it before applying.');}finally{busy=false;el('Build').disabled=!inspected&&!resume;}});
 el('Jobs').onchange=()=>{review=null;el('Apply').disabled=true;};
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value,token=epoch;if(!id)throw Error('Select a bridge correction.');review=null;el('Apply').disabled=true;const r=await api(`/api/native-transition-fit-review?id=${encodeURIComponent(id)}`);
  if(token!==epoch||el('Jobs').value!==id||r.id!==id)throw Error('Correction selection changed.');el('Results').replaceChildren();const p=document.createElement('p');p.textContent=r.status==='complete'?Object.entries(r.checks).map(([n,v])=>`${n}: ${v?'pass':'fail'}`).join(' · '):`${r.status}: ${r.stage??r.error??'waiting'}`;el('Results').append(p);status(p.textContent);
  if(r.status==='complete'){const staged=stagedBridgeCorrection(r);review=clone(r);for(const d of staged.downloads){const a=document.createElement('a');a.href=d.url;a.download='';a.className='btn';a.textContent=d.label;el('Results').append(a);}el('Apply').disabled=false;}
 });
 el('Resume').onclick=guard(()=>{if(!review||el('Jobs').value!==review.id)throw Error('Review a completed correction first.');stagedBridgeCorrection(review);resume={request:clone(review.authoring_request),binding:clone(review.candidate_binding)};selections=clone(resume.request.actors);el('Iterations').value='1';el('Label').value=resume.request.label;el('Build').disabled=false;summary();status('Original source epoch, permissions, geometry and query budget retained. Only iteration count and variant name may change.');});
 el('Apply').onclick=guard(async()=>{const before=review;if(busy||!before||el('Jobs').value!==before.id)throw Error('Review the selected candidate first.');const scene=key(getDraft()),token=epoch,updated=await api(`/api/native-transition-fit-review?id=${encodeURIComponent(before.id)}`);
  if(token!==epoch||review!==before||key(updated)!==key(before)||el('Jobs').value!==before.id||scene!==key(getDraft()))throw Error('Scene or candidate changed; review again.');
  const staged=stagedBridgeCorrection(updated);queueGameTracks({request:staged.game,actor_hashes:Object.fromEntries(Object.entries(staged.draft.scene.actors).map(([n,a])=>[n,{sha256:a.sha256,animation_index:a.animation_index}]))});setDraft(staged.draft);el('Apply').disabled=true;status('Reviewed candidate staged for further editing. Source failures remain recorded; build scene assets and review import and motion quality.');
 });
 return {request,refresh,snapshot:()=>review?clone(review):null};
}
