const active=new Set(['waiting_resources','ready','starting','processing','encoding','generation','export']);
export const activeGenerationStatus=status=>active.has(status);
export function generationJobMessage(job){
  if(job.status==='waiting_resources'||job.status==='ready')return 'Waiting for free memory. Your request is saved.';
  if(job.status==='deferred')return 'Not started: more free memory is needed. Your request is saved; retry when ready.';
  if(job.status==='failed')return 'Generation stopped. Your request and logs are preserved.';
  if(job.status==='encoding')return 'Encoding your descriptions. This can take several minutes.';
  return `Local job: ${job.status}`;
}
export function activityMessage(studies,busy){
  const waiting=studies.some(s=>['waiting_resources','ready'].includes(s.status));
  return busy?(waiting?'Waiting for free memory.':'Motion in progress.'):
    studies.some(s=>s.status==='deferred')?'Some requests were not started.':'All caught up.';
}
export function renderJobList(container,studies,busy,retry,doc=container.ownerDocument){
  container.replaceChildren();
  for(const s of studies){
    const row=doc.createElement('div');row.className='job-row';
    const title=doc.createElement('strong');
    title.textContent=s.kind==='contact_check'?'Contact timing check · '+s.id.split('/')[1]:
      s.kind==='contact_edit'?'Contact edit · '+s.id.split('/')[1]:
      s.id==='action-coverage-v1'?'Motion coverage examples':s.id.split('/').pop();
    const status=doc.createElement('span');
    status.textContent=s.kind==='generation'?generationJobMessage(s)+(s.ready?' · files available':''):
      s.kind==='contact_check'?(s.status==='needs_authoring_change'?'Contact changes needed':
        s.status==='checked'?'Timing checked · no animation created':s.status):s.status+(s.ready?' · files available':'');
    row.append(title,status);
    if(s.kind==='generation'&&s.status==='deferred'&&s.can_retry===true){
      const button=doc.createElement('button');button.type='button';button.textContent='Retry saved request';button.disabled=busy;
      button.onclick=async()=>{if(button.disabled)return;button.disabled=true;try{await retry(s.id);}finally{button.disabled=busy;}};
      row.append(button);
    }
    container.append(row);
  }
}
