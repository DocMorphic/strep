const JOINTS=['LeftFoot','LeftToeBase','RightFoot','RightToeBase'];
export function intervals(values){const rows=[];let start=0;for(let end=1;end<=values.length;end++)if(end===values.length||values[end]!==values[start]){rows.push({start_frame:start,end_frame_exclusive:end,contact:values[start]});start=end;}return rows;}
export function annotate(values,start,end,state){if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||start>=end||end>values.length||![true,false,null].includes(state))throw Error('Choose a valid segment interval and state');const result=values.slice();result.fill(state,start,end);return result;}
export function createCorrectionReviewPanel({document=globalThis.document,fetch=globalThis.fetch,Option=globalThis.Option,createPlayer,MutationObserver=globalThis.MutationObserver,now=()=>new Date().toISOString()}={}){
 const el=id=>document.getElementById(id),panel=el('correctionReviewPanel');let packets=[],packet=null,selected=null,states=new Map(),serial=0,player=null,activePreview=null,playhead=0,saving=false,histories=new Map();
 const status=text=>{el('correctionReviewStatus').textContent=text;};
 const fields=['Decision','Split','CleanupSeconds','Notes'];
 const checks=['SemanticPass','QualityPass','ContactPass'];
 function state(){return selected&&states.get(selected.item_id);}
 function stop(){player?.pause();}
 async function request(url,body){const response=await fetch(url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'Review request failed');return data;}
 function capture(){const s=state();if(!s)return;for(const key of fields)s[key]=el('correctionReview'+key).value;for(const key of checks)s[key]=el('correction'+key).checked;for(const key of ['Name','Evidence','Obligations','Notes'])s['Rights'+key]=el('correctionRights'+key).value;s.RightsPermitted=el('correctionRightsPermitted').checked;}
 function renderContacts(){const s=state();if(!s)return;const known=s.contacts.flat().filter(v=>v!==null).length;el('correctionContactCoverage').textContent=`${known} / ${selected.frames*4} contact states marked.`;el('correctionReviewPack').disabled=saving||known!==selected.frames*4;const node=el('correctionContactIntervals');node.replaceChildren();for(let i=0;i<4;i++){const p=document.createElement('p');p.textContent=JOINTS[i]+': '+intervals(s.contacts[i]).map(r=>`${r.start_frame}â€“${r.end_frame_exclusive} ${r.contact===null?'unknown':r.contact?'planted':'free'}`).join(' Â· ');node.append(p);}el('correctionReviewProgress').textContent=`${[...states.values()].filter(s=>s.Decision!=='unreviewed').length} / ${packet.items.length} segment decisions recorded in this draft.`;}
 function recipe(){const value=structuredClone(selected.recipe);value.contacts=JOINTS.map((joint,i)=>({joint,intervals:intervals(state().contacts[i])}));return value;}
 function restore(){const s=state();for(const key of fields)el('correctionReview'+key).value=s[key];for(const key of checks)el('correction'+key).checked=s[key];for(const key of ['Name','Evidence','Obligations','Notes'])el('correctionRights'+key).value=s['Rights'+key];el('correctionRightsPermitted').checked=s.RightsPermitted;el('correctionPackStatus').textContent=s.pack?'Packed correction saved locally; review and permission remain separate.':'';renderContacts();}
 function blank(data){return {metadata:data,contacts:Array.from({length:4},()=>Array(data.frames).fill(null)),Decision:'unreviewed',Split:'',CleanupSeconds:'',Notes:'',SemanticPass:false,QualityPass:false,ContactPass:false,RightsName:'',RightsEvidence:'',RightsObligations:'',RightsNotes:'',RightsPermitted:false,pack:null,packKey:null,candidatePreview:null};}
 async function showPreview(version='original',token=++serial){
  stop();const data=version==='candidate'?state()?.candidatePreview:selected;
  if(!data){el('correctionPreviewVersion').value='original';status('Build the selected candidate preview first');return;}
  activePreview=data;el('correctionPreviewVersion').value=version;el('correctionPreviewScope').textContent=version==='original'?'Original reference geometry. Build or select the candidate preview to compare.':data.preview_scope;
  el('correctionReviewTime').min=data.preview_start_s;el('correctionReviewTime').max=data.preview_end_s;
  el('correctionReviewTime').value=data.preview_start_s;
  if(!player&&createPlayer)player=await createPlayer({canvas:el('correctionReviewCanvas'),onTime:t=>{
   if(!selected||!activePreview)return;
   playhead=Math.max(0,Math.min(selected.frames-1,Math.round((t-activePreview.preview_start_s)*30)));
   el('correctionReviewTime').value=t;el('correctionReviewClock').textContent=`Frame ${playhead} · ${t.toFixed(3)} s`;
  }});
  if(token!==serial||!panel.open)return;if(player)await player.load(data);
 }
 function install(data){
  selected=data;let s=states.get(data.item_id);
  if(!s||JSON.stringify(s.metadata.recipe.candidate_motion)!==JSON.stringify(data.recipe.candidate_motion)||s.metadata.recipe.candidate_start_frame!==data.recipe.candidate_start_frame){s=blank(data);states.set(data.item_id,s);}else s.metadata=data;
  el('correctionReviewItem').value=data.item_id;el('correctionReviewPrompt').textContent=data.prompt;
  el('correctionCandidatePath').value=data.candidate_relative;el('correctionCandidateStart').value=data.recipe.candidate_start_frame;
  el('correctionContactStart').value=0;el('correctionContactEnd').value=data.frames;
  const joint=el('correctionEditJoint').value,names=data.recipe.joint_names||[];
  el('correctionEditJoint').replaceChildren(...names.map(name=>new Option(name,name)));
  if(names.includes(joint))el('correctionEditJoint').value=joint;
  for(const [id,value] of [['Start',0],['Peak',Math.floor((data.frames-1)/2)],['End',data.frames-1]]){el('correctionEdit'+id).value=value;el('correctionEdit'+id).max=data.frames-1;}
  el('correctionEditApply').disabled=data.frames<3;
  el('correctionEditUndo').disabled=!(histories.get(data.item_id)?.length);
  el('correctionEditReport').textContent='';restore();
 }
 function previewMatches(data,selection){return data?.quality_approved===false&&data.training_admitted===false&&/^\/files\/native-correction-previews\/[A-Za-z0-9_-]+\/candidate\.glb$/.test(data.preview_url)&&/^[0-9a-f]{64}$/.test(data.preview_sha256)&&data.preview_start_s===0&&Object.keys(data.selection||{}).length===5&&['draft_id','draft_sha256','item_id','candidate_start_frame'].every(key=>data.selection[key]===selection[key])&&JSON.stringify(data.selection.candidate_motion)===JSON.stringify(selection.candidate_motion);}
 async function applyEdit(){
  if(saving||!selected)return;capture();stop();const previous=selected,s=state(),token=++serial;
  let payload;
  try{
   const number=id=>{const value=el(id).value;if(!value.trim()||!Number.isFinite(Number(value)))throw Error('Enter every edit vector component and frame key explicitly');return Number(value);};
   const edit={joint:el('correctionEditJoint').value,rotation_vector_degrees:['X','Y','Z'].map(axis=>number('correctionEditRotation'+axis)),root_offset_m:['X','Y','Z'].map(axis=>number('correctionEditRoot'+axis)),start_frame:number('correctionEditStart'),peak_frame:number('correctionEditPeak'),end_frame:number('correctionEditEnd')};
   if(![edit.start_frame,edit.peak_frame,edit.end_frame].every(Number.isInteger)||!(0<=edit.start_frame&&edit.start_frame<edit.peak_frame&&edit.peak_frame<edit.end_frame&&edit.end_frame<selected.frames))throw Error('Choose ordered start, interior peak and end frame keys');
   if(![...edit.rotation_vector_degrees,...edit.root_offset_m].some(v=>v!==0))throw Error('Enter a nonzero joint rotation or root offset');
   payload={draft_id:packet.draft_id,draft_sha256:packet.draft_sha256,item_id:selected.item_id,candidate_motion:structuredClone(selected.recipe.candidate_motion),candidate_start_frame:selected.recipe.candidate_start_frame,edit};
   saving=true;el('correctionReviewFields').disabled=true;status('Saving bounded native edit and checking its preview…');
   const data=await request('/api/correction-review-edit',payload);
   if(token!==serial||!panel.open||s!==state())return;
   const m=data.metadata,selection={draft_id:packet.draft_id,draft_sha256:packet.draft_sha256,item_id:previous.item_id,candidate_motion:data.candidate_motion,candidate_start_frame:0};
   if(JSON.stringify(data.selection)!==JSON.stringify(payload)||data.quality_approved!==false||data.training_admitted!==false||data.release_approved!==false||data.candidate_start_frame!==0||!m||m.item_id!==previous.item_id||m.draft_sha256!==packet.draft_sha256||m.frames!==previous.frames||m.quality_approved!==false||m.training_admitted!==false||!/^reports\/native-correction-edits\/[A-Za-z0-9_-]+\/candidate\.npz$/.test(m.candidate_relative)||JSON.stringify(m.recipe.candidate_motion)!==JSON.stringify(data.candidate_motion)||m.recipe.candidate_start_frame!==0||!previewMatches(data.preview,selection))throw Error('Native edit differs from its bound selection');
   if(!data.report?.measured||['joint_from_original_degrees','root_from_original_m','correction_step_degrees','root_correction_step_m'].some(key=>!Number.isFinite(data.report.measured[key])))throw Error('Native edit has no finite bound report');
   const history=histories.get(previous.item_id)||[];history.push(previous);histories.set(previous.item_id,history);
   install(m);state().candidatePreview=data.preview;
   const values=data.report.measured;
   el('correctionEditReport').textContent=`Saved candidate: ${m.candidate_relative}. Maximum original-relative joint offset ${values.joint_from_original_degrees.toFixed(3)}°, root offset ${values.root_from_original_m.toFixed(4)} m. Contact labels and review claims reset.`;
   await showPreview('candidate',token);
   if(token===serial&&panel.open)status('Native edit saved. Inspect the candidate and annotate its contacts before making review decisions.');
  }catch(error){if(token===serial)status(error.message);}
  finally{saving=false;el('correctionReviewFields').disabled=!selected;renderContacts();}
 }
 async function undoEdit(){
  if(saving||!selected)return;const history=histories.get(selected.item_id);if(!history?.length)return;
  const previous=history.at(-1);await bind(selected.item_id,previous.recipe.candidate_motion.path,previous.recipe.candidate_start_frame);
  if(JSON.stringify(selected?.recipe.candidate_motion)===JSON.stringify(previous.recipe.candidate_motion)&&selected.recipe.candidate_start_frame===previous.recipe.candidate_start_frame){history.pop();el('correctionEditUndo').disabled=!history.length;await buildPreview();}
 }
 async function bind(item,candidate=null,start=null,original=false){
  if(saving)return;capture();stop();if(candidate===null&&!original&&states.has(item)){candidate=states.get(item).metadata.recipe.candidate_motion.path;start=states.get(item).metadata.recipe.candidate_start_frame;}const token=++serial;el('correctionReviewFields').disabled=true;status('Checking selected native segment…');
  try{
   const query=new URLSearchParams({draft:packet.draft_id,sha256:packet.draft_sha256,item});
   if(candidate!==null){query.set('candidate',candidate);query.set('start',String(start));}
   const data=await request('/api/correction-review-source?'+query);
   if(token!==serial||!panel.open)return;
   if(data.draft_sha256!==packet.draft_sha256||data.item_id!==item||data.quality_approved!==false)throw Error('Selected packet changed');
   install(data);
   await showPreview('original',token);if(token!==serial||!panel.open)return;
   el('correctionReviewFields').disabled=false;status('Review the selected candidate; contact labels and decisions remain your draft.');
  }catch(error){if(token===serial){status(error.message);el('correctionReviewFields').disabled=!selected;if(selected){el('correctionCandidatePath').value=selected.candidate_relative;el('correctionCandidateStart').value=selected.recipe.candidate_start_frame;}}}
 }
 async function buildPreview(){
  if(saving||!selected)return;capture();stop();const s=state(),token=++serial;
  const payload={draft_id:packet.draft_id,draft_sha256:packet.draft_sha256,item_id:selected.item_id,candidate_motion:structuredClone(selected.recipe.candidate_motion),candidate_start_frame:selected.recipe.candidate_start_frame};
  saving=true;el('correctionReviewFields').disabled=true;status('Building and checking selected candidate geometry…');
  try{
   const data=await request('/api/correction-review-preview',payload);
   if(token!==serial||!panel.open||s!==state())return;
   if(JSON.stringify(data.selection)!==JSON.stringify(payload)||data.quality_approved!==false||data.training_admitted!==false||!/^\/files\/native-correction-previews\/[A-Za-z0-9_-]+\/candidate\.glb$/.test(data.preview_url)||!(/^[0-9a-f]{64}$/).test(data.preview_sha256))throw Error('Candidate preview differs from the bound selection');
   s.candidatePreview=data;await showPreview('candidate',token);
   if(token===serial&&panel.open)status('Selected candidate preview ready. Review judgments and permission remain unset unless you record them.');
  }catch(error){if(token===serial)status(error.message);}
  finally{saving=false;el('correctionReviewFields').disabled=!selected;renderContacts();}
 }
 async function refresh(){if(saving)return;capture();stop();const token=++serial;el('correctionReviewLoad').disabled=true;status('Checking saved review packetsâ€¦');try{const data=await request('/api/correction-review-drafts');if(token!==serial||!panel.open)return;packets=data.drafts.filter(r=>/^kimodo-target-review-[A-Za-z0-9_-]+$/.test(r.id)&&/^[0-9a-f]{64}$/.test(r.sha256)&&r.quality_approved===false);el('correctionReviewDraft').replaceChildren(...packets.map(p=>new Option(`${p.id} Â· ${p.segments} segments`,p.id)));el('correctionReviewDraft').disabled=!packets.length;el('correctionReviewLoad').disabled=!packets.length;status(packets.length?'Choose a packet. Loading a different packet resets this unsaved review draft.':'No native target review packets found.');}catch(error){if(token===serial)status(error.message);}}
 async function load(){if(saving)return;const p=packets.find(p=>p.id===el('correctionReviewDraft').value);if(!p)return;stop();const token=++serial;try{const data=await request('/api/correction-review-packet?'+new URLSearchParams({draft:p.id,sha256:p.sha256}));if(token!==serial||!panel.open)return;packet=data;states=new Map();histories=new Map();selected=null;el('correctionReviewItem').replaceChildren(...data.items.map(i=>new Option(i.id,i.id)));await bind(data.item_id);}catch(error){status(error.message);}}
 function setRange(whole=false){if(saving)return;try{const s=state();if(!s)throw Error('Load a segment first');if(!whole&&(!el('correctionContactStart').value.trim()||!el('correctionContactEnd').value.trim()))throw Error('Enter both interval frame boundaries');const channel=Number(el('correctionContactJoint').value);if(!Number.isInteger(channel)||channel<0||channel>3)throw Error('Choose a foot joint');const value=el('correctionContactState').value;const next=value==='planted'?true:value==='free'?false:value==='unknown'?null:undefined;s.contacts[channel]=annotate(s.contacts[channel],whole?0:Number(el('correctionContactStart').value),whole?selected.frames:Number(el('correctionContactEnd').value),next);s.pack=null;s.packKey=null;el('correctionPackStatus').textContent='Annotation changed; pack it again before acceptance.';renderContacts();}catch(error){status(error.message);}}
 async function pack(){if(saving)return;capture();const s=state();try{if(!s)throw Error('Load a segment first');if(s.contacts.flat().some(v=>v===null))throw Error('Mark planted and free states for every joint and frame');const value=recipe(),key=JSON.stringify(value);saving=true;el('correctionReviewFields').disabled=true;renderContacts();const data=await request('/api/correction-review-pack',{draft_id:packet.draft_id,draft_sha256:packet.draft_sha256,recipe:value});if(s!==state()||JSON.stringify(recipe())!==key)return;if(data.training_admitted!==false||data.item_id!==selected.item_id)throw Error('Unexpected packing result');s.pack=data;s.packKey=key;el('correctionPackStatus').textContent=`Saved ${data.folder}. Review and rights are still pending.`;}catch(error){status(error.message);}finally{saving=false;el('correctionReviewFields').disabled=!selected;renderContacts();}}
 async function save(){if(saving)return;capture();try{if(!packet)throw Error('Load a packet first');const name=el('correctionReviewerName').value.trim();if(!name)throw Error('Enter your actual reviewer name or alias');const timestamp=now();const items=packet.items.map(item=>{const s=states.get(item.id);if(!s||s.Decision==='unreviewed')throw Error('Every segment needs an accept or exclude decision');if(!s.Notes.trim())throw Error('Add review or exclusion notes for '+item.id);const row={id:item.id,decision:s.Decision,split:null,semantic_pass:null,motion_quality_pass:null,contact_schedule_pass:null,cleanup_seconds:null,notes:s.Notes,pack_id:null,rights:null};if(s.Decision==='exclude')return row;if(s.Decision!=='accept_corrected'||!s.pack||s.packKey!==JSON.stringify({...s.metadata.recipe,contacts:JOINTS.map((joint,i)=>({joint,intervals:intervals(s.contacts[i])}))}))throw Error('Pack the current annotation for '+item.id);if(!['train','development_validation'].includes(s.Split)||!s.SemanticPass||!s.QualityPass||!s.ContactPass||s.CleanupSeconds.trim()===''||!Number.isFinite(Number(s.CleanupSeconds))||Number(s.CleanupSeconds)<0)throw Error('Complete reviews, split and measured cleanup time for '+item.id);if(!s.RightsPermitted||!s.RightsName.trim()||!s.RightsEvidence.trim()||!s.RightsObligations.trim()||!s.RightsNotes.trim())throw Error('Complete the exact correction permission evidence for '+item.id);return {...row,split:s.Split,semantic_pass:true,motion_quality_pass:true,contact_schedule_pass:true,cleanup_seconds:Number(s.CleanupSeconds),pack_id:s.pack.id,rights:{authorized_by:s.RightsName,attested_at:timestamp,permitted:true,evidence_paths:s.RightsEvidence.split(/\r?\n/).map(s=>s.trim()).filter(Boolean),obligations:s.RightsObligations,notes:s.RightsNotes}};});saving=true;el('correctionReviewFields').disabled=true;el('correctionReviewSave').disabled=true;const data=await request('/api/correction-review-submission',{draft_id:packet.draft_id,draft_sha256:packet.draft_sha256,reviewer:{name,role:el('correctionReviewerRole').value,reviewed_at:timestamp},items});if(data.training_admitted!==false)throw Error('Unexpected review admission');status(`Saved review: ${data.submission.path}. ${data.reviewed_corrections} reviewed corrections; no training started.`);}catch(error){status(error.message);}finally{saving=false;el('correctionReviewFields').disabled=!selected;el('correctionReviewSave').disabled=false;}}
 el('correctionEditApply').onclick=applyEdit;el('correctionEditUndo').onclick=undoEdit;el('correctionEditOriginal').onclick=async()=>{if(saving||!selected)return;histories.delete(selected.item_id);await bind(selected.item_id,null,null,true);};
 el('correctionPreviewBuild').onclick=buildPreview;el('correctionPreviewVersion').onchange=()=>{if(!saving)return showPreview(el('correctionPreviewVersion').value).catch(error=>status(error.message));};
 el('correctionReviewRefresh').onclick=refresh;el('correctionReviewLoad').onclick=load;el('correctionReviewItem').onchange=()=>bind(el('correctionReviewItem').value);el('correctionCandidateBind').onclick=()=>{if(!selected||!/^\d+$/.test(el('correctionCandidateStart').value)){status('Enter a nonnegative matching-window start frame');return;}return bind(selected.item_id,el('correctionCandidatePath').value,Number(el('correctionCandidateStart').value));};el('correctionContactSet').onclick=()=>setRange(false);el('correctionContactWhole').onclick=()=>setRange(true);el('correctionContactHere').onclick=()=>{el('correctionContactStart').value=playhead;};el('correctionReviewPack').onclick=pack;el('correctionReviewSave').onclick=save;el('correctionReviewPlay').onclick=()=>player?.toggle();el('correctionReviewFit').onclick=()=>player?.fit();el('correctionReviewTime').oninput=()=>{stop();player?.seek(Number(el('correctionReviewTime').value));};
 for(const key of fields)el('correctionReview'+key).onchange=()=>{capture();renderContacts();};
 panel.addEventListener('toggle',()=>{if(panel.open)void refresh();else{++serial;stop();}});
 const owner=panel.closest?.('.window');if(owner&&MutationObserver)new MutationObserver(()=>{if(owner.hidden)stop();}).observe(owner,{attributes:true,attributeFilter:['hidden']});
 return {refresh,load,bind,pack,save,buildPreview,showPreview,applyEdit,undoEdit,pause:stop};
}
