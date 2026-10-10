import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {activeGenerationStatus,generationAvailabilityMessage,generationJobMessage,activityMessage,renderJobList} from '../scripts/generation-job-status.mjs';

function element(){return {children:[],append(...nodes){this.children.push(...nodes);},replaceChildren(){this.children=[];}};}
function fixture(){const container=element();container.ownerDocument={createElement:element};return container;}
const deferred={id:'action-jobs/clock',kind:'generation',status:'deferred',can_retry:true,ready:false};
function embedded(page){
  const start='// strep job status begin:',end='// strep job status end';
  const begin=page.indexOf(start),finish=page.indexOf(end);
  assert.ok(begin>=0&&finish>begin);assert.equal(page.lastIndexOf(start),begin);
  return page.slice(begin,finish);
}

test('waiting is active; deferred preserves saved intent and is terminal',()=>{
  assert.ok(activeGenerationStatus('waiting_resources'));assert.ok(!activeGenerationStatus('deferred'));
  assert.match(generationJobMessage(deferred),/Not started/);
  assert.match(activityMessage([{status:'waiting_resources'}],true),/Waiting for free memory/);
});

test('retry uses saved job identity once while pending and disables during other work',async()=>{
  const container=fixture();const called=[];let release;
  renderJobList(container,[deferred],false,async id=>{called.push(id);await new Promise(r=>release=r);});
  const button=container.children[0].children[2];const pending=button.onclick();
  assert.equal(button.disabled,true);await button.onclick();assert.deepEqual(called,['action-jobs/clock']);
  release();await pending;assert.equal(button.disabled,false);
  renderJobList(container,[deferred],true,async id=>called.push(id));
  await container.children[0].children[2].onclick();assert.equal(called.length,1);
});

test('only eligible deferred generation has retry; motion output never created by rendering',()=>{
  const container=fixture();renderJobList(container,[deferred,{...deferred,id:'action-jobs/failed',status:'failed'},
    {...deferred,id:'action-jobs/denied',can_retry:false},{id:'contact-jobs/a',kind:'contact_check',status:'checked'}],false,()=>{});
  assert.deepEqual(container.children.map(row=>row.children.length),[3,2,2,2]);
  assert.match(container.children[3].children[1].textContent,/no animation created/);
});

test('rebuilt Studio callback retries the saved identity without reading composer or preview',async()=>{
  const page=fs.readFileSync(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
  const lines=page.split(/\r?\n/).filter(line=>line.startsWith("window.addEventListener('strep:jobs'"));
  assert.equal(lines.length,1);
  const nodes={systemState:{},activityTitle:{},jobList:fixture(),formStatus:{},generate:{},generationAvailability:{}};
  const requests=[];let callback,refreshes=0;
  const context={window:{addEventListener(type,fn){assert.equal(type,'strep:jobs');callback=fn;}},
    $(id){assert.ok(id in nodes,'Composer/preview must not be read during saved retry');return nodes[id];},
    activityMessage,renderJobList,generationJobMessage,generationAvailabilityMessage,pendingJob:null,
    async json(path,options){requests.push({path,...options});return {...deferred,id:'action-jobs/retry',status:'waiting_resources'};},
    async refresh(){refreshes++;}};
  vm.runInNewContext(embedded(page)+'\n'+lines[0],context);
  callback({detail:{studies:[deferred],busy:false}});
  assert.match(nodes.activityTitle.textContent,/not started/);
  await nodes.jobList.children[0].children[2].onclick();
  assert.equal(requests.length,1);assert.equal(requests[0].path,'/api/jobs/retry');
  assert.equal(requests[0].method,'POST');assert.deepEqual(JSON.parse(requests[0].body),{job:deferred.id});
  assert.equal(context.pendingJob,'action-jobs/retry');assert.equal(refreshes,1);
  assert.match(nodes.formStatus.textContent,/Waiting for free memory/);
});

test('unlisted owned work explains disabled generation without claiming a saved request',()=>{
  assert.match(generationAvailabilityMessage(true),/Another local job/);
  assert.match(generationAvailabilityMessage(true),/keep editing this draft/);
  assert.doesNotMatch(generationAvailabilityMessage(true),/saved|queued|Waiting for free memory/);
  assert.match(generationAvailabilityMessage(false),/^Runs locally/);
});

test('actual job event updates availability without touching draft or pending-result feedback',()=>{
  const page=fs.readFileSync(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
  assert.match(page, /id="generate"[^>]*aria-describedby="generationAvailability"/);
  assert.match(page, /id="generationAvailability"[^>]*role="status"/);
  const line=page.split(/\r?\n/).find(l=>l.startsWith("window.addEventListener('strep:jobs'"));
  const nodes={systemState:{},activityTitle:{},jobList:fixture(),formStatus:{textContent:'Saved request feedback'},generate:{},generationAvailability:{}};
  let callback;
  vm.runInNewContext(embedded(page)+'\n'+line,{window:{addEventListener(type,fn){callback=fn;}},
    $(id){assert.ok(id in nodes,'Availability must not read or rewrite the composer draft');return nodes[id];},
    activityMessage,renderJobList,generationJobMessage,generationAvailabilityMessage,pendingJob:'action-jobs/preserved'});
  callback({detail:{studies:[],busy:true}});
  assert.equal(nodes.generate.disabled,true);assert.match(nodes.generationAvailability.textContent,/Another local job/);
  assert.equal(nodes.formStatus.textContent,'Saved request feedback');
  callback({detail:{studies:[],busy:false}});
  assert.equal(nodes.generate.disabled,false);assert.match(nodes.generationAvailability.textContent,/Runs locally/);
  assert.equal(nodes.formStatus.textContent,'Saved request feedback');
});

test('raw desktop document includes exact status helper and does not require its newer server route',()=>{
  const page=fs.readFileSync(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
  const helper=fs.readFileSync(new URL('../scripts/generation-job-status.mjs',import.meta.url),'utf8').replace(/\r\n/g,'\n').replace(/export /g,'');
  assert.ok(embedded(page).replace(/\r\n/g,'\n').includes(helper));
  assert.doesNotMatch(page,/from ['"]\/generation-job-status\.mjs['"]/);
});
