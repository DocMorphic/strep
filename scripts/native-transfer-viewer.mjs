import {createNativeReferencePlayer} from '/native-reference-player.mjs';
const el=n=>document.getElementById(n);let review,time=0,epoch=0;
const player=createNativeReferencePlayer({canvas:el('preview'),onTime:t=>{time=t;el('time').value=t;el('clock').textContent=`${t.toPrecision(9)} s`;}});
async function load(){player.pause();const token=++epoch,chosen=review?.previews.find(v=>v.id===el('version').value);for(const n of ['play','time','fit'])el(n).disabled=true;
 try{if(!chosen)throw Error('Choose a bound transfer version');const old=time;await player.load(chosen);if(token!==epoch)return;player.seek(old);el('time').max=chosen.preview_end_s;for(const n of ['play','time','fit'])el(n).disabled=false;el('status').textContent=chosen.label+'. Contacts and animation quality remain unverified.';}catch(e){if(token===epoch)el('status').textContent='Preview unavailable: '+e.message;}
}
el('version').onchange=load;el('time').oninput=()=>{player.pause();player.seek(Number(el('time').value));};el('fit').onclick=()=>player.fit();el('play').onclick=()=>player.toggle();
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===parent&&e.data==='strep-native-pause')player.pause();});
try{const q=new URLSearchParams(location.search),id=q.get('id'),digest=q.get('result');if(!/^[A-Za-z0-9_-]{1,100}$/.test(id||'')||!/^[a-f0-9]{64}$/.test(digest||''))throw Error('Choose a saved transfer result');
 const r=await fetch('/api/native-transfer-review?id='+encodeURIComponent(id),{cache:'no-store'});if(!r.ok)throw Error('Bound transfer result unavailable');review=await r.json();
 if(review.status!=='complete'||review.id!==id||review.result_sha256!==digest||review.quality_approved!==false||review.release_approved!==false||review.previews?.length!==2||review.previews[0].id!=='source'||review.previews[1].id!=='candidate')throw Error('Transfer result changed; review it again in Studio');
 el('version').replaceChildren(...review.previews.map(v=>new Option(v.label,v.id)));el('version').value='candidate';el('version').disabled=false;await load();
}catch(e){el('status').textContent=e.message;}
