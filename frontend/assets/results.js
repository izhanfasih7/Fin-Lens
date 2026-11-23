(()=>{
 const $=id=>document.getElementById(id),F=FinLens;let report;
 const names={revenue:'Revenue',ebitda:'EBITDA',pat:'Profit after tax',pbt:'Profit before tax',tax:'Tax',finance_cost:'Finance cost',depreciation:'Depreciation'};
 const metric=(key,period)=>report.metrics?.[key]?.[period];
 const pct=value=>F.valid(value)?F.number(value)+'%':'—';
 const multiple=value=>F.valid(value)?F.number(value)+'×':'—';
 function source(key,period){return [...new Set((report.sources?.[key+'.'+period]||[]).map(s=>s.page))].join(', ')}
 function header(id,label='Metric',sourceColumn=false){const row=F.element('tr');[label,report.periods?.previous||'Previous',report.periods?.current||'Current',...(sourceColumn?['Pages prev / current']:[])].forEach(t=>row.append(F.element('th',t)));$(id).replaceChildren(row)}
 function row(id,label,previous,current,format=F.number,sourceText){const tr=F.element('tr');tr.append(F.element('td',label),F.element('td',format(previous)),F.element('td',format(current),'current'));if(sourceText!==undefined)tr.append(F.element('td',sourceText));$(id).append(tr)}
 function chart(id,labels,previous,current,horizontal=false){
  const wrap=$(id+'Wrap');
  if(![...previous,...current].some(F.valid)){wrap.replaceChildren(F.element('p','No comparable figures were found.','status'));return}
  if(!window.Chart){wrap.replaceChildren(F.element('p','Chart unavailable. Open the data table below to view the figures.','status'));return}
  new Chart($(id),{type:'bar',data:{labels,datasets:[{label:report.periods?.previous||'Previous',data:previous,backgroundColor:'#433655',borderRadius:4},{label:report.periods?.current||'Current',data:current,backgroundColor:'#a78bfa',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,indexAxis:horizontal?'y':'x',animation:matchMedia('(prefers-reduced-motion: reduce)').matches?false:{duration:450},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': '+F.number(horizontal?ctx.parsed.x:ctx.parsed.y)+' crore'}}},scales:{x:{beginAtZero:true,grid:{color:horizontal?'rgba(255,255,255,.05)':'transparent'},ticks:{color:'#9890a5',font:{size:10}}},y:{beginAtZero:true,grid:{color:horizontal?'transparent':'rgba(255,255,255,.05)'},ticks:{color:'#9890a5',font:{size:10}}}}}});
 }
 function render(){
  $('reportTitle').textContent=report.filename||'Financial report';$('demoNotice').hidden=!report.is_demo;if(report.is_demo)$('demoNav').setAttribute('aria-current','page');
  if(report.is_fallback){document.querySelector('h1').textContent='Illustrative demonstration.';}
  $('reportMeta').textContent=report.is_demo?'Demo · Not saved to history':`${F.date(report.created_at)} · ${F.number(report.page_count,0)} pages · INR crore`;
  if(report.is_fallback)$('reportMeta').textContent='Sample preview · Saved to history';
  const adjustment=(report.warnings||[]).find(note=>/exclude.*profit|exclude.*gain/i.test(note));
  if(adjustment){$('comparisonNote').textContent='Comparison basis · '+adjustment;$('comparisonNote').hidden=false;}
  ['previous','current'].forEach(p=>$('periodLegend').append(F.element('span',report.periods?.[p]||p)));
  for(const key of ['revenue','ebitda','pat']){
   const card=F.element('section',undefined,'panel kpi');card.append(F.element('div',names[key],'kpi-label'));
   const value=F.element('div',F.number(metric(key,'current')),'kpi-value');value.append(F.element('small','₹ crore'));card.append(value);
   const growth=report.ratios?.yoy_growth_pct?.[key];card.append(F.element('div',F.valid(growth)?`${growth>0?'+':''}${F.number(growth)}% year on year`:'YoY growth unavailable','kpi-note '+(F.valid(growth)?growth>=0?'up':'down':'')));$('kpis').append(card);
  }
  const margin=report.ratios?.current?.ebitda_margin_pct,card=F.element('section',undefined,'panel kpi');card.append(F.element('div','EBITDA margin','kpi-label'),F.element('div',pct(margin),'kpi-value'),F.element('div',`${report.periods?.current||'Current period'} · EBITDA / revenue`,'kpi-note'));$('kpis').append(card);
  header('financialHead','INR crore',true);for(const key of Object.keys(names))row('financialTable',names[key],metric(key,'previous'),metric(key,'current'),F.number,`${source(key,'previous')||'—'} / ${source(key,'current')||'—'}`);
  const segments=Object.keys(report.segment_ebitda||{});header('segmentHead','INR crore',true);for(const key of segments)row('segmentTable',key,report.segment_ebitda[key].previous,report.segment_ebitda[key].current,F.number,`${source('segments.'+key,'previous')||'—'} / ${source('segments.'+key,'current')||'—'}`);
  header('ratioHead');for(const [key,label,format] of [['ebitda_margin_pct','EBITDA margin',pct],['pbt_margin_pct','PBT margin',pct],['pat_margin_pct','PAT margin',pct],['effective_tax_rate_pct','Effective tax rate',pct],['interest_coverage_x','Interest coverage',multiple]])row('ratioTable',label,report.ratios?.previous?.[key],report.ratios?.current?.[key],format);
  row('ratioTable','Net debt / LTM EBITDA'+(report.balance_as_of?` (${report.balance_as_of})`:''),null,report.ratios?.net_debt_to_ebitda_x,multiple);
  if(F.valid(report.annualized_net_debt_to_ebitda))row('ratioTable','Net debt / EBITDA (reported, annualised)',null,report.annualized_net_debt_to_ebitda,multiple);
  const health=report.health||{};$('healthScore').textContent=F.number(health.score,0);$('healthRating').textContent=health.rating||'Insufficient data';
  $('healthMethod').textContent=({random_forest:'Ratio classifier',rule_based:'Ratio rules',insufficient_data:'Limited data',illustrative:'Demo score'})[health.method]||'Not available';
  $('healthCoverage').textContent=F.valid(health.available_features)?`${health.available_features} of 5 model ratios available`:'Model coverage unavailable';
  $('healthReason').textContent=health.reason||health.score_meaning||'Health analysis was not included in this saved result.';
  const sentiment=report.sentiment||{},usable=sentiment.status==='ok'&&F.valid(sentiment.gauge_score);$('sentimentModel').textContent=report.is_demo?'Illustrative':'FinBERT';
  $('sentimentStatus').textContent=usable?`${F.number(sentiment.gauge_score)}/100 · ${F.number(sentiment.sentences_analyzed,0)} sentences analyzed. ${sentiment.sentences_skipped||0} skipped; ${sentiment.sentences_truncated||0} truncated.`:sentiment.reason||'Sentiment is unavailable for this analysis.';
  if(usable){$('sentimentVisual').hidden=false;$('gaugeMarker').style.left=Math.max(0,Math.min(100,sentiment.gauge_score))+'%';$('sentimentGauge').setAttribute('aria-valuenow',sentiment.gauge_score);
   for(const key of ['positive','neutral','negative']){const cell=F.element('div');cell.append(F.element('strong',pct(sentiment.percentages?.[key])),F.element('span',key[0].toUpperCase()+key.slice(1)));$('sentimentScores').append(cell)}}
  for(const [id,key] of [['positiveQuotes','top_positive'],['negativeQuotes','top_negative']]){const quotes=sentiment[key]||[];if(!quotes.length)$(id).append(F.element('p','No sentences available for this class.','health-explainer'));for(const quote of quotes){const p=F.element('p',quote.sentence,'quote');p.append(F.element('small',`Confidence: ${pct(F.valid(quote.confidence)?quote.confidence*100:null)}`));$(id).append(p)}}
  const sentences=[];for(const key of ['revenue','ebitda','pat']){const current=metric(key,'current'),growth=report.ratios?.yoy_growth_pct?.[key];if(F.valid(current))sentences.push(`${names[key]} was ₹${F.number(current)} crore${F.valid(growth)?`, ${growth>0?'up':growth<0?'down':'unchanged'}${growth===0?'':` ${F.number(Math.abs(growth))}%`} year on year`:''}.`)}
  if(F.valid(margin))sentences.push(`EBITDA margin was ${pct(margin)}.`);$('summary').textContent=sentences.join(' ')||'There are not enough extracted figures to summarize this report. Review the missing metrics below and confirm that the PDF contains selectable text and supported tables.';
  if(report.is_demo)$('summaryFoot').textContent='Illustrative figures only. No actual report was used to create this demo.';
  const missing=report.missing||[];$('missingCount').textContent=`${missing.length} missing fields`;missing.forEach(key=>$('missingList').append(F.element('span',F.label(key),'missing-item')));
  if(!missing.length)$('missingList').append(F.element('span','No missing fields reported.','health-explainer'));(report.warnings||[]).forEach(w=>$('warnings').append(F.element('li',w)));
  $('resultStatus').hidden=true;$('dashboard').hidden=false;$('download').disabled=false;
  chart('financialChart',['Revenue','EBITDA','PAT'],['revenue','ebitda','pat'].map(k=>metric(k,'previous')),['revenue','ebitda','pat'].map(k=>metric(k,'current')));
  chart('segmentChart',segments,segments.map(k=>report.segment_ebitda[k].previous),segments.map(k=>report.segment_ebitda[k].current),true);
  const coverage=report.coverage;
  if(coverage&&coverage.status!=='figures_available'){
   $('coverageNotice').hidden=false;
   $('coverageTitle').textContent=coverage.status==='narrative_only'?'Results commentary available':'Financial table not extracted';
   $('coverageReason').textContent=coverage.reason;
   for(const item of coverage.reported_highlights||[]){const p=F.element('p',item.text,'quote');p.append(F.element('small','Source pages: '+item.pages.join(', ')));$('reportedHighlights').append(p)}
   $('kpis').hidden=true;
   $('financialChartWrap').closest('.grid-two').hidden=true;
   $('ratioTable').closest('.grid-two').hidden=true;
   $('summary').textContent=coverage.reason;
   $('summaryFoot').textContent='Reported narrative is shown above with source pages. No amounts are inferred from percentage changes.';
  }else if(!segments.length){$('segmentChartWrap').closest('section').hidden=true;}
 }
 $('download').addEventListener('click',()=>{if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=F.element('a');a.href=url;a.download='finlens-'+String(report.id).replace(/[^a-z0-9-]/gi,'')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 async function load(){try{const id=decodeURIComponent(location.pathname.split('/').filter(Boolean).at(-1));report=await F.json(id==='demo'?'/api/demo':'/api/analysis/'+encodeURIComponent(id));render()}catch(error){$('resultStatus').replaceChildren(F.element('p',error.message));const back=F.element('a','Back to history','btn');back.href='/history';$('resultStatus').append(back)}}load();
})();
