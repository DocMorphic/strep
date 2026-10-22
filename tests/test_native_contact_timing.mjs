import assert from 'node:assert/strict';
import {worldContactTiming} from '../scripts/native-scene-editor.mjs';
const contact=(id,start,end,x,extra={})=>({id,actor:'A',vertices:[[7,0,4]],reduction:'individual',
 target:{space:'world',points_m:[[x,0,0]]},mode:start===end?'touch':'hold',interval_s:[start,end],limits:{position_m:.02},...extra});
const scene=contacts=>({duration_s:10,actors:{A:{},B:{}},contacts});
const inspect=contacts=>worldContactTiming(scene(contacts));
const near=(a,b)=>assert(Math.abs(a-b)<1e-12,`${a} != ${b}`);
{
 const input=scene([contact('later',2,3,1,{limits:{position_m:.1}}),contact('earlier',0,1,0)]),before=structuredClone(input),r=worldContactTiming(input),p=r.pairs[0];
 assert.deepEqual(input,before);assert.equal(p.from,'earlier');assert.equal(p.to,'later');near(p.minimum_travel_m,.88);near(p.minimum_average_speed_m_s,.88);
 assert.equal(p.gap_s,1);assert.equal(r.point_comparisons,1);assert.equal(r.actual_motion_assessed,false);assert.equal(r.quality_approved,false);
}
{
 const r=inspect([contact('a',0,1,0,{limits:{position_m:0}}),contact('b',1.25,2,1,{limits:{position_m:0}})]);
 near(r.pairs[0].minimum_average_speed_m_s,4);
}
for(const [start,end] of [[.5,.8],[1,2],[.25,1.25]]){
 const r=inspect([contact('a',0,1,0),contact('b',start,end,1)]);
 assert.equal(r.pairs[0].simultaneous_target_conflict,true);assert.equal(r.pairs[0].minimum_average_speed_m_s,null);assert(!JSON.stringify(r).includes('Infinity'));
}
{
 const r=inspect([contact('long',0,8,0),contact('middle',1,2,0),contact('late',5,6,1)]);
 assert.equal(r.pairs.length,3);assert(r.pairs.find(p=>p.from==='long'&&p.to==='late').simultaneous_target_conflict);
}
{
 const r=inspect([contact('a',0,1,0),contact('b',1,2,.04)]);assert.equal(r.pairs[0].minimum_average_speed_m_s,0);assert(!r.pairs[0].simultaneous_target_conflict);
}
for(const extra of [{actor:'B'},{vertices:[[8,0,4]]},{vertices:[[7,1,4]]},{vertices:[[7,0,5]]}]){
 assert.equal(inspect([contact('a',0,1,0),contact('b',2,3,1,extra)]).pairs.length,0);
}
{
 const refs=[[7,0,4],[7,0,5]],r=inspect([contact('a',0,1,0,{reduction:'centroid',vertices:refs}),
  contact('b',2,3,1,{reduction:'centroid',vertices:[...refs].reverse()}),contact('constituent',4,5,2)]);
 assert.equal(r.pairs.length,1);assert.equal(r.pairs[0].matched_points,1);near(r.pairs[0].minimum_average_speed_m_s,.96);
 assert.equal(inspect([contact('a',0,1,0,{reduction:'centroid'}),contact('b',2,3,1)]).pairs.length,1);
}
{
 const a=contact('a',0,1,0,{vertices:[[7,0,4],[7,0,5]],target:{space:'world',points_m:[[0,0,0],[0,1,0]]}});
 const b=contact('b',2,3,0,{vertices:[[7,0,5],[7,0,4]],target:{space:'world',points_m:[[2,1,0],[1,0,0]]}});
 const r=inspect([a,b]);assert.equal(r.pairs.length,1);assert.equal(r.point_comparisons,2);assert.equal(r.pairs[0].matched_points,2);near(r.pairs[0].minimum_average_speed_m_s,1.96);assert.deepEqual(r.pairs[0].vertices,[[7,0,5]]);
 b.interval_s=[1,2];const conflict=inspect([a,b]).pairs[0];assert(conflict.simultaneous_target_conflict);near(conflict.minimum_travel_m,1.96);
}
{
 const r=inspect([contact('a',0,1,0),contact('object',2,3,0,{target:{space:'object',object:'box',points_m:[[1,0,0]]}}),
  contact('partner',4,5,0,{target:{space:'actor',actor:'B',vertices:[[7,0,4]],reduction:'individual'}})]);
 assert.equal(r.pairs.length,0);assert.deepEqual(r.unassessed,[{id:'object',space:'object'},{id:'partner',space:'actor'}]);
}
for(const extra of [{limits:{position_m:true}},{limits:{position_m:-1}},{limits:{position_m:NaN}},
 {vertices:[[7,0,true]]},{vertices:[[7,0,4],[7,0,4]]},{interval_s:[2,1]},{interval_s:[0,11]},
 {interval_s:[0,Infinity]},{mode:'touch'},{actor:'unknown'},{reduction:'median'},
 {target:{space:'world',points_m:[[Infinity,0,0]]}},{target:{space:'world',points_m:[]}},
 {target:{space:'unknown'}}])assert.throws(()=>inspect([contact('bad',0,1,0,extra)]));
assert.throws(()=>inspect([contact('same',0,1,0),contact('same',2,3,0)]));
assert.throws(()=>inspect([contact('a',0,1,-1e308),contact('b',2,3,1e308)]));
assert.equal(inspect([]).pairs.length,0);
console.log('World-target timing: identity, centroid equivalence, unequal/zero tolerances, overlaps, strongest-point aggregation, coverage and malformed inputs passed.');
