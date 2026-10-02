export function createNativeSupportEditor({getContext,prefix='nativeSupport',onNativeCandidate=null,document=globalThis.document,fetch=globalThis.fetch,Option=globalThis.Option,storage=globalThis.localStorage,MutationObserver=globalThis.MutationObserver}={}){
 const el=id=>document.getElementById(prefix+id),panel=el('Panel');
 const roles=['LeftLeg','LeftShin','LeftFoot','RightLeg','RightShin','RightFoot'];
 let binding=null,spec=null,epoch=0,revision=0,pending=null,applying=false,jobs=[],mapping=new Map(),refreshEpoch=0;
 const clone=v=>JSON.parse(JSON.stringify(v));
 const api=async(url,body)=>{const r=await fetch(url,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;};
 const safe=fn=>async()=>{try{await fn();}catch(e){el('Status').textContent=e.message;}};
 function unload(){el('Frame').removeAttribute('src');el('Frame').hidden=true;}
 function methodState(){el('Refine').disabled=el('JointSearch').checked;el('JointSearch').disabled=el('Refine').checked;}
 function reset(){++epoch;++revision;binding=null;spec=null;el('Fields').disabled=true;el('PrepareRig').checked=false;el('Refine').checked=false;el('JointSearch').checked=false;methodState();el('PrepareRig').disabled=true;el('Preparation').hidden=true;el('Binding').textContent='No clip selected.';unload();}
 function key(){return 'strep:native-support:'+binding.glb_sha256;}
 function persist(){revision++;if(!binding||!spec)return;try{storage?.setItem(key(),JSON.stringify(spec));}catch{el('Status').textContent='Browser storage is full. The draft is still usable; submitting saves a snapshot.';}}
 function numeric(id){const text=String(el(id).value).trim(),n=Number(text);if(!text||!Number.isFinite(n))throw Error('Enter a finite '+id+' value');return n;}
 function syncMapping(){for(const role of roles){const value=mapping.get(role).value;if(value==='')delete spec.mapping[role];else spec.mapping[role]=Number(value);}persist();clock();}
 function clock(){
  const foot=el('Foot').value,side=foot.slice(0,-4),joints=['Leg','Shin','Foot'].map(n=>binding.joints.find(j=>j.node===spec.mapping[side+n]));
  const valid=joints.every(j=>j&&j.interpolation==='LINEAR'&&j.rotation_clock===joints[0].rotation_clock)&&joints[1]?.parent===joints[0]?.node&&joints[2]?.parent===joints[1]?.node;
  const times=valid?binding.clocks.find(c=>c.id===joints[0].rotation_clock)?.times_s:[];
  for(const id of ['First','Last']){const old=el(id).value;el(id).replaceChildren(...(times||[]).map((t,i)=>new Option(`${i} · ${t.toPrecision(9)} s`,String(i))));if(old!==''&&Number(old)<(times||[]).length)el(id).value=old;else if(id==='Last'&&times?.length)el(id).value=String(times.length-1);}
  if(!valid)el('Status').textContent='Map a direct thigh, knee and foot chain with a shared LINEAR native rotation clock.';
 }
 function intervals(){el('Intervals').replaceChildren();for(const r of spec.supports){const row=document.createElement('div'),text=document.createElement('span'),edit=document.createElement('button'),remove=document.createElement('button');row.className='rig-contact-row';text.textContent=`${r.id} · ${r.foot} · ${r.stance_s.join('–')} s · keys ${r.edit_keys.join('–')}`;edit.className=remove.className='btn';edit.type=remove.type='button';edit.textContent='Edit';remove.textContent='Remove';edit.onclick=()=>{el('Name').value=r.id;el('Foot').value=r.foot;clock();el('Start').value=r.stance_s[0];el('End').value=r.stance_s[1];el('First').value=String(r.edit_keys[0]);el('Last').value=String(r.edit_keys[1]);['NX','NY','NZ'].forEach((id,i)=>el(id).value=r.plane.normal_xyz[i]);el('Plane').value=r.plane.offset_m;for(const[id,k]of [['Clearance','clearance_m'],['Gap','maximum_gap_m'],['Displacement','maximum_displacement_m']])el(id).value=r[k]*1000;el('Angle').value=r.maximum_angle_degrees;};remove.onclick=()=>{spec.supports=spec.supports.filter(s=>s.id!==r.id);persist();intervals();};row.append(text,edit,remove);el('Intervals').append(row);}}
 async function bind(){
  reset();const context=getContext(),job=context.job,variant=context.variant;
  if(!job?.id||!['input','transfer','corrected','native_review'].includes(variant))throw Error(variant==='native_review'?'Build the selected native candidate preview first.':'Choose a saved character motion result and version first.');
  const token=epoch;el('Binding').textContent='Checking selected clip and native rotation clocks…';
  const data=await api(`/api/native-support-source?job=${encodeURIComponent(job.id)}&variant=${encodeURIComponent(variant)}`);
  const current=getContext();if(token!==epoch||current.job?.id!==job.id||current.variant!==variant)return;
  binding=data;spec={schema:'strep-native-support-v1',glb_sha256:data.glb_sha256,animation_index:0,duration_s:data.duration_s,root_node:data.root_node,mapping:clone(data.mapping),supports:[]};
  const preparation=data.rigid_preparation;el('Preparation').hidden=!preparation||(preparation.eligible&&!preparation.static_node_changes);el('PrepareRig').disabled=!preparation?.eligible||!preparation.static_node_changes;el('PreparationHint').textContent=preparation?.eligible?'This rig has tiny scale differences. Preparation creates a separate version, measures the mesh change and keeps your original clip.':'This rig needs a separate conversion before rigid foot editing. Tiny-scale preparation is unavailable.';
  try{const saved=JSON.parse(storage?.getItem(key())||'null');if(saved?.schema===spec.schema&&saved.glb_sha256===spec.glb_sha256&&saved.duration_s===spec.duration_s&&saved.root_node===spec.root_node&&Array.isArray(saved.supports)&&saved.mapping&&typeof saved.mapping==='object')spec=saved;}catch{}
  mapping=new Map();el('Mapping').replaceChildren();for(const role of roles){const label=document.createElement('label'),select=document.createElement('select');label.textContent=role.replace('Leg',' thigh').replace('Shin',' knee').replace('Foot',' foot');select.setAttribute('aria-label','Native support '+role);select.replaceChildren(new Option('Unmapped',''),...data.joints.map(j=>new Option(`${j.name||'Joint'} · ${j.node}`,String(j.node))));select.value=spec.mapping[role]===undefined?'':String(spec.mapping[role]);select.onchange=syncMapping;mapping.set(role,select);label.append(select);el('Mapping').append(label);}
  el('Start').value=data.duration_s*.4;el('End').value=data.duration_s*.6;clock();intervals();el('Fields').disabled=!!pending;el('Binding').textContent=`${data.label} · ${variant} · ${data.duration_s.toPrecision(9)} s · ${data.glb_sha256.slice(0,12)}`;
  el('Status').textContent='Edit the draft, then try correction. These are the selected exported GLB’s keys; a prepared rough clip may already have been resampled.';
 }
 el('Bind').onclick=safe(bind);el('Foot').onchange=()=>{revision++;clock();};
 el('PrepareRig').onchange=()=>{revision++;};
 el('Refine').onchange=()=>{revision++;methodState();};
 el('JointSearch').onchange=()=>{revision++;methodState();};
 el('Add').onclick=safe(async()=>{
  if(!spec)throw Error('Load a clip first');
  const id=el('Name').value.trim();if(!/^[A-Za-z0-9_-]{1,64}$/.test(id))throw Error('Use a short interval name with letters, digits, underscores or hyphens.');
  const r={id,foot:el('Foot').value,stance_s:[numeric('Start'),numeric('End')],edit_keys:[numeric('First'),numeric('Last')],plane:{normal_xyz:['NX','NY','NZ'].map(numeric),offset_m:numeric('Plane')},clearance_m:numeric('Clearance')/1000,maximum_gap_m:numeric('Gap')/1000,maximum_displacement_m:numeric('Displacement')/1000,maximum_angle_degrees:numeric('Angle')};
  if(r.stance_s[0]>=r.stance_s[1]||r.stance_s[0]<0||r.stance_s[1]>spec.duration_s)throw Error('Choose an increasing stance within the clip.');
  if(r.edit_keys.some(k=>!Number.isInteger(k))||r.edit_keys[1]-r.edit_keys[0]<4)throw Error('Choose boundary keys with at least three interior keys.');
  spec.supports=spec.supports.filter(s=>s.id!==id);spec.supports.push(r);persist();intervals();el('Status').textContent='Interval saved in this draft. Server validation checks the full mapping, timing and hard limits.';
 });
 el('Clear').onclick=()=>{if(spec){spec.supports=[];persist();intervals();}};
 async function refresh(){
  const serial=++refreshEpoch,data=await api('/api/native-support-jobs');if(serial!==refreshEpoch)return data;const selected=el('Jobs').value,oldReview=jobs.find(j=>j.id===selected)?.review?.result_sha256;jobs=data.jobs;
  if(el('Frame').src&&oldReview!==jobs.find(j=>j.id===selected)?.review?.result_sha256)unload();
  el('Jobs').replaceChildren(...jobs.map(j=>new Option(`${j.id} · ${j.status}${j.review?.retained_input?' · input retained':''}`,j.id)));if(jobs.some(j=>j.id===selected))el('Jobs').value=selected;
  el('Jobs').disabled=!jobs.length;el('Review').disabled=!jobs.find(j=>j.id===el('Jobs').value)?.review;
  if(pending){const j=jobs.find(j=>j.id===pending);if(j&&['complete','failed'].includes(j.status)){pending=null;el('Fields').disabled=!binding;el('Jobs').value=j.id;el('Review').disabled=!j.review;el('Status').textContent=j.status==='failed'?'Support job failed: '+j.error:j.review.retained_input?(j.review.preparation?'Prepared input retained: ':'Input retained: ')+j.review.retention_reason+'. Failed proposals remain available.':'Candidate met the sampled support and source-rate screens. Naturalness and other release checks remain unapproved.';}}
  nativeChoice();return data;
 }
 el('Fit').onclick=safe(async()=>{
  if(!binding||!spec?.supports.length)throw Error('Add a stance interval first.');
  const current=getContext();if(current.job?.id!==binding.source_job||current.variant!==binding.variant)throw Error('Selected clip changed. Load it again before submitting.');
  if(pending)throw Error('A native support job is already running.');
  const token=epoch,draft=revision,body={source_job:binding.source_job,variant:binding.variant,spec:clone(spec)};
  if(el('PrepareRig').checked){if(el('PrepareRig').disabled)throw Error('Rig preparation is unavailable for this source.');body.prepare_rigid_input=true;}
  if(el('Refine').checked&&el('JointSearch').checked)throw Error('Choose one support proposal method');
  if(el('Refine').checked)body.sampled_support_repair=true;
  if(el('JointSearch').checked)body.joint_source_rate_search=true;
  el('Fields').disabled=true;try{const job=await api('/api/native-support-edits',body);pending=job.id;if(token===epoch&&draft===revision)el('Status').textContent='Native correction started; source and draft are frozen. A completed fit can retain the input.';await refresh();}finally{el('Fields').disabled=!!pending||!binding;}
 });
 function nativeChoice(){const report=jobs.find(j=>j.id===el('Jobs').value)?.review?.native_review_candidate;el('UseCorrection').hidden=!onNativeCandidate;el('UseCorrection').disabled=!onNativeCandidate||!report||!!pending||applying;return report;}
 el('UseCorrection').onclick=safe(async()=>{if(pending||applying)throw Error('Wait for the current support operation');const report=nativeChoice();if(!report||!onNativeCandidate)throw Error('Choose a completed native support result');applying=true;nativeChoice();try{await onNativeCandidate(clone(report));}finally{applying=false;nativeChoice();}});
 el('Refresh').onclick=safe(refresh);el('Jobs').onchange=()=>{unload();el('Review').disabled=!jobs.find(j=>j.id===el('Jobs').value)?.review;nativeChoice();};
 el('Review').onclick=()=>{const job=jobs.find(j=>j.id===el('Jobs').value);if(!panel.open||!job?.review)return;el('Frame').src=`/native-support-viewer.html?id=${encodeURIComponent(job.id)}&result=${job.review.result_sha256}`;el('Frame').hidden=false;};
 panel.addEventListener('toggle',()=>{if(panel.open)void safe(refresh)();else{++epoch;unload();}});
 const owner=panel.closest?.('.window');if(owner&&MutationObserver)new MutationObserver(()=>{if(owner.hidden)el('Frame').contentWindow?.postMessage('strep-native-pause',globalThis.location.origin);}).observe(owner,{attributes:true,attributeFilter:['hidden']});
 nativeChoice();
 const timer=globalThis.setInterval?.(()=>{if(pending)void safe(refresh)();},2500);
 return {reset,bind,refresh,dispose(){globalThis.clearInterval?.(timer);reset();}};
}
