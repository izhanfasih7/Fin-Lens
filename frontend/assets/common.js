/* Use textContent for all report-derived content; never interpolate it into HTML. */
window.FinLens = {
  number(value, digits=1) { return typeof value==='number' && Number.isFinite(value) ? new Intl.NumberFormat('en-IN',{maximumFractionDigits:digits}).format(value) : '—'; },
  date(value) { if(!value)return 'Date unavailable'; const d=new Date(value); return Number.isNaN(d.getTime())?'Date unavailable':new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(d); },
  async json(url,options={}) { const response=await fetch(url,options); let data; try{data=await response.json()}catch{throw new Error('The server returned an unreadable response. Please try again.')} if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'The request failed. Please try again.'); return data; },
  element(tag,text,className) { const node=document.createElement(tag); if(text!==undefined)node.textContent=text;if(className)node.className=className;return node; },
  valid(value) { return typeof value==='number' && Number.isFinite(value); },
  label(value) { return String(value).replaceAll('_',' ').replaceAll('.',' · '); }
};
