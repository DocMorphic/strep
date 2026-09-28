const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto, createHash} = require('node:crypto');
const root = path.resolve(__dirname, '..');
// Small DOM sink: integration, layout and native disclosure behavior are checked in Studio.
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.value = ''; }
  set textContent(value) { this.value = value; this.children = []; }
  get textContent() { return this.value + this.children.map(x => x.textContent).join('\n'); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.value = ''; this.children = items; }
  all(tag) { return this.children.flatMap(x => [...(x.tag === tag ? [x] : []), ...x.all(tag)]); }
}
function harness(fetch) {
  const host = new Element('details'), summary = new Element('summary'), body = new Element('div');
  host.append(summary, body); host.querySelector = q => q === 'summary' ? summary : body;
  const context = vm.createContext({document: {createElement: tag => new Element(tag)}, location: {origin:'http://localhost'}, URL, fetch, AbortController, TextDecoder, Uint8Array, crypto: webcrypto});
  vm.runInContext(fs.readFileSync(path.join(root, 'scripts/generation-history.js'), 'utf8'), context);
  return {host, panel: context.createGenerationHistoryPanel(host)};
}
const transition = '20260928-031815-5d1de71d', edited = '20260928-031826-b8ebef83';
function job(id) { return {id, result: JSON.parse(fs.readFileSync(path.join(root,'reports/rig-jobs',id,'result.json')))}; }
function savedResponse(url) {
  const file = path.join(root, 'reports', new URL(url).pathname.slice('/files/'.length));
  const bytes = fs.readFileSync(file);
  return {ok:true, arrayBuffer:async()=>bytes};
}
test('real transition and retimed descendant retain distinct original profiles and copy counts', async () => {
  const {host,panel} = harness(savedResponse);
  await panel.show(job(transition));
  assert.equal(host.all('article').length,2);
  for (const text of ['Mobility: 100','Mobility: 0','Seed 301','2 retained copies','4 seconds requested']) assert.ok(host.textContent.includes(text));
  await panel.show(job(edited));
  assert.equal(host.all('article').length,2);
  assert.ok(!host.textContent.includes('2 retained copies'));
  for (const a of host.all('a')) assert.ok(a.href.startsWith(`http://localhost/files/rig-jobs/${edited}/`));
});
test('late response cannot replace a newly selected result or cleared reference', async () => {
  let release;
  const {host,panel} = harness(url => url.includes(transition) && url.endsWith('generation-sources.json') ? new Promise(resolve=>{release=()=>resolve(savedResponse(url));}) : savedResponse(url));
  const old = panel.show(job(transition));
  await panel.show({id:'older',result:{}}); release(); await old;
  assert.ok(host.textContent.includes('older package')); assert.equal(host.all('article').length,0);
  const pending = panel.show(job(transition)); panel.clear(); release(); await pending;
  assert.equal(host.hidden,true); assert.equal(host.all('article').length,0);
});
test('index and metadata corruption are rejected without presenting original profiles', async () => {
  for (const target of ['generation-sources.json','generation-record.json']) {
    const {host,panel} = harness(url => url.endsWith(target) ? {ok:true,arrayBuffer:async()=>Buffer.from('{}')} : savedResponse(url));
    await panel.show(job(transition));
    assert.ok(host.textContent.includes('checksum'));
    assert.ok(!host.textContent.includes('Mobility:'));
  }
});
test('missing local files produce readable unavailable state', async () => {
  const {host,panel} = harness(async()=>({ok:false}));
  await panel.show(job(transition)); assert.ok(host.textContent.includes('unavailable'));
});
test('history never fetches a different package, remote host or traversed path', async () => {
  for (const url of ['https://example.org/data.json','/files/rig-jobs/other/index.json','../other/index.json','%2e%2e/index.json','source/../../index.json']) {
    let called=false;
    const {host,panel} = harness(()=>{called=true;throw Error('Must not fetch');});
    const input=job(transition);input.result.generation_sources.manifest=url;
    await panel.show(input);assert.equal(called,false);assert.ok(host.textContent.includes('unavailable'));
  }
});
test('old packages disclose partial provenance and keep primary-source links', async () => {
  const {host,panel}=harness(()=>{throw Error('No automatic legacy fetch');});
  await panel.show(job('20260928-015236-7ba359be'));
  assert.ok(host.textContent.includes('Other contributors may not be listed'));assert.equal(host.all('a').length,2);
});
test('unrecorded entries and empty inventories remain explicit', async () => {
  for (const entries of [[],[{status:'unavailable',locations:[]}]]) {
    const bytes=Buffer.from(JSON.stringify({schema:'strep-generation-sources-v1',entries}));
    const {host,panel}=harness(async()=>({ok:true,arrayBuffer:async()=>bytes}));
    const input=job(transition);input.result.generation_sources.manifest_sha256=createHash('sha256').update(bytes).digest('hex');
    await panel.show(input);assert.ok(host.textContent.includes(entries.length?'not retained for this source':'No model-generation records'));
  }
});
