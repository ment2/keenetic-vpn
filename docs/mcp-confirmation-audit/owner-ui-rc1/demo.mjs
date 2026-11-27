import {ownerReview} from './owner-review.mjs';
const $=id=>document.getElementById(id);
let pending,review,approved=0,queued=0,epoch=0;
function counters(){$('counter').textContent=`Запросы согласования: ${approved} · тестовые постановки: ${queued}`;}
function draw(){const s=review.status();$('status').textContent=s.toUpperCase();$('approve').disabled=s!=='review'||!$('agree').checked;$('allow').disabled=$('deny').disabled=s!=='approved';$('cancel').disabled=!['review','approving','approved'].includes(s);counters();}
function reset(){if(review)review.cancel();epoch++;if($('device').value==='ha'&&$('route').value==='legacy')$('route').value='named';$('route').querySelector('[value="legacy"]').disabled=$('device').value==='ha';pending={target:$('device').value,route:$('route').value,task:$('operation').value==='write_file'?{op:'write_file',path:'/synthetic-unit/sample.txt',content:'synthetic only'}:{op:'exec',command:'SYNTHETIC_NO_EXECUTION',timeout:20}};
 review=ownerReview(pending,{requestApproval:async()=>{approved++;return {approval_id:crypto.randomUUID(),expires_in:120};}});$('task').textContent=review.display();$('agree').checked=false;draw();}
for(const id of ['device','route','operation'])$(id).addEventListener('change',reset);
$('agree').addEventListener('change',draw);
$('approve').addEventListener('click',async e=>{if(!e.isTrusted||!$('agree').checked||review.status()!=='review')return;const r=review,n=epoch;const p=r.approve(true);draw();await p;if(epoch===n)draw();else counters();});
$('cancel').addEventListener('click',e=>{if(e.isTrusted){review.cancel();draw();}});
$('deny').addEventListener('click',e=>{if(e.isTrusted&&review.status()==='approved'){review.hostDenied(pending);draw();}});
$('allow').addEventListener('click',async e=>{if(!e.isTrusted||review.status()!=='approved')return;const r=review,n=epoch;const p=r.deliverTo(pending,async()=>{queued++;return {status:'queued'};});draw();await p;if(epoch===n)draw();else counters();});
reset();
