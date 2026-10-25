import assert from 'node:assert/strict';
import {createSurfaceClipComparison} from '../scripts/surface-clip-viewer.mjs';
class Element{constructor(){this.value='';this.disabled=true;this.children=[];}replaceChildren(...v){this.children=v;}append(v){this.children.push(v);}}
const nodes=new Map(['version','play','time','fit','view','clock','status'].map(id=>[id,new Element()]));
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()},el=id=>nodes.get(id),job='a'.repeat(32),attempt='b'.repeat(32);
const base={id:job,attempt,quality_approved:false,release_approved:false,result:{status:'checkpointed',total_keys:11,validated_through:2,quality_approved:false,release_approved:false,transition_review_required:true},
 versions:['original','candidate','rejected'].map(role=>({label:role,kind:'native_surface_correction',preview_url:`/files/surface-clip-jobs/${job}/${attempt}/${role}.glb`,preview_sha256:'c'.repeat(64),preview_start_s:0,preview_end_s:2,animation_index:0,animation_count:1}))};
let response=base,created=0,onTime,loads=[],seeks=[],fits=0,toggles=0;
const createPlayer=async options=>{created++;onTime=options.onTime;return {pause(){},seek(t){seeks.push(t);onTime(t);},fit(){fits++;},toggle(){toggles++;},async load(v,o){loads.push([v.label,o]);onTime(0);}};};
const make=()=>createSurfaceClipComparison({document,job,attempt,createPlayer,api:async url=>{assert.equal(url,`/api/surface-clip-jobs/${job}/attempt/${attempt}`);return response;}});
await make().init();assert.equal(created,1);assert.deepEqual(loads[0],['original',{fitView:true}]);assert.match(el('status').textContent,/3\/11/);
onTime(1.25);el('version').value='1';await el('version').onchange();assert.deepEqual(loads.at(-1),['candidate',{fitView:false}]);assert.equal(seeks.at(-1),1.25);
el('time').value='.9';el('time').oninput();assert.equal(seeks.at(-1),.9);el('fit').onclick();el('play').onclick();assert.equal(fits,1);assert.equal(toggles,1);
for(const mutate of [s=>s.quality_approved=true,s=>s.versions.reverse(),s=>s.versions[1].preview_end_s=3,s=>s.versions[1].preview_url=s.versions[0].preview_url,s=>s.versions[1].animation_count=2,s=>s.result.validated_through=11,s=>s.versions[1].preview_url+='?x=1']){
 response=structuredClone(base);mutate(response);await make().init();assert.equal(created,1);assert.equal(el('play').disabled,true);
}
console.log('Ground-contact comparison: original first, exact assets, shared time/camera, controls and malformed descriptor rejection pass.');
