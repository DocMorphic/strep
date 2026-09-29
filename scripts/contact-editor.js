const contactEditor=(()=>{
 const el=id=>document.getElementById(id),names=['LeftHand','RightHand','LeftFoot','RightFoot','Torso','Head','LeftKnee','RightKnee','LeftElbow','RightElbow'];
 let context=null,draft=null,busy=false,submit=null,currentFrame=null,editing=null,shownTiming=null,savedCheck=null;
 const clone=v=>JSON.parse(JSON.stringify(v));
 function persist(){if(context)try{localStorage.setItem('strep:contacts:'+context.key,JSON.stringify(draft));}catch{}}
 function inputs(){const mode=el('contactMode').value;el('contactInterval').hidden=['inferred','disabled'].includes(mode);el('contactWorld').hidden=mode!=='world';}
 function message(text){el('contactStatus').textContent=text;}
 function render(){
  el('contactPlan').replaceChildren();
  for(const [region,item] of Object.entries(draft.regions)){
   const segments=item.segments?.length?item.segments:[null];
   segments.forEach((s,index)=>{const row=document.createElement('div');row.className='contact-plan-row';
    const label=document.createElement('button');label.type='button';label.className='btn';label.textContent=s?`${region} · ${s.start_frame}–${s.end_frame} · ${s.space==='track'?'Moving target':s.space==='world'?'World pin':'Follow source'}`:`${region} · ${item.mode==='disabled'?'Disabled':'Automatic'}`;
    label.onclick=()=>{if(s?.space==='track'){editing=null;return message('This sampled moving target is retained as authored. Edit its scene trajectory and recompile, or remove the interval to replace it.');}el('contactRegion').value=region;el('contactMode').value=s?s.space:item.mode;editing=s?{region,index}:null;if(s){el('contactStart').value=s.start_frame;el('contactEnd').value=s.end_frame;if(s.position_m)['X','Y','Z'].forEach((axis,i)=>el('contact'+axis).value=s.position_m[i]);}inputs();};
    const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.textContent='Remove';remove.setAttribute('aria-label',`Remove ${region} ${s?index+1:'override'}`);remove.onclick=()=>{if(s){item.segments.splice(index,1);if(!item.segments.length)delete draft.regions[region];}else delete draft.regions[region];editing=null;persist();render();};row.append(label,remove);el('contactPlan').append(row);
   });
  }
  if(!Object.keys(draft.regions).length)el('contactPlan').textContent='No overrides. Automatic contact estimates remain in use.';
  el('contactApply').disabled=busy||!context;el('contactCheck').disabled=busy||!context;el('contactFitChecked').disabled=busy||!savedCheck||savedCheck.status!=='checked'||!savedCheck.check_revision;
 }
 function save(){
  if(!context)return;const region=el('contactRegion').value,mode=el('contactMode').value;
  if(['inferred','disabled'].includes(mode))draft.regions[region]={mode};
  else{
   const a=Number(el('contactStart').value),b=Number(el('contactEnd').value);
   if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<a||b>=draft.frame_count)return message(`Frames must lie between 0 and ${draft.frame_count-1}, with start before end.`);
   const segment={start_frame:a,end_frame:b,space:mode};
   const prior=editing?.region===region?draft.regions[region]?.segments?.[editing.index]:null;if(prior?.vertex_id!==undefined)segment.vertex_id=prior.vertex_id;
   if(mode==='world'){
    const coordinates=['X','Y','Z'].map(axis=>el('contact'+axis).value);
    if(coordinates.some(v=>v.trim()===''))return message('Enter all three world coordinates.');
    segment.position_m=coordinates.map(Number);
    if(segment.position_m.some(v=>!Number.isFinite(v)||Math.abs(v)>1000)||segment.position_m[1]<0)return message('Use finite metre coordinates; floor-contact Y must be at least zero.');
   }
   const segments=clone(draft.regions[region]?.mode==='explicit'?draft.regions[region].segments:[]);
   if(editing?.region===region)segments[editing.index]=segment;else segments.push(segment);
   segments.sort((x,y)=>x.start_frame-y.start_frame);
   if(segments.some((s,i)=>i&&s.start_frame<=segments[i-1].end_frame))return message('Intervals for the same region cannot overlap.');
   draft.regions[region]={mode:'explicit',segments};
  }
  editing=null;persist();render();message('Contact plan saved locally. Apply it to produce a separate candidate.');
 }
 return {
  mount(options){submit=options.submit;currentFrame=options.frame;
   el('contactRegion').replaceChildren(...names.map(n=>new Option(n.replace(/([a-z])([A-Z])/g,'$1 $2'),n)));
   el('contactMode').onchange=inputs;el('contactRegion').onchange=()=>{editing=null;};el('contactSave').onclick=save;
   el('contactHere').onclick=()=>{el('contactStart').value=currentFrame();el('contactEnd').value=currentFrame();};
   el('contactApply').onclick=async()=>{if(!context||busy)return;busy=true;render();message('Starting local contact correction…');try{await submit(context,clone(draft));message('Correction is running. The result will open when ready.');}catch(e){message(e.message);busy=false;render();}};
   for(const id of ['contactWindowStart','contactWindowEnd'])el(id).oninput=()=>{if(context)try{localStorage.setItem('strep:contact-window:'+context.key,JSON.stringify([Number(el('contactWindowStart').value),Number(el('contactWindowEnd').value)]));}catch{}};
   el('contactFitChecked').onclick=async()=>{if(!context||busy||savedCheck?.status!=='checked')return;busy=true;render();message('Fitting the saved checked pins on a source copy…');try{await submit(context,null,null,{checked_plan:savedCheck.id.split('/')[1],revision:savedCheck.check_revision});}catch(e){message(e.message);busy=false;render();}};
   el('contactCheck').onclick=async()=>{if(!context||busy)return;const w=[Number(el('contactWindowStart').value),Number(el('contactWindowEnd').value)];if(!w.every(Number.isInteger)||w[0]<1||w[0]>=w[1]||w[1]>=draft.frame_count-1)return message('Choose two held interior frames in increasing order.');busy=true;render();message('Checking stationary pin timing on a saved copy…');try{await submit(context,clone(draft),{edit_window:w});}catch(e){message(e.message);busy=false;render();}};
   inputs();
  },
  load(collection,t){
   const supported=!!t.body_correction;el('contactEditor').hidden=!supported;if(!supported){context=null;return;}
   const key=collection+'/'+t.id;
   if(context?.key!==key){context={key,collection,take_id:t.id};draft=clone(t.support_correction?.contact_spec||{schema_version:1,fps:30,frame_count:t.frames,regions:{}});
    try{const saved=JSON.parse(localStorage.getItem('strep:contacts:'+key)||'null');if([1,2].includes(saved?.schema_version)&&saved.frame_count===t.frames&&saved.regions&&typeof saved.regions==='object')draft=saved;}catch{}
    editing=null;shownTiming=null;savedCheck=null;el('contactWindowStart').value=1;el('contactWindowEnd').value=t.frames-2;el('contactWindowStart').max=el('contactWindowEnd').max=t.frames-2;try{const w=JSON.parse(localStorage.getItem('strep:contact-window:'+key)||'null');if(Array.isArray(w)&&w.length===2){el('contactWindowStart').value=w[0];el('contactWindowEnd').value=w[1];}}catch{}el('contactTimingResult').textContent='';el('contactTimingLinks').replaceChildren();el('contactStart').max=el('contactEnd').max=t.frames-1;el('contactStart').value=0;el('contactEnd').value=t.frames-1;message('');
   }
   const check=t.support_correction?.target_evaluation;
   el('contactResult').textContent=check?.intervals?.length?check.intervals.map(r=>`${r.region} frames ${r.start_frame}–${r.end_frame}: max ${(r.max_error_m*1000).toFixed(1)} mm; ${r.frames_outside_tolerance}/${r.frame_count} frames outside target tolerance.`).join(' '):'No authored-target measurements attached to this candidate.';
   if(t.support_correction?.checked_fit){el('contactResult').append(document.createTextNode(' This candidate was fitted from a saved timing check. Exported contact and rate failures remain review flags. '));const a=document.createElement('a');a.textContent='Checked export audit';a.href='/files/'+collection+'/takes/'+t.id+'/checked-export-audit.json';a.target='_blank';a.rel='noopener';el('contactResult').append(a);}
   render();
  },
  showTiming(job){if(!context||job.source!==context.collection+'/takes/'+context.take_id||shownTiming===job.id)return;shownTiming=job.id;savedCheck=job;el('contactFitChecked').disabled=busy||job.status!=='checked'||!job.check_revision;el('contactTimingResult').textContent='Saved timing check (your current draft may differ):\n'+(job.timing_message||'Timing check finished.');el('contactTimingLinks').replaceChildren();for(const [label,url] of [['Explanation',job.timing_report],['Full timing report',job.timing_json],['Bound contact points',job.bound_contacts]]){if(typeof url!=='string'||!url.startsWith('/files/contact-jobs/'))continue;const a=document.createElement('a');a.textContent=label;a.href=url;a.className='btn';a.target='_blank';a.rel='noopener';el('contactTimingLinks').append(a);}message('Timing check saved. Your source and contact draft are unchanged.');},
  setBusy(value){busy=value;if(context){el('contactApply').disabled=busy;el('contactCheck').disabled=busy;el('contactFitChecked').disabled=busy||savedCheck?.status!=='checked'||!savedCheck?.check_revision;}}
 };
})();
