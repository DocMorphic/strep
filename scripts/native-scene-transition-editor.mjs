const clone=x=>structuredClone(x),hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),name=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const namespace='native-scene-transition-jobs';
export function stagedTransition(review){
 if(review?.status!=='complete'||!name(review.id)||!hash(review.result_sha256)||review.staging_conditions_pass!==true||review.original_selected!==true||
    ['studio_selection_changed','quality_approved','training_admitted','release_approved','engine_playback_verified'].some(k=>review[k]!==false))throw Error('A verified separate transition draft is required.');
 const draft=clone(review.draft),game=clone(review.game_tracks);
 if(draft?.schema!=='strep-studio-native-scene-v1'||game?.schema!=='strep-native-scene-game-tracks-v1'||draft.object_edit!==null||!Array.isArray(review.downloads))throw Error('Transition draft or timing request changed.');
 const names=new Set(),allowed=new Set(['result.json','stage-draft.json','stage-game-tracks.json','transition/result.json','transition/events.json','transition/contacts.json','transition/roots.json']);
 for(const [actor,entry]of Object.entries(draft.scene.actors)){
  const file=`transition/actors/${actor}.glb`;allowed.add(file);
  if(!/^[A-Za-z0-9_-]{1,64}$/.test(actor)||entry.glb!==`/files/${namespace}/${review.id}/${file}`||!hash(entry.sha256)||!Number.isInteger(entry.animation_index)||!Number.isInteger(game.actors?.[actor]?.root_node))throw Error('Source-bound transition clip changed.');
 }
 if(Object.keys(game.actors).sort().join()!==Object.keys(draft.scene.actors).sort().join()||!Array.isArray(game.markers)||game.markers.some(m=>m.confirmed!==false))throw Error('All transition timing needs review.');
 for(const d of review.downloads){if(!allowed.has(d.label)||names.has(d.label)||!hash(d.sha256)||d.url!==`/files/${namespace}/${review.id}/${d.label}`)throw Error('Transition download changed.');names.add(d.label);}
 if(names.size!==allowed.size)throw Error('Complete transition downloads required.');
 for(const [actor,a]of Object.entries(draft.scene.actors))if(review.downloads.find(d=>d.label===`transition/actors/${actor}.glb`).sha256!==a.sha256)throw Error('Transition actor receipt changed.');
 return {draft,game,downloads:clone(review.downloads)};
}

export function createNativeSceneTransitionEditor({document=globalThis.document,api,post,setDraft,queueGameTracks}={}){
 const el=n=>document.getElementById('nativeSceneTransition'+n);let inspected=null,review=null,epoch=0,busy=false;
 const status=t=>{el('Status').textContent=t;},source=()=>({folder:el('Folder').value.trim(),result_sha256:el('Hash').value.trim()});
 const key=x=>JSON.stringify(x);const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 const invalidate=()=>{epoch++;inspected=null;review=null;el('Stage').disabled=true;el('Apply').disabled=true;};el('Folder').oninput=invalidate;el('Hash').oninput=invalidate;
 el('Inspect').onclick=guard(async()=>{const s=source(),token=++epoch;invalidate();const current=epoch,r=await post('/api/native-scene-transition-inspect',s);
  if(current!==epoch||key(source())!==key(s))throw Error('Transition selection changed; inspect again.');
  if(key(r.source)!==key(s)||r.original_selected!==true||r.quality_approved!==false||r.release_approved!==false||!Array.isArray(r.times_s))throw Error('Transition inspection changed.');
  inspected=clone(r);el('Floor').checked=r.floor!==null;if(r.floor){el('FloorHeight').value=String(r.floor.height_m);el('Penetration').value=String(r.floor.maximum_penetration_m*1000);}
  el('Stage').disabled=false;status(`${r.actors.length} characters · ${r.objects.length} props · ${r.duration_s} s. Source checks: ${Object.entries(r.checks).map(([n,v])=>`${n} ${v?'pass':'fail'}`).join(', ')}. ${r.timeline_mapping.length} original annotation records retained.`);
 });
 el('Stage').onclick=guard(async()=>{if(busy||!inspected||key(inspected.source)!==key(source()))throw Error('Inspect the intended saved transition first.');busy=true;el('Stage').disabled=true;const token=epoch;
  try{const number=(id,lo,hi)=>{const text=el(id).value.trim(),v=Number(text);if(!text||!Number.isFinite(v)||v<lo||v>hi)throw Error('Invalid '+id);return v;};
   const geometry={clock:{mode:'explicit',times_s:clone(inspected.times_s)},limits:{penetration_m:number('Penetration',0,100)/1000,depth_resolution_m:1e-6,surface_tolerance_m:1e-8},planes:el('Floor').checked?{floor:{normal_world:[0,1,0],offset_m:number('FloorHeight',-100,100)}}:{}};
   const r=await post('/api/native-scene-transition-stage',{schema:'strep-studio-native-scene-transition-v1',source:clone(inspected.source),geometry});
   if(token!==epoch||key(source())!==key(inspected.source))throw Error('Selection changed; the separate saved stage remains available in its history.');
   const staged=stagedTransition(r);review=clone(r);el('Results').replaceChildren();const summary=document.createElement('p');summary.textContent=`Separate draft saved. Original transition conditions: ${r.source_conditions_pass?'pass':'fail'}. Marker timings require review. The current scene is still selected.`;el('Results').append(summary);
   for(const d of staged.downloads){const a=document.createElement('a');a.href=d.url;a.download='';a.className='btn';a.textContent=d.label;el('Results').append(a);}el('Apply').disabled=false;status(summary.textContent);
  }finally{busy=false;el('Stage').disabled=!inspected;}
 });
 el('Apply').onclick=guard(()=>{if(busy||!review)throw Error('Save a separate stage first.');const staged=stagedTransition(review);queueGameTracks({request:staged.game,actor_hashes:Object.fromEntries(Object.entries(staged.draft.scene.actors).map(([n,a])=>[n,{sha256:a.sha256,animation_index:a.animation_index}]))});setDraft(staged.draft);status('Transition staged in the scene editor. Build scene assets, then bind that completed scene in Root & gameplay tracks to load the unconfirmed markers.');});
 return {snapshot:()=>review?clone(review):null};
}
