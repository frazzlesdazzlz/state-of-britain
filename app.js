function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function whatChanged(d){
 const changes=(d.recent_changes||[]).slice(0,6);
 if(!changes.length) return '<section id="what-changed"><h2>What Changed?</h2><p class="muted">No newly changed official observations since the last recorded update.</p></section>';
 return '<section id="what-changed"><h2>What Changed?</h2><div class="changes">'+changes.map(c=>{
  const x=(()=>{for(const g of d.groups||[])for(const i of g.items||[])if(i.id===c.id)return i;return null})();
  const label=x?.label||c.id;
  return '<div class="change"><strong>'+esc(label)+'</strong><span>'+esc(c.from??"—")+' → '+esc(c.to??"—")+'</span><small>'+esc(c.at||"")+'</small></div>'
 }).join("")+'</div></section>'
}
function card(x){let src=x.source_url?'<a href="'+x.source_url+'" target="_blank" rel="noopener">'+esc(x.source)+'</a>':esc(x.source);return '<article class="card"><div class="label">'+esc(x.label)+'</div><div class="value">'+esc(x.display)+'</div><div class="meta">'+esc(x.period)+' · '+src+'</div><div class="compare">'+(x.direction?esc(x.direction)+' ':'')+esc(x.comparison||'')+'</div></article>'}
fetch("./data.json?"+Date.now()).then(r=>r.json()).then(d=>{document.querySelector("#checked").textContent="Latest available official observations · "+d.last_checked;document.querySelector("#changed").textContent=d.changed_count+" indicators changed at the latest check";let h='<nav class="nav">'+d.navigation.map(n=>'<a href="#'+n.toLowerCase().replace(/[^a-z0-9]+/g,"-")+'">'+esc(n)+'</a>').join("")+'</nav>';
if(d.summary){h+='<section id="britain-today"><h2 class="section">'+esc(d.summary.title)+'</h2><div class="grid summarygrid">'+d.summary.ids.map(id=>{for(const g of d.groups){for(const x of(g.items||[])){if(x.id===id)return card(x)}}return ''}).join("")+'</div><div class="direction"><b>Direction:</b> '+esc(d.summary.direction)+'</div></section>'}
for(const g of d.groups){let gid=g.name.toLowerCase().replace(/[^a-z0-9]+/g,"-");h+='<section id="'+gid+'"><h2 class="section">'+esc(g.name)+'</h2>';if(g.status)h+='<div class="note">'+esc(g.status)+'</div>';if(g.items&&g.items.length)h+='<div class="grid">'+g.items.map(card).join("")+'</div>';if(g.name==="Money in → money out")h+='<div class="note">'+esc(d.notes.receipts)+'</div>';if(g.name==="UK energy balance")h+='<div class="note">'+esc(d.notes.energy)+'</div>';if(g.name==="Daily markets")h+='<div class="note">'+esc(d.notes.markets)+'</div>';h+='</section>'}
{
 const hs=d.history_series||{};
 const chart=(key,label)=>{
  const z=hs[key], pts=(z?.points||[]);
  if(!pts.length)return '<div class="histcard"><b>'+esc(label)+'</b><small>Official history pending</small></div>';
  const vals=pts.map(p=>Number(p.value)).filter(Number.isFinite), lo=Math.min(...vals), hi=Math.max(...vals), w=300,hg=92,pad=8,den=(hi-lo)||1;
  const path=vals.map((v,i)=>(i?'L':'M')+(pad+i*(w-2*pad)/Math.max(1,vals.length-1)).toFixed(1)+' '+(hg-pad-(v-lo)*(hg-2*pad)/den).toFixed(1)).join(' ');
  const last=pts[pts.length-1];
  return '<div class="histcard"><div class="histhead"><b>'+esc(label)+'</b><span>'+esc(last.value)+(z.unit||'')+'</span></div><svg viewBox="0 0 300 92" role="img" aria-label="'+esc(label)+' official history"><path d="'+path+'" fill="none" stroke="currentColor" stroke-width="2"/></svg><small>'+esc(pts[0].period)+' → '+esc(last.period)+' · '+esc(z.source||'official source')+'</small></div>';
 };
 h+='<section id="direction-history"><h2 class="section">Direction & history</h2><div class="historycharts">'+chart("debt_gdp","Debt / GDP")+chart("debt_interest","Debt interest")+chart("real_pay","Real pay")+chart("house_prices_pay","House prices / pay")+chart("gdp_per_person","GDP per person")+'</div><div class="note">Charts show stored official observations; missing series are labelled rather than estimated.</div></section>';
}document.querySelector("#app").innerHTML=h}).catch(()=>document.querySelector("#checked").textContent="Dashboard data unavailable");if("serviceWorker"in navigator)navigator.serviceWorker.register("./sw.js");