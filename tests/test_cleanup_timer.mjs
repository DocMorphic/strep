// Synthetic clocks and editor artifacts; no real human review is recorded.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createCleanupSession,startCleanup,pauseCleanup,finishCleanup,recoverCleanup,activeCleanupSeconds,cleanupTrace,validateStoredCleanup,mountCleanupTimer} from '../scripts/cleanup-timer.mjs';
const context={packet_id:'synthetic',manifest_sha256:'a'.repeat(64),clip_id:'clip-001',source_sha256:'b'.repeat(64),review_type:'developer',reviewer_id:'synthetic-test'};
const at='2026-10-09T12:00:00.000Z';

test('explicit active intervals exclude breaks and preserve fractional seconds',()=>{
  const s=createCleanupSession(context,60,'synthetic');startCleanup(s,'page',100,at);pauseCleanup(s,'page',2100.25,at);
  startCleanup(s,'page',100000,at);finishCleanup(s,'page',101000.5,at);
  assert.equal(activeCleanupSeconds(s),3.00075);const trace=cleanupTrace(s);
  assert.equal(trace.preselected_limit_seconds,60);assert.equal(trace.duration_complete,true);
  assert.deepEqual(trace.context,context);assert.equal(trace.quality_approved,false);assert.equal(trace.release_approved,false);
  assert.throws(()=>startCleanup(s,'page',110000,at));assert.throws(()=>finishCleanup(s,'page',110000,at));
});

test('reloading a running timer keeps unknown duration separate from active intervals',()=>{
  const s=createCleanupSession(context,null,'synthetic');startCleanup(s,'old',100,at);pauseCleanup(s,'old',1100,at);
  startCleanup(s,'old',2100,at);recoverCleanup(s,at);assert.equal(activeCleanupSeconds(s),1);
  startCleanup(s,'new',0,at);finishCleanup(s,'new',1000,at);
  const trace=cleanupTrace(s);assert.equal(trace.active_seconds,2);assert.equal(trace.duration_complete,false);assert.equal(trace.interruptions.length,1);
});

test('wrong page, backwards clocks, unsupported context and premature export are rejected',()=>{
  const s=createCleanupSession(context,null,'synthetic');assert.throws(()=>cleanupTrace(s));assert.throws(()=>finishCleanup(s,'page',0,at));
  startCleanup(s,'page',100,at);assert.throws(()=>pauseCleanup(s,'other',200,at));assert.throws(()=>pauseCleanup(s,'page',99,at));
  pauseCleanup(s,'page',200,at);assert.throws(()=>startCleanup(s,'page',199,at));
  for(const limit of [-1,0,NaN,Infinity,true])assert.throws(()=>createCleanupSession(context,limit,'synthetic'));
  assert.throws(()=>createCleanupSession({...context,source_sha256:'changed'},null,'synthetic'));
});

test('malformed restored state cannot crash or manufacture a completed duration',()=>{
  const s=createCleanupSession(context,null,'synthetic');startCleanup(s,'page',100,at);finishCleanup(s,'page',1100,at);
  assert.equal(validateStoredCleanup(structuredClone(s)).state,'finished');
  for(const update of [{segments:null},{release_approved:true},{open:{}},{finished_at:null},{segments:[{page_id:'x',start_ms:3,end_ms:2,started_at:at,ended_at:at}]}])
    assert.throws(()=>validateStoredCleanup({...s,...update}));
});

function timerUI(storage=new Map()){
  const element=tag=>({tag,children:[],value:'',append(...c){this.children.push(...c);},setAttribute(){},click(){}});
  const container=element('section'),measured=[];let time=0,current=context;
  const ui=mountCleanupTimer({container,context:()=>current,onMeasured:(...v)=>measured.push(v),
    storage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},doc:{createElement:element},
    readClock:()=>time,wallClock:()=>at,pageId:'synthetic-page',schedule:()=>1,cancel:()=>{}});
  const buttons=container.children.find(e=>e.tag==='div').children;
  return {ui,storage,measured,buttons,clock:v=>time=v,context:v=>current=v,status:container.children.filter(e=>e.tag==='p').at(-1)};
}

test('actual timer controls do not fill outcomes; measured seconds require Finish',async()=>{
  const t=timerUI();t.ui.bind(context);const [start,pause,finish,use]=t.buttons;
  assert.equal(use.disabled,true);await start.onclick();t.clock(2000);await pause.onclick();
  t.clock(10000);await start.onclick();t.clock(11000);await finish.onclick();await use.onclick();
  assert.deepEqual(t.measured,[[3,null]]);assert.equal(start.disabled,true);
  const saved=JSON.parse([...t.storage.values()][0]);assert.equal(saved.state,'finished');assert.equal(saved.context.reviewer_id,'synthetic-test');
  assert.equal(saved.quality_approved,false);assert.equal(saved.output_artifact,null);t.ui.destroy();
});

test('switching clips pauses the old interval and keeps drafts separate',async()=>{
  const t=timerUI();t.ui.bind(context);await t.buttons[0].onclick();t.clock(500);
  const other={...context,clip_id:'clip-002',source_sha256:'c'.repeat(64)};t.context(other);t.ui.bind(other);
  assert.equal(t.measured.length,0);const old=JSON.parse([...t.storage.values()][0]);
  assert.equal(old.state,'paused');assert.equal(activeCleanupSeconds(old),.5);assert.equal(old.open,null);
  assert.equal(t.buttons[3].disabled,true);t.ui.destroy();
});

test('lost active interval can be exported as partial but cannot fill measured review time',async()=>{
  const s=createCleanupSession(context,null,'synthetic');startCleanup(s,'old-page',100,at);
  const storage=new Map([['strep-cleanup-timer:'+JSON.stringify(context),JSON.stringify(s)]]);
  const t=timerUI(storage);t.ui.bind(context);await t.buttons[0].onclick();t.clock(1000);await t.buttons[2].onclick();
  assert.equal(t.buttons[3].disabled,true);await t.buttons[3].onclick();assert.equal(t.measured.length,0);
  assert.match(t.status.textContent,/unknown duration/);t.ui.destroy();
});
