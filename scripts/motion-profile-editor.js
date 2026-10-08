// Character profiles are authored descriptions, not calibrated physical stats.
export function createMotionProfileEditor(host,onChange,{idPrefix=''}={}){
 const clone=x=>JSON.parse(JSON.stringify(x));let profile=null,enabled=false,version=0;
 const el=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
 const toggle=el('input');toggle.type='checkbox';toggle.id=idPrefix+'motionProfileEnabled';
 const toggleLabel=el('label','Use a character movement profile ');toggleLabel.prepend(toggle);host.append(toggleLabel);
 const body=el('div');body.hidden=true;host.append(body);const css=el('style');css.textContent='#movementProfile fieldset{border:1px solid var(--line);border-radius:10px;margin:12px 0;padding:12px}#movementProfile .row{display:flex;align-items:center;gap:12px}#movementProfile input[type=range]{flex:1}#movementProfile output{min-width:2em}#movementProfile .btn{margin:6px 6px 6px 0}#motionBriefPreview p{white-space:pre-wrap;overflow-wrap:anywhere}'.replaceAll('#movementProfile','#'+host.id).replaceAll('#motionBriefPreview','#'+idPrefix+'motionBriefPreview');host.append(css);
 const note=el('p','These are editable art-direction rules. Their effect on each action needs review. A stat with no rule is saved without changing the generated description.');note.className='small';body.append(note);
 const evidence=el('p','Mobility is not reliable across actions yet: only waving passed the angle-range screen in a three-action, three-seed test; squats and kicks did not. Action quality and naturalness remain unreviewed. Other stats are not validated by that test.');evidence.className='small';body.append(evidence);
 const fields={};for(const [key,label,max] of [['name','Profile name',80],['policy_name','Rule set name',100],['style','Movement style',300],['training','Training or specialties',200],['state','Current state, such as fatigue or carried load',200]]){
  const wrap=el('label',label),input=el(key==='name'||key==='policy_name'?'input':'textarea');input.maxLength=max;input.id=idPrefix+'motionProfile-'+key;wrap.append(input);body.append(wrap);fields[key]=input;
  input.oninput=()=>{if(profile){profile[key]=input.value;changed();}};
 }
 const bandNote=el('p','Each rule selects a low (0–33), middle (34–66) or high (67–100) description. Values in the same band use the same description. Endurance has no default rule: describe current fatigue above when it matters.');bandNote.className='small';body.append(bandNote);
 const stats=el('div');stats.id=idPrefix+'motionProfileStats';body.append(stats);
 const add=el('button','+ Add a game stat');add.type='button';add.className='btn';body.append(add);
 const previewButton=el('button','Preview resolved motion description');previewButton.type='button';previewButton.className='btn';body.append(previewButton);
 const preview=el('div');preview.id=idPrefix+'motionBriefPreview';preview.setAttribute('aria-live','polite');body.append(preview);
 let requestSource=null;
 function changed(){version++;preview.replaceChildren(el('p','Description changed. Preview it before generating.'));onChange?.();}
 function draw(){
  body.hidden=!enabled;toggle.checked=enabled;if(!profile)return;
  for(const [key,input] of Object.entries(fields))input.value=profile[key];stats.replaceChildren();
  for(const stat of profile.stats){
   const group=el('fieldset'),legend=el('legend',stat.label);group.append(legend);
   const label=el('label','Game stat name'),name=el('input');name.value=stat.label;name.maxLength=60;label.append(name);group.append(label);name.oninput=()=>{stat.label=name.value;legend.textContent=name.value;changed();};
   const row=el('div');row.className='row';const range=el('input');range.type='range';range.min=0;range.max=100;range.step=1;range.value=stat.value;range.setAttribute('aria-label',stat.label+' game stat');const value=el('output',String(stat.value));row.append(range,value);group.append(row);
   const effect=el('p');effect.className='small';group.append(effect);
   function updateEffect(){effect.textContent=stat.levels?stat.levels[stat.value<34?0:stat.value<67?1:2]:'No rule: saved as profile data only.';}
   range.oninput=()=>{stat.value=Number(range.value);value.textContent=range.value;updateEffect();changed();};
   const details=el('details'),summary=el('summary','Edit this stat’s motion rules');details.append(summary);
   const apply=el('input');apply.type='checkbox';apply.checked=!!stat.levels;const applyLabel=el('label',' Apply a description for this stat');applyLabel.prepend(apply);details.append(applyLabel);
   const inputs=[];for(const [i,title] of ['Low · 0–33','Middle · 34–66','High · 67–100'].entries()){
    const wrap=el('label',title),input=el('textarea');input.maxLength=180;input.value=stat.levels?.[i]||'';input.disabled=!stat.levels;wrap.append(input);details.append(wrap);inputs.push(input);
    input.oninput=()=>{if(stat.levels){stat.levels[i]=input.value;updateEffect();changed();}};
   }
   apply.onchange=()=>{stat.levels=apply.checked?inputs.map(i=>i.value):null;inputs.forEach(i=>i.disabled=!apply.checked);updateEffect();changed();};
   const remove=el('button','Remove stat');remove.type='button';remove.className='btn';remove.onclick=()=>{profile.stats=profile.stats.filter(s=>s!==stat);draw();changed();};details.append(remove);group.append(details);updateEffect();stats.append(group);
  }
  add.disabled=profile.stats.length>=12;
 }
 toggle.onchange=async()=>{const token=++version;enabled=toggle.checked;if(enabled&&!profile){try{const r=await fetch('/api/motion-profile-template');if(!r.ok)throw Error('Could not load movement profile');const loaded=await r.json();if(token!==version)return;profile=loaded;}catch(e){if(token!==version)return;enabled=false;toggle.checked=false;preview.textContent=e.message;body.hidden=false;return;}}draw();changed();};
 add.onclick=()=>{let i=1;while(profile.stats.some(s=>s.id==='custom-'+i))i++;profile.stats.push({id:'custom-'+i,label:'Custom stat '+i,value:50,levels:null});draw();changed();};
 previewButton.onclick=async()=>{
  if(!requestSource)return;const token=++version;preview.textContent='Resolving description…';
  try{const request=requestSource(),r=await fetch('/api/motion-brief',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}),data=await r.json();if(!r.ok)throw Error(data.error||'Could not resolve profile');if(token!==version)return;
   preview.replaceChildren();const brief=data.motion_brief;if(!brief){preview.textContent='No movement profile applied.';return;}
   for(const [i,s] of brief.segments.entries()){const item=el('p',`Action ${i+1}: ${s.conditioning_prompt}`);preview.append(item);}
   if(brief.unmapped_stats.length)preview.append(el('p','Saved without a motion rule: '+brief.unmapped_stats.map(s=>s.label).join(', ')+'.'));
  }catch(e){if(token===version)preview.textContent=e.message;}
 };
 return {snapshot:()=>({enabled,profile:profile?clone(profile):null}),request:()=>enabled&&profile?clone(profile):null,
  replace(value){enabled=!!value;profile=value?clone(value):null;draw();changed();},
  restore(value){version++;preview.replaceChildren();enabled=!!value?.enabled;profile=value?.profile?clone(value.profile):null;draw();},
  setRequestSource(fn){requestSource=fn;},markChanged:changed};
}
