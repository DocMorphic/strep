import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {activeGenerationStatus,generationJobMessage,activityMessage,renderJobList} from '../scripts/generation-job-status.mjs';

function element(){return {children:[],append(...nodes){this.children.push(...nodes);},replaceChildren(){this.children=[];}};}
function fixture(){const container=element();container.ownerDocument={createElement:element};return container;}
const deferred={id:'action-jobs/clock',kind:'generation',status:'deferred',can_retry:true,ready:false};

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
  const nodes={systemState:{},activityTitle:{},jobList:fixture(),formStatus:{}};
  const requests=[];let callback,refreshes=0;
  const context={window:{addEventListener(type,fn){assert.equal(type,'strep:jobs');callback=fn;}},
    $(id){assert.ok(id in nodes,'Composer/preview must not be read during saved retry');return nodes[id];},
    activityMessage,renderJobList,generationJobMessage,pendingJob:null,
    async json(path,options){requests.push({path,...options});return {...deferred,id:'action-jobs/retry',status:'waiting_resources'};},
    async refresh(){refreshes++;}};
  vm.runInNewContext(lines[0],context);
  callback({detail:{studies:[deferred],busy:false}});
  assert.match(nodes.activityTitle.textContent,/not started/);
  await nodes.jobList.children[0].children[2].onclick();
  assert.equal(requests.length,1);assert.equal(requests[0].path,'/api/jobs/retry');
  assert.equal(requests[0].method,'POST');assert.deepEqual(JSON.parse(requests[0].body),{job:deferred.id});
  assert.equal(context.pendingJob,'action-jobs/retry');assert.equal(refreshes,1);
  assert.match(nodes.formStatus.textContent,/Waiting for free memory/);
});
