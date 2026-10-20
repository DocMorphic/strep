const hash=/^[a-f0-9]{64}$/;
const finite3=v=>Array.isArray(v)&&v.length===3&&v.every(x=>typeof x==='number'&&Number.isFinite(x));
export function validateGeometry(asset,geometry){
 if(!hash.test(asset?.id)||!hash.test(asset?.geometry_sha256)||geometry?.asset_id!==asset.id||geometry.geometry_sha256!==asset.geometry_sha256)throw Error('Object geometry does not match this saved object.');
 const {vertices_m:vertices,faces}=geometry;
 if(!Array.isArray(vertices)||vertices.length<3||vertices.length>200000||vertices.length!==asset.inventory?.vertices||!vertices.every(v=>finite3(v)&&v.every(x=>Number.isFinite(Math.fround(x)))))throw Error('Object vertices cannot be displayed safely.');
 if(!Array.isArray(faces)||!faces.length||faces.length>400000||faces.length!==asset.inventory?.faces||!faces.every(f=>Array.isArray(f)&&f.length===3&&f.every(i=>Number.isInteger(i)&&i>=0&&i<vertices.length)))throw Error('Invalid object triangles.');
 return geometry;
}
export function selectionRequest(asset,face,barycentric){
 if(!asset||!Number.isInteger(face)||face<0||face>=asset.inventory.faces||!finite3(barycentric)||barycentric.some(x=>x<0||x>1)||Math.abs(barycentric.reduce((a,b)=>a+b,0)-1)>1e-10)throw Error('Choose a point on the object surface.');
 return {asset_id:asset.id,geometry_sha256:asset.geometry_sha256,face,barycentric:[...barycentric]};
}
export function verifyPoint(request,point){
 if(point?.source_sha256!==request.asset_id||point.geometry_sha256!==request.geometry_sha256||point.face!==request.face||JSON.stringify(point.barycentric)!==JSON.stringify(request.barycentric)||!finite3(point.position_m)||!finite3(point.winding_normal)||point.contact_verified!==false||point.outward_normal_verified!==false)throw Error('The saved surface point does not match this object.');
 return point;
}
export function createPropGripEditor({document=globalThis.document,request,viewer}){
 const el=s=>document.getElementById('propGrip'+s);
 let asset=null,draft=null,epoch=0,pickEpoch=0,busy=false;
 const status=s=>{el('Status').textContent=s;};
 const controls=()=>{for(const name of ['Import','Open'])el(name).disabled=busy;el('Pick').disabled=el('Home').disabled=!asset||busy;el('Save').disabled=!draft||busy;el('Show').disabled=el('Saved').disabled=!asset?.grip_ids.length||busy;};
 function reset(){epoch++;pickEpoch++;asset=draft=null;viewer.clear();el('Info').textContent='';el('Downloads').replaceChildren();el('Saved').replaceChildren();controls();}
 function link(label,url){const a=document.createElement('a');a.textContent=label;a.href=url;a.download='';a.className='btn';el('Downloads').append(a);}
 function savedOptions(){el('Saved').replaceChildren(...asset.grip_ids.map((id,i)=>{const o=document.createElement('option');o.value=id;o.textContent=`Grip ${i+1} · ${id.slice(0,8)}`;return o;}));}
 async function bind(value,ticket){
  if(ticket!==epoch)return;
  if(!hash.test(value?.id)||!Array.isArray(value.grip_ids)||!value.grip_ids.every(id=>hash.test(id)))throw Error('Invalid saved object.');
  const geometry=await request(`/api/props/${value.id}/geometry`);
  if(ticket!==epoch)return;
  validateGeometry(value,geometry);viewer.show(geometry);asset=value;draft=null;el('Asset').value=value.id;
  el('Info').textContent=`${value.name} · ${value.inventory.vertices} vertices · ${value.inventory.faces} triangles. Drag to orbit; scroll to zoom. Object ID: ${value.id}`;
  savedOptions();link('Original object',`/files/prop-assets/${value.id}/prop.glb`);status('Object ready. Choose Pick grip, then click its surface.');controls();
 }
 async function action(fn){if(busy)return;busy=true;controls();try{await fn();}catch(e){status(e.message);}finally{busy=false;controls();}}
 el('Import').onclick=()=>action(async()=>{
  const file=el('File').files?.[0],license=el('License').value;
  if(!file||!file.name.toLowerCase().endsWith('.glb')||file.size<=0||file.size>32*1024**2)throw Error('Choose a static GLB up to 32 MiB.');
  reset();const ticket=epoch;status('Importing object…');
  const value=await request('/api/props/import',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Filename':encodeURIComponent(file.name),'X-License-Note':encodeURIComponent(license)},body:file});
  await bind(value,ticket);
 });
 el('Open').onclick=()=>action(async()=>{const id=el('Asset').value.trim();if(!hash.test(id))throw Error('Paste the complete saved object ID.');reset();const ticket=epoch;status('Opening object…');await bind(await request(`/api/props/${id}`),ticket);});
 el('File').onchange=el('Asset').oninput=()=>{reset();status('Selection changed. Import or open the selected object.');};
 async function choose(face,barycentric){
  if(!asset||busy)return;const ticket=epoch,pick=++pickEpoch;
  draft=null;viewer.mark(null);controls();status('Checking surface point…');
  try{const payload=selectionRequest(asset,face,barycentric);
   const point=await request('/api/props/surface-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   if(ticket!==epoch||pick!==pickEpoch)return;
   verifyPoint(payload,point);draft=payload;viewer.mark(point.position_m);status(`Grip selected at ${point.position_m.map(x=>x.toFixed(4)).join(', ')} m. Name it, then save.`);controls();
  }catch(e){if(ticket===epoch&&pick===pickEpoch)status(e.message);}
 }
 el('Pick').onclick=()=>{if(!asset||busy)return;pickEpoch++;draft=null;viewer.mark(null);controls();viewer.pick(choose);status('Click the object to select a grip. Escape cancels; drag to orbit after picking.');};
 el('Home').onclick=()=>viewer.home();
 el('Save').onclick=()=>action(async()=>{
  const label=el('Label').value.trim();if(!draft||!label||label.length>120)throw Error('Select a grip and enter a name.');
  const payload={...draft,label},ticket=epoch;pickEpoch++;viewer.cancel();
  const result=await request('/api/props/grips',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(ticket!==epoch)return;
  verifyPoint(payload,result.selection);if(!hash.test(result.grip_id)||result.selection.label!==label)throw Error('Invalid saved grip receipt.');
  if(!asset.grip_ids.includes(result.grip_id))asset.grip_ids.push(result.grip_id);
  savedOptions();el('Saved').value=result.grip_id;link(`${label} · grip JSON`,`/files/prop-assets/${asset.id}/grips/${result.grip_id}.json`);
  status(`Saved “${label}”. This point is ready for scene authoring; grasp motion and collision checks are still required.`);
 });
 el('Show').onclick=()=>action(async()=>{
  const id=el('Saved').value;if(!asset||!asset.grip_ids.includes(id))throw Error('Choose a saved grip.');
  const ticket=epoch;pickEpoch++;draft=null;viewer.cancel();viewer.mark(null);
  const point=await request(`/api/props/${asset.id}/grips/${id}`);if(ticket!==epoch)return;
  const payload=selectionRequest(asset,point.face,point.barycentric);verifyPoint(payload,point);
  draft=payload;el('Label').value=point.label;viewer.mark(point.position_m);
  link(`${point.label} · grip JSON`,`/files/prop-assets/${asset.id}/grips/${id}.json`);status(`Showing saved grip “${point.label}”.`);
 });
 controls();return {choose,reset,snapshot:()=>draft?structuredClone(draft):null};
}
