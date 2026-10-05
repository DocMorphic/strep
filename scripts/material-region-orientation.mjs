const canonical=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const vector=v=>Array.isArray(v)&&v.length===3&&v.every(finite);
const subtract=(a,b)=>a.map((v,i)=>v-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const near=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=1e-10*Math.max(1e-9,Math.abs(a),Math.abs(b));
const vectorNear=(a,b)=>vector(a)&&vector(b)&&a.every((v,i)=>Math.abs(v-b[i])<=1e-12+1e-10*Math.max(Math.abs(v),Math.abs(b[i])));

export function checkedRegionOrientation(value,patch){
 const faces=value?.triangle_vertex_indices,points=patch?.reference_positions_m,n=patch?.face_references?.length;
 if(value?.schema!=='strep-material-region-orientation-v1'||value.coordinate_space!=='character_default_pose_metres'
  ||!Number.isInteger(n)||n<1||n>512||!Array.isArray(points)||points.length<3||points.length>256||!points.every(vector)
  ||!patch.winding||canonical(value.face_references)!==canonical(patch.face_references)||canonical(value.patch_winding)!==canonical(patch.winding)
  ||!Array.isArray(faces)||faces.length!==n||!['triangle_centroids_m','triangle_unit_winding_normals','triangle_twice_areas_m2'].every(k=>Array.isArray(value[k])&&value[k].length===n)
  ||value.complete_triangle_population!==true||value.original_winding_preserved!==true||value.anatomical_review_pending!==true
  ||['animation_sampled','contact_intent_approved','quality_approved','release_approved'].some(k=>value[k]!==false))throw Error('Surface direction preview is incomplete or has changed.');
 const used=new Set();let total=0,center=[0,0,0],anchor=null;
 for(let i=0;i<n;i++){
  const face=faces[i];
  if(!Array.isArray(face)||face.length!==3||face.some(k=>!Number.isInteger(k)||k<0||k>=points.length)||new Set(face).size!==3)throw Error('Surface direction triangle references are invalid.');
  face.forEach(k=>used.add(k));
  const triangle=face.map(k=>points[k]),winding=cross(subtract(triangle[1],triangle[0]),subtract(triangle[2],triangle[0])),area=Math.hypot(...winding);
  const centroid=[0,1,2].map(k=>triangle[0][k]+((triangle[1][k]-triangle[0][k])+(triangle[2][k]-triangle[0][k]))/3);
  if(!finite(area)||area<=patch.selector.minimum_twice_area_m2||!near(area,value.triangle_twice_areas_m2[i])
   ||!vectorNear(centroid,value.triangle_centroids_m[i])||!vectorNear(winding.map(v=>v/area),value.triangle_unit_winding_normals[i]))throw Error('Surface directions do not preserve the displayed triangle winding.');
  anchor??=centroid;center=center.map((v,k)=>v+(centroid[k]-anchor[k])*area);total+=area;
 }
 if(used.size!==points.length||!vectorNear(center.map((v,k)=>anchor[k]+v/total),value.area_weighted_centroid_m))throw Error('Surface direction preview omits selected vertices or changes its center.');
 return structuredClone(value);
}

export function orientationViews(value,patch){
 checkedRegionOrientation(value,patch);
 const origin=patch.reference_positions_m[0],points=patch.reference_positions_m.map(p=>subtract(p,origin)),centers=value.triangle_centroids_m.map(p=>subtract(p,origin));
 const span=Math.max(...[0,1,2].map(k=>Math.max(...points.map(p=>p[k]))-Math.min(...points.map(p=>p[k]))));
 const length=span*.25;
 return [{label:'Front · X/Y',axes:[0,1],sign:[1,1],depth:2},{label:'Side · −Z/Y',axes:[2,1],sign:[-1,1],depth:0},{label:'Top · X/−Z',axes:[0,2],sign:[1,-1],depth:1}].map(view=>{
  const project=p=>view.axes.map((k,i)=>p[k]*view.sign[i]);
  const vertices=points.map(project),arrows=centers.map((p,i)=>({start:project(p),end:project(p.map((v,k)=>v+value.triangle_unit_winding_normals[i][k]*length)),toward:value.triangle_unit_winding_normals[i][view.depth]>=0}));
  const population=[...vertices,...arrows.flatMap(a=>[a.start,a.end])];
  const low=[0,1].map(k=>Math.min(...population.map(p=>p[k]))),high=[0,1].map(k=>Math.max(...population.map(p=>p[k])));
  const scale=Math.min(264/Math.max(high[0]-low[0],span*1e-6),156/Math.max(high[1]-low[1],span*1e-6));
  const center=low.map((v,k)=>(v+high[k])/2),screen=p=>[160+(p[0]-center[0])*scale,116-(p[1]-center[1])*scale];
  return {label:view.label,vertices:vertices.map(screen),triangles:value.triangle_vertex_indices.map(face=>face.map(k=>screen(vertices[k]))),arrows:arrows.map(a=>({...a,start:screen(a.start),end:screen(a.end)}))};
 });
}

export function renderRegionOrientation(document,container,value,patch){
 const node=(tag,attrs={},text)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;return el;};
 const views=orientationViews(value,patch),svgs=[];
 for(const view of views){
  const svg=node('svg',{viewBox:'0 0 320 220',role:'img','aria-label':`${view.label}; default-pose triangles and winding directions`,style:'width:100%;max-width:360px;border:1px solid #8095ac55;border-radius:12px;background:#101827'});
  svg.append(node('title',{},`${view.label}: every selected triangle, vertex index and winding direction`),node('text',{x:16,y:22,fill:'#e2e8f0','font-size':12},view.label));
  for(const triangle of view.triangles)svg.append(node('polygon',{points:triangle.map(p=>p.join(',')).join(' '),fill:'#2dd4bf33',stroke:'#7dd3fc88','stroke-width':.7}));
  for(const arrow of view.arrows){
   const [x,y]=arrow.start,[ex,ey]=arrow.end,dx=ex-x,dy=ey-y,magnitude=Math.hypot(dx,dy);
   if(magnitude<1e-6){
    svg.append(node('circle',{cx:x,cy:y,r:2.5,fill:arrow.toward?'#fbbf24':'none',stroke:'#fbbf24','stroke-width':1}));
    if(!arrow.toward)svg.append(node('path',{d:`M ${x-2},${y-2} L ${x+2},${y+2} M ${x+2},${y-2} L ${x-2},${y+2}`,stroke:'#fbbf24','stroke-width':1}));
   }else{
    const ux=dx/magnitude,uy=dy/magnitude;
    svg.append(node('line',{x1:x,y1:y,x2:ex,y2:ey,stroke:'#fbbf24','stroke-width':1.1}),node('path',{d:`M ${ex-ux*5-uy*2.5},${ey-uy*5+ux*2.5} L ${ex},${ey} L ${ex-ux*5+uy*2.5},${ey-uy*5-ux*2.5}`,fill:'none',stroke:'#fbbf24','stroke-width':1.1}));
   }
  }
  view.vertices.forEach(([x,y],i)=>svg.append(node('circle',{cx:x,cy:y,r:1.8,fill:'#e2e8f0'}),node('text',{x:x+3,y:y-3,fill:'#e2e8f0','font-size':8},String(i))));
  svg.append(node('text',{x:16,y:207,fill:'#94a3b8','font-size':10},'Default pose · arrows follow original winding'));
  svgs.push(svg);
 }
 container.replaceChildren(...svgs);
 return views;
}
