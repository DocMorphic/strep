// Execute the actual page's form and export handlers with a synthetic DOM.
// No renderer, server, browser, rating file or human evidence is created.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
import {reviewIdentity,reviewExport} from '../scripts/review-identity.js';

const html=fs.readFileSync(new URL('../scripts/human-review.html',import.meta.url),'utf8');
function part(start,end) {
  const i=html.indexOf(start),j=html.indexOf(end,i+start.length);
  assert.ok(i>=0&&j>i,`Page code boundary changed: ${start}`);
  assert.equal(html.indexOf(start,i+start.length),-1,`Ambiguous page boundary: ${start}`);
  return html.slice(i,j);
}
const draftCode=part('const fields=','const canvas=');
const formCode=part("$('reviewForm').onsubmit=",'function tick(');
const initCode=part("try{const response=await fetch('manifest.json')",'</script>');
const categories=['action','weight_balance','coordination_timing','contacts_collisions','starts_ends'];

async function page(role,storage=new Map(),context={}) {
  const manifest={packet_id:'synthetic-form-test',instructions:'Synthetic fixture only',
    cases:[{id:'clip-001',review_context:context}]};
  if(role!==undefined)manifest.review_type=role;
  const elements=new Map(),downloads=[],blobs=[];
  const element=id=>{
    if(!elements.has(id))elements.set(id,{value:'',checked:false,textContent:'',readOnly:false,
      addEventListener(){},replaceChildren(...options){this.options=options;}});
    return elements.get(id);
  };
  const sandbox={reviewIdentity,reviewExport,TextDecoder,Blob,crypto:webcrypto,console,
    document:{title:'',getElementById:element,createElement(){return {click(){downloads.push(this.download);}};}},
    localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
    URL:{createObjectURL(blob){blobs.push(blob);return 'blob:synthetic';},revokeObjectURL(){}},
    Option:function(text,value){this.text=text;this.value=value;},setTimeout(){},
    fetch:async()=>({ok:true,arrayBuffer:async()=>new TextEncoder().encode(JSON.stringify(manifest)).buffer})};
  const ctx=vm.createContext(sandbox);
  vm.runInContext(`const $=id=>document.getElementById(id),labels=${JSON.stringify(Object.fromEntries(categories.map(k=>[k,k])))};
    let manifest,digest,key,identity,state={drafts:{},reviews:{},reviewer:'',human:false},selected=null;
    async function load(){selected=manifest.cases[0];}
    ${draftCode}
    ${formCode}`,ctx);
  await vm.runInContext(`(async()=>{${initCode}})()`,ctx);
  return {ctx,element,downloads,blobs,storage,manifest,
    count:()=>vm.runInContext('Object.keys(state.reviews).length',ctx),
    save:()=>element('reviewForm').onsubmit({preventDefault(){}}),
    export:()=>element('export').onclick()};
}

const storage=new Map();
for(const role of [undefined,'developer']) {
  const p=await page(role,storage);
  const expected=reviewIdentity(p.manifest);
  assert.equal(p.element('reviewTitle').textContent,expected.title);
  assert.equal(p.element('attestation').textContent,expected.attestation);
  assert.equal(p.count(),0);
  p.element('reviewer').value=' synthetic-reviewer ';p.element('reviewer').oninput();
  for(const k of categories)p.element('score-'+k).value='4';
  p.element('defect').value='no';p.element('confidence').value='medium';p.element('cleanup').value='not_performed';
  p.save();assert.equal(p.count(),0);assert.equal(p.element('status').textContent,expected.error);
  p.export();assert.equal(p.downloads.length,0);
  p.element('human').checked=true;p.element('human').onchange();
  p.save();assert.equal(p.count(),1);assert.equal(p.element('reviewer').readOnly,true);
  p.export();assert.equal(p.downloads.length,1);
  const response=JSON.parse(await p.blobs[0].text());
  assert.equal(response.schema,expected.schema);assert.equal(response.reviewer_id,'synthetic-reviewer');
  assert.equal(response.packet_id,p.manifest.packet_id);
  assert.equal(response.reviews[0].cleanup.status,'not_performed');
  assert.equal(response.reviews[0].cleanup.active_seconds,null);
  assert.match(response.manifest_sha256,/^[a-f0-9]{64}$/);
  assert.deepEqual(Object.fromEntries(Object.keys(expected.fields).map(k=>[k,response[k]])),expected.fields);
  assert.equal(p.downloads[0],`${expected.prefix}-${p.manifest.packet_id}.json`);
  const savedKey=[...storage.keys()].find(k=>k===`${expected.prefix}:${response.manifest_sha256}`);
  assert.ok(savedKey,'Actual page storage uses the declared role prefix');
  const reloaded=await page(role,storage);
  assert.equal(reloaded.count(),1);assert.equal(reloaded.element('reviewer').value,' synthetic-reviewer ');
}
assert.equal(storage.size,2,'Independent and developer drafts are separate');

const limited=await page('developer',new Map(),{unavailable_categories:{contacts_collisions:'Partner absent'}});
limited.element('reviewer').value='synthetic';limited.element('human').checked=true;
for(const k of categories)limited.element('score-'+k).value='4';
limited.element('defect').value='no';limited.element('confidence').value='high';limited.element('cleanup').value='not_performed';
limited.save();assert.equal(limited.count(),0);assert.match(limited.element('status').textContent,/scene evidence is absent/);
limited.element('score-contacts_collisions').value='na';limited.element('na-contacts_collisions').value='Cannot see absent partner';
limited.element('cleanup').value='time_limit';limited.element('seconds').value='59';limited.element('limit').value='60';limited.element('operations').value='Synthetic fixture edit';
limited.save();assert.equal(limited.count(),0);assert.match(limited.element('status').textContent,/reached the stated limit/);
limited.element('seconds').value='60';limited.save();assert.equal(limited.count(),1);
limited.export();const response=JSON.parse(await limited.blobs[0].text());
assert.equal(response.reviews[0].scores.contacts_collisions,null);
assert.equal(response.reviews[0].cleanup.status,'time_limit');assert.equal(response.reviews[0].cleanup.active_seconds,60);
assert.equal(response.independent_human,false);assert.equal(response.release_approved,false);
console.log('Actual packet form save, reload, N/A, cleanup and role-specific export passed');
