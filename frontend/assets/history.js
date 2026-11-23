(()=>{const F=FinLens,list=document.getElementById('historyList'),status=document.getElementById('historyStatus'),more=document.getElementById('loadMore');let offset=0,loading=false;
 async function load(){if(loading)return;loading=true;more.disabled=true;status.hidden=true;
  try{const rows=await F.json(`/api/history?limit=21&offset=${offset}`);if(!Array.isArray(rows))throw new Error('History returned an unreadable response.');
   for(const record of rows.slice(0,20)){const link=F.element('a',undefined,'panel history-row');link.href='/results/'+encodeURIComponent(record.id);const text=F.element('div');text.append(F.element('h2',record.filename),F.element('p',F.date(record.created_at)));link.append(text,F.element('span','↗','arrow'));list.append(link)}offset+=Math.min(rows.length,20);more.hidden=rows.length<=20;
   if(!offset){status.hidden=false;status.replaceChildren(F.element('h2','Your first report starts here.'),F.element('p','Upload a financial report to save your first analysis.'));const link=F.element('a','Analyze a report →','btn primary');link.href='/upload';status.append(link)}
  }catch(error){status.hidden=false;status.replaceChildren(F.element('p',error.message));const retry=F.element('button','Try again','btn');retry.addEventListener('click',load);status.append(retry)}finally{loading=false;more.disabled=false}}
 more.addEventListener('click',load);load();})();
