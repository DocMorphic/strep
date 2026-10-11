import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JOINT_CHOICES,validateJointSelection} from '../scripts/selected-joint-guides.mjs';
test('authoring choices agree with the Python request boundary',()=>{
 const source=readFileSync(new URL('../scripts/generation_constraints.py',import.meta.url),'utf8');
 const names=[...source.match(/SELECTABLE_JOINTS = \(([\s\S]*?)\)/)[1].matchAll(/'([^']+)'/g)].map(m=>m[1]);
 assert.deepEqual(JOINT_CHOICES.map(([name])=>name),names);assert.equal(new Set(names).size,30);
});
test('selected knees head and pelvis remain ordered, independent draft copies',()=>{
 const input=['LeftShin','RightShin','Head','Hips'];const result=validateJointSelection(input);
 assert.deepEqual(result,input);result.push('Chest');assert.equal(input.length,4);
 assert.ok(Object.isFrozen(JOINT_CHOICES)&&JOINT_CHOICES.every(Object.isFrozen));
});
test('empty duplicate unknown or non-array selections cannot enter a request',()=>{
 for(const input of [[],null,'Head',['head'],['Head','Head'],[true],[{}],['LeftHandIndex1'],Array(31).fill('Head')])
  assert.throws(()=>validateJointSelection(input));
});
