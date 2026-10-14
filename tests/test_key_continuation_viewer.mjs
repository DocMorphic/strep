import assert from 'node:assert/strict';
import {createKeyContinuationComparison} from '../scripts/key-continuation-viewer.mjs';
class Element{constructor(){this.value='';this.textContent='';this.disabled=false;}replaceChildren(...v){this.children=v;this.value=v[0]?.value??'';}}
const nodes=new Map(['version','play','time','fit','preview','clock','decision','status'].map(n=>[n,new Element()]));
const document={getElementById:n=>nodes.get(n),createElement:()=>new Element()},el=n=>nodes.get(n),sha='a'.repeat(64),id='keys-one';
const review={schema:'strep-studio-key-continuation-review-v1',id,status:'complete',completion_sha256:sha,full_replay_pass:true,sampled_conditions_pass:false,rate_failures:41,floor_failures:17,original_selected:true,quality_approved:false,release_approved:false,
 downloads:['input/saved-start.glb','study/probes/final/character.glb','study/result.json','replay/result.json'].map(n=>({url:`/files/key-continuation-jobs/${id}/${n}`,label:n,sha256:sha}))};
review.previews=review.downloads.slice(0,2).map((d,i)=>({id:i?'candidate':'source',label:i?'Returned proposal':'Saved starting clip',kind:'native_key_continuation',preview_url:d.url,preview_sha256:d.sha256,animation_index:1,animation_count:2,preview_start_s:.1,preview_end_s:3.96}));
let response=review,created=0,clock,loads=[],seeks=[],paused=0,fit=0;
const factory=async options=>{created++;clock=options.onTime;return {pause(){paused++;},async load(v,o){loads.push([v.id,o]);clock(v.preview_end_s);},seek(t){seeks.push(t);clock(t);},fit(){fit++;},toggle(){}};};
const make=()=>createKeyContinuationComparison({document,id,completion:sha,api:async url=>{assert.equal(url,`/api/key-continuation-preview?id=${id}&completion=${sha}`);return response;},createPlayer:factory});
const viewer=make();await viewer.init();assert.equal(created,1);assert.deepEqual(loads,[['source',{fitView:true}]]);assert.equal(seeks.at(-1),.1);assert.match(el('decision').textContent,/41.*17.*fails acceptance.*Original remains selected/);
clock(2.3);el('version').value='candidate';await el('version').onchange();assert.deepEqual(loads.at(-1),['candidate',{fitView:false}]);assert.equal(seeks.at(-1),2.3);assert.equal(created,1);
el('time').value='1.75';el('time').oninput();assert.equal(seeks.at(-1),1.75);el('fit').onclick();assert.equal(fit,1);viewer.pause();assert(paused>0);
el('play').onclick();assert.equal(el('play').textContent,'Pause');clock(review.previews[0].preview_end_s);assert.equal(el('play').textContent,'Play');el('play').onclick();assert.equal(el('play').textContent,'Pause');
for(const fault of ['digest','clock','index','url','approval','incomplete']){
 response=structuredClone(review);
 if(fault==='digest')response.completion_sha256='b'.repeat(64);
 else if(fault==='clock')response.previews[1].preview_end_s=4;
 else if(fault==='index')response.previews[1].animation_index=2;
 else if(fault==='url')response.previews[1].preview_url+='?changed';
 else if(fault==='approval')response.quality_approved=true;
 else {response.status='failed';response.downloads=[];}
 const before=created;await make().init();assert.equal(created,before);assert(el('play').disabled);assert.match(el('status').textContent,/unavailable/);
}
console.log('Continuation comparison binding, appended clips, same-clock/camera switching and rejection checks passed.');
