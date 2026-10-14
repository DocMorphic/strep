import {checkedReview} from './key-continuation-editor.mjs';
export function createKeyContinuationComparison({document,api,createPlayer,id,completion}){
 const el=n=>document.getElementById(n);let review,player,time=0,epoch=0,loaded=false;
 const controls=value=>{for(const n of ['version','play','time','fit'])el(n).disabled=value;};
 const pause=()=>{player?.pause();el('play').textContent='Play';};
 async function load(){pause();controls(true);const token=++epoch,previous=time,version=review?.previews.find(v=>v.id===el('version').value);
  try{if(!version)throw Error('Choose a recorded comparison version');
   if(!player)player=await createPlayer({canvas:el('preview'),onTime:t=>{time=t;el('time').value=t;el('clock').textContent=`${t.toFixed(3)} s`;if(t>=Number(el('time').max))el('play').textContent='Play';}});
   if(token!==epoch)return;
   await player.load(version,{fitView:!loaded});if(token!==epoch)return;
   player.seek(loaded?previous:version.preview_start_s);loaded=true;controls(false);
   el('status').textContent=version.label+'. Same native clock; camera retained when switching. No acceptance or scene selection changed.';
  }catch(e){if(token===epoch){el('status').textContent='Preview unavailable: '+e.message;el('version').disabled=false;}}
 }
 el('version').onchange=load;el('time').oninput=()=>{pause();player?.seek(Number(el('time').value));};
 el('fit').onclick=()=>player?.fit();el('play').onclick=()=>{const play=el('play').textContent!=='Pause';player?.toggle();el('play').textContent=play?'Pause':'Play';};
 async function init(){controls(true);
  try{if(!/^[A-Za-z0-9_-]{1,100}$/.test(id||'')||!/^[a-f0-9]{64}$/.test(completion||''))throw Error('Choose a completed continuation');
   review=checkedReview(await api(`/api/key-continuation-preview?id=${encodeURIComponent(id)}&completion=${completion}`),id);
   if(review.status!=='complete'||review.completion_sha256!==completion||review.previews?.length!==2)throw Error('Comparison binding changed');
   for(const [i,v] of review.previews.entries()){
    if(v.id!==['source','candidate'][i]||v.kind!=='native_key_continuation'||v.preview_url!==review.downloads[i].url||v.preview_sha256!==review.downloads[i].sha256
      ||!Number.isInteger(v.animation_index)||!Number.isInteger(v.animation_count)||v.animation_index<0||v.animation_index>=v.animation_count
      ||![v.preview_start_s,v.preview_end_s].every(Number.isFinite)||v.preview_start_s<0||v.preview_end_s<=v.preview_start_s)throw Error('Recorded comparison selection changed');
   }
   if(['preview_start_s','preview_end_s'].some(k=>review.previews[0][k]!==review.previews[1][k]))throw Error('Comparison clocks differ');
   el('decision').textContent=`Motion-rate failures: ${review.rate_failures}; floor failures: ${review.floor_failures}. ${review.sampled_conditions_pass?'Sampled checks pass; animation quality remains unapproved.':'Proposal still fails acceptance.'} Original remains selected.`;
   el('version').replaceChildren(...review.previews.map(v=>{const o=document.createElement('option');o.value=v.id;o.textContent=v.label;return o;}));el('version').value='source';
   el('time').min=review.previews[0].preview_start_s;el('time').max=review.previews[0].preview_end_s;await load();
  }catch(e){controls(true);el('status').textContent='Preview unavailable: '+e.message;}
 }
 return {init,pause};
}
