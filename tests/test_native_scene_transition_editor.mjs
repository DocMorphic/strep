import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeSceneTransitionEditor,stagedTransition} from '../scripts/native-scene-transition-editor.mjs';
import {createNativeSceneGameEditor} from '../scripts/native-scene-game-editor.mjs';
class Element{constructor(){this.value='';this.children=[];this.checked=false;this.disabled=false;this.textContent='';}replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}append(...items){this.children.push(...items);}}
const html=await readFile(new URL('../scripts/native-scene-transition-editor.html',import.meta.url),'utf8').then(x=>x.replace(/\r\n/g,'\n'));const nodes=new Map();
for(const m of html.matchAll(/<[^>]*id="(nativeSceneTransition[^"]+)"[^>]*>/g)){const item=new Element();item.value=m[0].match(/value="([^"]*)"/)?.[1]??'';item.disabled=m[0].includes('disabled');nodes.set(m[1],item);}
const doc={getElementById:id=>nodes.get(id),createElement:()=>new Element()},el=n=>nodes.get('nativeSceneTransition'+n);
const source={folder:'saved/transition',result_sha256:'a'.repeat(64)},inspection={source,actors:['A','B'],objects:['box'],duration_s:1.2,bridge_interval_s:[.4,.6],checks:{contacts:false,objects:true},timeline_mapping:[{}],times_s:[0,.4,.5,.6,1.2],floor:null,original_selected:true,quality_approved:false,release_approved:false};
const draft={schema:'strep-studio-native-scene-v1',scene:{duration_s:1.2,actors:Object.fromEntries(['A','B'].map(n=>[n,{glb:`/files/native-scene-transition-jobs/stage1/transition/actors/${n}.glb`,sha256:'b'.repeat(64),animation_index:3}])),objects:{box:{}},contacts:[{}]},geometry:{},object_edit:null};
const game={schema:'strep-native-scene-game-tracks-v1',actors:{A:{root_node:0},B:{root_node:3}},markers:[{id:'reaction',name:'react',actor:'B',time_s:.5,confirmed:false}]};
const labels=['result.json','stage-draft.json','stage-game-tracks.json','transition/result.json','transition/events.json','transition/contacts.json','transition/roots.json','transition/actors/A.glb','transition/actors/B.glb'];
const review={id:'stage1',status:'complete',result_sha256:'c'.repeat(64),original_selected:true,staging_conditions_pass:true,source_conditions_pass:false,studio_selection_changed:false,quality_approved:false,training_admitted:false,release_approved:false,engine_playback_verified:false,draft,game_tracks:game,downloads:labels.map(label=>({label,url:`/files/native-scene-transition-jobs/stage1/${label}`,sha256:label.endsWith('.glb')?'b'.repeat(64):'d'.repeat(64)}))};
assert.deepEqual(stagedTransition(review).draft,draft);
for(const mutate of [r=>r.quality_approved=true,r=>r.original_selected=1,r=>r.game_tracks.markers[0].confirmed=true,r=>r.downloads.pop(),r=>r.downloads[0].url='https://bad.test/x',r=>r.downloads[0].sha256='bad',r=>r.draft.scene.actors.A.animation_index=true,r=>r.downloads.at(-1).sha256='f'.repeat(64)]){const r=structuredClone(review);mutate(r);assert.throws(()=>stagedTransition(r));}
let staged=null,queued=null,waiting=null,posts=[];
const editor=createNativeSceneTransitionEditor({document:doc,api:()=>{throw Error('Unexpected GET');},post:async(url,payload)=>{posts.push([url,structuredClone(payload)]);return waiting??structuredClone(url.endsWith('inspect')?inspection:review);},setDraft:x=>staged=structuredClone(x),queueGameTracks:x=>queued=structuredClone(x)});
el('Folder').value=source.folder;el('Hash').value=source.result_sha256;await el('Stage').onclick();assert.match(el('Status').textContent,/Inspect/);assert.equal(posts.length,0);
await el('Inspect').onclick();assert.match(el('Status').textContent,/contacts fail/);assert.equal(el('Stage').disabled,false);
await el('Stage').onclick();assert.equal(staged,null);assert.equal(queued,null);assert.match(el('Results').children[0].textContent,/conditions: fail/);assert.equal(posts.at(-1)[1].geometry.planes.floor,undefined);
await el('Apply').onclick();assert.deepEqual(staged,draft);assert.deepEqual(queued.request,game);assert.equal(queued.actor_hashes.B.animation_index,3);
el('Folder').value='other';el('Folder').oninput();await el('Apply').onclick();assert.match(el('Status').textContent,/Save a separate/);
el('Folder').value=source.folder;let resolve;waiting=new Promise(r=>resolve=r);const pending=el('Inspect').onclick();el('Folder').value='changed';el('Folder').oninput();resolve(inspection);await pending;assert.match(el('Status').textContent,/selection changed/);assert.equal(el('Stage').disabled,true);waiting=null;
// Timing stays queued until exact source clips and audited times are bound.
const gh=await readFile(new URL('../scripts/native-scene-game-editor.html',import.meta.url),'utf8');const gn=new Map();
for(const m of gh.matchAll(/<[^>]*id="(nativeSceneGame[^"]+)"[^>]*>/g))gn.set(m[1],new Element());gn.set('nativeSceneJobs',new Element());gn.get('nativeSceneJobs').value='built-scene';
const metadata={scene_job:'built-scene',source_result_sha256:'e'.repeat(64),times_s:[0,.5,1.2],actors:{A:{glb_sha256:'b'.repeat(64),animation_index:3,joints:[{node:0}]},B:{glb_sha256:'b'.repeat(64),animation_index:3,joints:[{node:3}]}}};
const ge=createNativeSceneGameEditor({document:{getElementById:id=>gn.get(id),createElement:()=>new Element()},api:async()=>structuredClone(metadata)});
ge.queueTransition(queued);assert.throws(()=>ge.snapshot(),/Bind/);await gn.get('nativeSceneGameBind').onclick();assert.deepEqual(ge.snapshot().request,game);
const invalid=structuredClone(queued);invalid.request.markers[0].confirmed=true;assert.throws(()=>ge.queueTransition(invalid));
ge.queueTransition(queued);metadata.actors.B.animation_index=4;await gn.get('nativeSceneGameBind').onclick();assert.match(gn.get('nativeSceneGameStatus').textContent,/different scene clips/);metadata.actors.B.animation_index=3;
ge.queueTransition(queued);metadata.times_s=[0,1.2];await gn.get('nativeSceneGameBind').onclick();assert.match(gn.get('nativeSceneGameStatus').textContent,/clock or participants changed/);
const studio=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8').then(x=>x.replace(/\r\n/g,'\n'));assert(studio.includes(html));assert(studio.includes("import('/native-scene-transition-editor.mjs')"));assert(studio.includes('nativeSceneGameEditor.queueTransition(value)'));
console.log('Shared transition staging, retained failures, typed downloads, stale selection and unconfirmed exact-clip timing passed offline.');
