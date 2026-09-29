// Render recorded numeric evidence without turning a partial screen into approval.
function contactAuditRows(audit){
 const rows=[],finite=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
 const fmt=v=>Number(v.toPrecision(6)).toString(),mm=v=>fmt(v*1000)+' mm';
 const add=(label,status,detail)=>rows.push({label,status,detail});
 const pins=Array.isArray(audit?.contacts)?audit.contacts:[];
 if(!pins.length)add('Contact pins','unavailable','No exported pin measurements attached.');
 for(const pin of pins){
  const label=typeof pin?.region==='string'?pin.region:'Contact';
  const interval=Number.isInteger(pin?.start_frame)&&Number.isInteger(pin?.end_frame)?` · frames ${pin.start_frame}–${pin.end_frame}`:'';
  const valid=finite(pin?.maximum_error_m)&&Number.isInteger(pin?.samples)&&pin.samples>0&&Number.isInteger(pin?.samples_over_5mm)&&pin.samples_over_5mm>=0&&pin.samples_over_5mm<=pin.samples;
  if(!valid){add(label+interval,'unavailable','Incomplete exported pin measurements.');continue;}
  const over=Math.max(0,pin.maximum_error_m-.005),failed=over>0||pin.samples_over_5mm>0;
  add(label+interval,failed?'fail':'pass',`${mm(pin.maximum_error_m)} maximum / 5 mm limit; ${pin.samples_over_5mm} of ${pin.samples} samples miss the target.${over>0?' Over by '+mm(over)+'.':''}`);
 }
 const rates=Array.isArray(audit?.phase_rates)?audit.phase_rates:[];
 if(!rates.length)add('Contact speed and acceleration','unavailable','No exported rate limits attached.');
 for(const row of rates){
  for(const [index,name,unit] of [[0,'speed','m/s'],[1,'acceleration','m/s²']]){
   const label=[typeof row?.region==='string'?row.region:'Contact',typeof row?.phase==='string'?row.phase:'phase',name].join(' · ');
   const value=row?.variants?.candidate?.[index],limit=row?.checked_ceilings?.[index];
   if(!finite(value)||!finite(limit)){add(label,'unavailable','Measurement or limit unavailable.');continue;}
   const excess=Math.max(0,value-limit);
   add(label,excess>0?'fail':'pass',`${fmt(value)} / ${fmt(limit)} ${unit} limit.${excess>0?' Over by '+fmt(excess)+' '+unit+'.':''}`);
  }
 }
 const depth=audit?.floor_nonregression?.maximum_added_depth_m,total=audit?.variants?.candidate?.maximum_floor_depth_m;
 add('Added floor penetration',finite(depth)?(depth>0?'fail':'pass'):'unavailable',finite(depth)?`${mm(depth)} added compared with the source.${finite(total)?' Total penetration: '+mm(total)+'.':''}`:'No floor comparison attached.');
 const outside=audit?.preservation?.all_outside_times,errors=outside?.maximum_errors;
 const valid=Number.isInteger(outside?.samples)&&outside.samples>0&&typeof outside.within_numerical_tolerance==='boolean'&&['joint_position_error_m','basis_error','skin_position_error_m'].every(k=>finite(errors?.[k]));
 if(!valid)add('Outside the edit window','unavailable','No complete outside-window comparison attached.');
 else{
  // Matches the existing SOMA outside-window audit's 1e-6 position/basis limits.
  const passed=outside.within_numerical_tolerance&&Object.values(errors).every(v=>v<=1e-6),exact=passed&&Object.values(errors).every(v=>v===0);
  add('Outside the edit window',passed?'pass':'fail',`${exact?'Unchanged at':passed?'Within export tolerance at':'Changed beyond export tolerance at'} ${outside.samples} samples; maximum mesh drift ${mm(errors.skin_position_error_m)}.`);
 }
 return rows;
}

const contactEditor=(()=>{
 const el=id=>document.getElementById(id),names=['LeftHand','RightHand','LeftFoot','RightFoot','Torso','Head','LeftKnee','RightKnee','LeftElbow','RightElbow'];
 let context=null,draft=null,busy=false,submit=null,currentFrame=null,editing=null,shownTiming=null,savedCheck=null;
 const clone=v=>JSON.parse(JSON.stringify(v));
 const canFit=()=>savedCheck?.status==='checked'&&savedCheck?.check_schema_version===3&&!!savedCheck?.check_revision;
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
  el('contactApply').disabled=busy||!context;el('contactCheck').disabled=busy||!context;el('contactFitChecked').disabled=busy||!canFit();
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
   el('contactFitChecked').onclick=async()=>{if(!context||busy||!canFit())return;busy=true;render();message('Fitting the saved checked pins on a source copy…');try{await submit(context,null,null,{checked_plan:savedCheck.id.split('/')[1],revision:savedCheck.check_revision});}catch(e){message(e.message);busy=false;render();}};
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
   if(t.support_correction?.checked_fit){
    const rows=contactAuditRows(t.support_correction.export_audit),failures=rows.filter(r=>r.status==='fail').length,missing=rows.filter(r=>r.status==='unavailable').length;
    const details=document.createElement('details'),summary=document.createElement('summary'),list=document.createElement('ul');
    details.className='contact-audit';details.open=failures>0||missing>0;
    summary.textContent=`Contact export checks · ${failures} failed · ${missing} unavailable`;details.append(summary);
    for(const row of rows){const item=document.createElement('li'),label=document.createElement('strong');item.setAttribute('data-status',row.status);label.textContent=`${row.status==='pass'?'Pass':row.status==='fail'?'Fail':'Unavailable'} · ${row.label}`;item.append(label,document.createTextNode(' — '+row.detail));list.append(item);}
    details.append(list);const note=document.createElement('p');note.textContent='These sampled checks do not approve the animation. Review the full clip and its body-quality flags.';details.append(note);
    const a=document.createElement('a');a.textContent='Full contact export audit';a.href='/files/'+collection+'/takes/'+t.id+'/checked-export-audit.json';a.target='_blank';a.rel='noopener';details.append(a);el('contactResult').append(details);
   }
   const feedback=t.support_correction?.export_feedback;
   if(feedback){
    const p=document.createElement('p'),value=feedback.maximum_root_step_m,valid=typeof value==='number'&&Number.isFinite(value)&&value>=0&&typeof feedback.export_and_native_screen==='boolean';
    p.textContent=valid?`Export repair: ${value>0?'selected a corrected candidate':'retained the fitted motion'}; ${feedback.export_and_native_screen?'sampled export and native checks pass':'measured constraints still fail'}. Maximum root adjustment ${Number((value*1000).toPrecision(6))} mm. Animation remains unapproved.`:'Export repair measurements unavailable. Animation remains unapproved.';
    el('contactResult').append(p);
    for(const [label,file] of [['Repair decisions','feedback-report.json'],['Joint rate measurements','checked-global-rates.json'],['Initial fitted motion','initial-fit/motion.npz']]){const a=document.createElement('a');a.textContent=label;a.href='/files/'+collection+'/takes/'+t.id+'/'+file;a.target='_blank';a.rel='noopener';el('contactResult').append(a,document.createTextNode(' '));}
   }
   render();
  },
  showTiming(job){if(!context||job.source!==context.collection+'/takes/'+context.take_id||shownTiming===job.id)return;shownTiming=job.id;savedCheck=job;el('contactFitChecked').disabled=busy||!canFit();el('contactTimingResult').textContent='Saved timing check (your current draft may differ):\n'+(job.timing_message||'Timing check finished.')+(job.check_schema_version!==3?'\nThis saved check predates pose-screen verification with full-distance bounds. Run a new check before fitting.':'');el('contactTimingLinks').replaceChildren();for(const [label,url] of [['Explanation',job.timing_report],['Full timing report',job.timing_json],['Pose compatibility',job.pose_report],['Bound contact points',job.bound_contacts]]){if(typeof url!=='string'||!url.startsWith('/files/contact-jobs/'))continue;const a=document.createElement('a');a.textContent=label;a.href=url;a.className='btn';a.target='_blank';a.rel='noopener';el('contactTimingLinks').append(a);}message('Timing check saved. Your source and contact draft are unchanged.');},
  setBusy(value){busy=value;if(context){el('contactApply').disabled=busy;el('contactCheck').disabled=busy;el('contactFitChecked').disabled=busy||!canFit();}}
 };
})();
