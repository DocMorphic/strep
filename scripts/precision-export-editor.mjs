const clone=x=>structuredClone(x);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const job=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const key=x=>JSON.stringify(x);
export function precisionRequest(binding,kind,id){
 if(!['scene','game'].includes(kind)||!job(id)||binding?.source?.kind!==kind||binding?.source?.job!==id||!hash(binding.source.result_sha256)||!hash(binding.package_sha256)||!hash(binding.engine_sha256)||!hash(binding.source_clock_sha256)||binding.original_selected!==true||binding.quality_approved!==false||binding.release_approved!==false)throw Error('Bind this exact completed source package first.');
 return {schema:'strep-studio-precision-export-v1',source:clone(binding.source)};
}
export function precisionDownloads(value){
 if(!job(value?.id)||!Array.isArray(value.downloads))throw Error('Invalid precision result.');
 if(value.status!=='complete'){if(value.downloads.length)throw Error('Partial jobs cannot expose complete assets.');return [];}
 const flags=['studio_selection_changed','quality_approved','release_approved','training_admitted','physics_verified','gpu_render_checked','continuous_collision_certified'];
 if(value.schema!=='strep-studio-precision-export-v1'||value.original_selected!==true||flags.some(k=>value[k]!==false)||!hash(value.result_sha256)||!Number.isInteger(value.actor_count)||value.actor_count<1||value.actor_count>8||typeof value.checked_package_available!=='boolean')throw Error('Typed unapproved precision evidence required.');
 if(['original_skin_samples_passed','scene_samples_passed','inherited_surface_checked','root_event_tracks_included'].some(k=>typeof value[k]!=='boolean'))throw Error('Explicit precision check decisions required.');
 const names=['result.json','original-assets.zip','fidelity.json','fidelity.npz'];
 for(let i=0;i<value.actor_count;i++)names.push(`actors/${i}.glb`,`actors/${i}.glb.weights.json`);
 if(value.checked_package_available)names.push('checked-assets.zip');
 const urls=new Set(names.map(n=>`/files/precision-export-jobs/${value.id}/${n}`));
 if(value.downloads.length!==urls.size||new Set(value.downloads.map(d=>d.url)).size!==urls.size||value.downloads.some(d=>!urls.has(d.url)||!hash(d.sha256)||typeof d.label!=='string'))throw Error('Complete bound precision downloads required.');
 if(value.checked_package_available&&(value.original_skin_samples_passed!==true||value.scene_samples_passed!==true||value.inherited_surface_checked&&value.inherited_surface_samples_passed!==true||value.root_event_tracks_included&&(value.root_samples_passed!==true||value.event_dispatch_verified!==true)))throw Error('Failed checks cannot expose a checked ZIP.');
 return clone(value.downloads);
}
export function createPrecisionExportEditor({document=globalThis.document,api,post}={}){
 const el=n=>document.getElementById('precisionExport'+n);
 let binding=null,serial=0,busy=false;
 const status=t=>{el('Status').textContent=t;};
 const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 const clear=()=>{binding=null;serial++;el('SourceInfo').replaceChildren();};
 const options=(name,rows)=>{const old=el(name).value;el(name).replaceChildren(...rows.map(r=>{const o=document.createElement('option');o.value=r.id;o.textContent=`${r.id} · ${r.status}`;return o;}));if(rows.some(r=>r.id===old))el(name).value=old;};
 async function refresh(){clear();const kind=el('Kind').value;const sources=await api(kind==='game'?'/api/native-scene-game-jobs':'/api/native-scene-jobs');if(kind!==el('Kind').value)return;options('Source',sources.jobs.filter(r=>r.status==='complete'));const jobs=await api('/api/precision-export-jobs');options('Jobs',jobs.jobs);status('Choose a completed package and bind it.');}
 async function bind(){clear();const token=serial,kind=el('Kind').value,id=el('Source').value;if(!job(id))throw Error('Choose a completed scene or game package.');const m=await api(`/api/precision-export-source?kind=${kind}&id=${encodeURIComponent(id)}`);if(token!==serial||kind!==el('Kind').value||id!==el('Source').value)throw Error('Source selection changed.');precisionRequest(m,kind,id);binding=clone(m);const p=document.createElement('p');p.textContent=`${m.actor_count} characters · original package retained · original skin reference preserved${kind==='game'?' · root and event tracks will be regenerated':''}.`;el('SourceInfo').append(p);status('Bound. Build a separate export and review its measured results.');}
 el('Kind').onchange=clear;el('Source').onchange=clear;el('Refresh').onclick=guard(refresh);el('Bind').onclick=guard(bind);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this submission.');const before=binding,kind=el('Kind').value,id=el('Source').value,payload=precisionRequest(before,kind,id);busy=true;el('Build').disabled=true;try{const m=await api(`/api/precision-export-source?kind=${kind}&id=${encodeURIComponent(id)}`);if(before!==binding||key(m)!==key(before)||key(payload)!==key(precisionRequest(binding,el('Kind').value,el('Source').value)))throw Error('Source changed; bind again.');const result=await post('/api/precision-export-assets',payload);if(!job(result.id))throw Error('Invalid precision receipt.');const jobs=await api('/api/precision-export-jobs');options('Jobs',jobs.jobs);el('Jobs').value=result.id;status('Export started. Originals remain selected; refresh results when it finishes.');}finally{busy=false;el('Build').disabled=false;}});
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value,token=++serial;if(!job(id))throw Error('Choose an export result.');el('Results').replaceChildren();const m=await api(`/api/precision-export-review?id=${encodeURIComponent(id)}`);if(token!==serial||id!==el('Jobs').value||m.id!==id)throw Error('Export selection changed.');const files=precisionDownloads(m),p=document.createElement('p');p.textContent=m.status==='complete'?`Original skin ${m.original_skin_samples_passed?'pass':'fail'} · scene ${m.scene_samples_passed?'pass':'fail'}. ${m.checked_package_available?'Separate checked package available.':'Failed conditions retained; no checked package.'} Motion review is still required.`:`${m.status}: ${m.stage||m.error||'waiting'}`;el('Results').append(p);for(const d of files){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}status(p.textContent);});
 return {refresh,bind};
}
