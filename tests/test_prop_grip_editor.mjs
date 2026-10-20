import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createPropGripEditor,validateGeometry,selectionRequest} from '../scripts/prop-grip-editor.mjs';
class Element{constructor(){this.value='';this.children=[];this.files=[];}replaceChildren(...a){this.children=a;this.value=a[0]?.value??'';}append(...a){this.children.push(...a);}}
const nodes=new Map(),html=await readFile(new URL('../scripts/prop-grip-editor.html',import.meta.url),'utf8');
for(const [,id] of html.matchAll(/id="(propGrip[^"]+)"/g)){assert(!nodes.has(id));nodes.set(id,new Element());}
const el=s=>nodes.get('propGrip'+s),document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const id='a'.repeat(64),digest='b'.repeat(64),grip='c'.repeat(64);
const asset={id,geometry_sha256:digest,name:'Object <script>',inventory:{vertices:3,faces:1},grip_ids:[]};
const geometry={asset_id:id,geometry_sha256:digest,vertices_m:[[0,0,0],[1,0,0],[0,1,0]],faces:[[0,1,2]]};
let calls=[],shown=[],marked=[],waitPreview=null,waitSave=null,saved=null;
const point=p=>({source_sha256:id,geometry_sha256:digest,face:p.face,barycentric:p.barycentric,position_m:[.3,.5,0],winding_normal:[0,0,1],contact_verified:false,outward_normal_verified:false});
const request=async(url,options)=>{calls.push({url,options});const p=options?.headers?.['Content-Type']==='application/json'?JSON.parse(options.body):null;
 if(url==='/api/props/import'||url===`/api/props/${id}`)return structuredClone(asset);
 if(url.endsWith('/geometry'))return structuredClone(geometry);
 if(url.endsWith('/surface-preview'))return waitPreview||point(p);
 if(url==='/api/props/grips'){saved={...point(p),label:p.label};return waitSave||{grip_id:grip,selection:saved};}
 if(url.endsWith('/grips/'+grip))return saved;
 throw Error(url);
};
const viewer={clear(){shown=[];},show(g){shown.push(g);},mark(p){marked.push(p);},cancel(){},home(){},pick(fn){this.callback=fn;}};
const editor=createPropGripEditor({document,request,viewer});
assert.equal(el('Save').disabled,true);el('Asset').value=id;await el('Open').onclick();assert.equal(shown.length,1);assert.equal(el('Pick').disabled,false);
await editor.choose(0,[.2,.3,.5]);assert.deepEqual(editor.snapshot(),selectionRequest(asset,0,[.2,.3,.5]));assert.equal(el('Save').disabled,false);
el('Label').value='Left hand';await el('Save').onclick();assert.match(el('Status').textContent,/Saved/);assert.equal(el('Downloads').children.at(-1).href,`/files/prop-assets/${id}/grips/${grip}.json`);
await el('Show').onclick();assert.equal(el('Label').value,'Left hand');assert.deepEqual(marked.at(-1),[.3,.5,0]);
for(const bad of [[-1,.5,1.5],[NaN,0,1],[0,0,0],[true,0,0]])assert.throws(()=>selectionRequest(asset,0,bad));
assert.throws(()=>selectionRequest(asset,1,[1,0,0]));assert.throws(()=>validateGeometry(asset,{...geometry,asset_id:'d'.repeat(64)}));assert.throws(()=>validateGeometry(asset,{...geometry,faces:[[0,1,3]]}));
let resolve;waitPreview=new Promise(r=>resolve=r);const pending=editor.choose(0,[1,0,0]);el('Asset').value='d'.repeat(64);el('Asset').oninput();resolve(point({face:0,barycentric:[1,0,0]}));await pending;assert.equal(editor.snapshot(),null);assert.equal(el('Save').disabled,true);waitPreview=null;
el('Asset').value=id;await el('Open').onclick();let firstResolve;waitPreview=new Promise(r=>firstResolve=r);const first=editor.choose(0,[1,0,0]);waitPreview=null;await editor.choose(0,[0,1,0]);firstResolve(point({face:0,barycentric:[1,0,0]}));await first;assert.deepEqual(editor.snapshot().barycentric,[0,1,0]);
let saveResolve;waitSave=new Promise(r=>saveResolve=r);const saving=el('Save').onclick();el('Asset').oninput();saveResolve({grip_id:grip,selection:saved});await saving;assert.equal(el('Downloads').children.length,0);assert.equal(editor.snapshot(),null);waitSave=null;
el('File').files=[{name:'Box.glb',size:12}];el('License').value='My own object';await el('Import').onclick();assert.equal(calls.find(c=>c.url==='/api/props/import').options.headers['X-License-Note'],'My%20own%20object');assert.equal(shown.length,1);
const before=calls.length;el('File').files=[{name:'bad.glb',size:33*1024**2}];await el('Import').onclick();assert.equal(calls.length,before);assert.match(el('Status').textContent,/32 MiB/);
console.log('Prop editor: import, reopen, exact surface selection, save/download, stale requests, racing picks, labels and size rejection pass.');
