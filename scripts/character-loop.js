function createRigLoopEditor({C,post,status,getContext,closeEditors,pause,onJob}){
 let binding=null,frames=0,revision=0,searching=false,busy=false;
 const searchFields=['rigLoopSearchStartMin','rigLoopSearchStartMax','rigLoopSearchPeriodMin','rigLoopSearchPeriodMax','rigLoopSearchStride','rigLoopRoot','rigLoopBlend','rigLoopTurn'];
 const safe=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 function controls(){C('rigLoopSearch').disabled=searching||busy;C('rigLoopApply').disabled=searching||busy;}
 function invalidate(){revision++;C('rigLoopCandidates').replaceChildren();C('rigLoopSearchStatus').textContent='';}
 function hide(){invalidate();C('rigLoopPanel').hidden=true;C('rigMappingPanel').hidden=false;}
 function reset(){binding=null;hide();C('rigLoop').disabled=true;}
 function bound(){const c=getContext();if(!binding||binding.job!==c.job?.id||binding.variant!==c.variant||binding.glb_sha256!==c.job?.result?.variants[c.variant]?.sha256)throw Error('Reopen loop settings for this clip');return c;}
 function clock(){const a=Number(C('rigLoopStart').value),p=Number(C('rigLoopPeriod').value),k=Number(C('rigLoopBlend').value);C('rigLoopClock').textContent=a>=0&&p>k&&k>=4&&a+p+k<=frames?`${(p/30).toFixed(2)} seconds per cycle · ${p+1} samples with terminal frame · needs source through frame ${a+p+k-1}.`:'Choose a cycle longer than the blend and leave enough continuation frames.';}
 C('rigLoop').onclick=safe(()=>{
  const c=getContext();if(!c.result||c.result.kind==='neutral'||c.variant==='repeated')throw Error('Choose a finite source or one-cycle version');
  pause();closeEditors();invalidate();binding={job:c.job.id,variant:c.variant,glb_sha256:c.job.result.variants[c.variant].sha256};frames=c.result.frames;
  C('rigLoopName').value=('Loop · '+c.job.label).slice(0,160);C('rigLoopStart').value=0;C('rigLoopPeriod').value=Math.min(60,frames-8);C('rigLoopBlend').value=8;C('rigLoopTurn').value=0;C('rigLoopRoot').value='travel';
  C('rigLoopSearchStartMin').value=0;C('rigLoopSearchStartMax').value=Math.min(30,Math.max(0,frames-39));C('rigLoopSearchPeriodMin').value=Math.min(30,frames-8);C('rigLoopSearchPeriodMax').value=Math.min(90,frames-8);C('rigLoopSearchStride').value=5;
  C('rigLoopBinding').textContent=c.job.label+' · '+c.variant+' · '+frames+' source frames';C('rigEventPanel').hidden=true;C('rigMappingPanel').hidden=true;C('rigLoopPanel').hidden=false;clock();controls();
 });
 for(const id of ['rigLoopStart','rigLoopPeriod'])C(id).oninput=clock;
 for(const id of searchFields)C(id).oninput=()=>{invalidate();clock();};
 C('rigLoopSearch').onclick=safe(async()=>{
  bound();invalidate();const token=revision;searching=true;controls();C('rigLoopSearchStatus').textContent='Comparing candidate ranges and checking shortlisted meshes…';
  const payload={...binding,schema:'strep-cycle-search-v1',root_mode:C('rigLoopRoot').value,blend_frames:Number(C('rigLoopBlend').value),turn_degrees:Number(C('rigLoopTurn').value),start_min:Number(C('rigLoopSearchStartMin').value),start_max:Number(C('rigLoopSearchStartMax').value),period_min:Number(C('rigLoopSearchPeriodMin').value),period_max:Number(C('rigLoopSearchPeriodMax').value),stride:Number(C('rigLoopSearchStride').value)};
  try{
   const data=await post('/api/rig-loop-search',payload);if(token!==revision)return;bound();
   C('rigLoopSearchStatus').textContent=`${data.candidate_count} candidates compared. Kinematic ranking only; none is automatically accepted. Missing contacts are unknown.`;
   const link=document.createElement('a');link.href=data.report_url;link.target='_blank';link.rel='noopener';link.textContent='Download full ranking and search settings';link.download='cycle-search.json';C('rigLoopCandidates').append(link);
   for(const row of data.shortlist){
    const item=document.createElement('div');item.className='rig-mapping';const text=document.createElement('p');text.className='small';
    const m=row.metrics,g=row.mesh,speed=g.any_weight_authored_patch_speed_p95_m_s,support=m.predicted_support_disagreement_fraction;
    text.textContent=`#${row.rank} · start ${row.recipe.start_frame} · ${row.recipe.period_frames} frames (${(row.recipe.period_frames/30).toFixed(2)}s). Max joint step ${m.step_max_deg.toFixed(1)}°; pose gap ${m.pose_gap_max_deg.toFixed(1)}°; velocity gap ${m.velocity_gap_max_deg_s.toFixed(0)}°/s; root acceleration ${m.root_acceleration_max_m_s2.toFixed(1)}m/s². Support disagreement ${support==null?'unknown':(support*100).toFixed(0)+'%'}. Floor ${(g.floor_depth_max_m*1000).toFixed(1)}mm; annotated patch sliding ${speed==null?'unknown':(speed*1000).toFixed(1)+'mm/s (p95)'}.`;
    const button=document.createElement('button');button.className='btn';button.textContent=`Use candidate ${row.rank}`;button.onclick=safe(()=>{if(token!==revision)throw Error('Search settings changed; search again');bound();C('rigLoopStart').value=row.recipe.start_frame;C('rigLoopPeriod').value=row.recipe.period_frames;clock();status('Candidate range selected. Create the loop to review its animation over three cycles.');});
    item.append(text,button);C('rigLoopCandidates').append(item);
   }
  }catch(e){if(token===revision)C('rigLoopSearchStatus').textContent=e.message;throw e;}finally{searching=false;controls();}
 });
 C('rigLoopClose').onclick=hide;C('rigLoopApply').onclick=safe(async()=>{bound();const p={...binding,schema:'strep-rig-loop-v1',root_mode:C('rigLoopRoot').value,label:C('rigLoopName').value,start_frame:Number(C('rigLoopStart').value),period_frames:Number(C('rigLoopPeriod').value),blend_frames:Number(C('rigLoopBlend').value),turn_degrees:Number(C('rigLoopTurn').value)};onJob(await post('/api/rig-loops',p));status('Building the cycle and a three-cycle review with accumulated root motion.');});
 return {hide,reset,ready:()=>C('rigLoop').disabled=!getContext().result||getContext().result.kind==='neutral'||getContext().variant==='repeated',setBusy:b=>{busy=b;controls();}};
}
