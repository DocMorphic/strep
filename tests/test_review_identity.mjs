// Synthetic role/export fixtures only; no human evidence is written.
import assert from 'node:assert/strict';
import {reviewIdentity,reviewExport} from '../scripts/review-identity.js';
const packet={packet_id:'synthetic'};
const independent=reviewIdentity(packet);
assert.equal(independent.role,'independent');
assert.equal(reviewExport(independent,packet,'a'.repeat(64),' fixture ',[]).independent_human,true);
const developerPacket={...packet,review_type:'developer'};
const developer=reviewIdentity(developerPacket);
const data=reviewExport(developer,developerPacket,'b'.repeat(64),'fixture',[]);
assert.equal(data.schema,'strep-developer-packet-review-v1');
assert.equal(data.human_review,true);
assert.equal(data.independent_human,false);
assert.equal(data.quality_approved,false);
assert.equal(data.release_approved,false);
assert.notEqual(developer.prefix,independent.prefix);
assert.throws(()=>reviewIdentity({...packet,review_type:'unknown'}));
assert.throws(()=>reviewIdentity({...packet,review_type:null}));
assert.throws(()=>reviewExport(independent,developerPacket,'x','fixture',[]));
assert.throws(()=>reviewExport(developer,developerPacket,'x',' ',[]));
assert.throws(()=>reviewExport(developer,developerPacket,'x','fixture',{}));
// A stale or modified identity cannot inject independent approval into export.
const forged={...developer,schema:'strep-human-review-v1',fields:{independent_human:true,quality_approved:true}};
assert.deepEqual(reviewExport(forged,developerPacket,'b'.repeat(64),'fixture',[]),data);
console.log('Review identity and export separation passed');
