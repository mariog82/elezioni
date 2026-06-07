/*
Modulo Social & Viral
- genera card condivisibili, dashboard pubbliche e Political Score;
- usa solo dati aggregati e non dati personali dei rappresentanti;
- pensato per crescita virale, comunicazione del candidato/lista e monetizzazione premium.
*/
let SOCIAL=null;
async function api(url){const r=await fetch(url,{credentials:'include'});const d=await r.json();if(!r.ok||d.ok===false)throw new Error(d.error||'Errore server');return d}
function esc(s){return String(s??'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}
function kpi(label,value){return `<div class="card kpi"><b>${esc(value)}</b><span>${esc(label)}</span></div>`}
async function loadSocial(){try{SOCIAL=await api('/api/intelligence'); publicUrl.value=location.origin+'/public-dashboard'; renderSummary(); renderCards();}catch(e){alert(e.message);location.href='/'}}
function renderSummary(){const s=SOCIAL.summary; publicSummary.innerHTML=[kpi('Sezioni caricate',s.sections_loaded),kpi('Sezioni chiuse',s.sections_closed),kpi('Votanti rilevati',s.observed_voters),kpi('Voto disgiunto censito',s.split_vote_count)].join('')}
function renderCards(){const q=(socialSearch.value||'').toLowerCase(); const lim=parseInt(cardLimit.value||24,10); const rows=SOCIAL.social_cards.filter(x=>!q||JSON.stringify(x).toLowerCase().includes(q)).slice(0,lim); scoreCards.innerHTML=rows.map(x=>`<article class="scoreCard"><div class="rank">#${x.rank}</div><h3>${esc(x.candidate)}</h3><p>${esc(x.list)}</p><div class="score">${x.political_score}<small>/100</small></div><div class="pillList">${x.badges.map(b=>`<span class="pill">${esc(b)}</span>`).join('')}</div><p class="small">Preferenze: <b>${x.preferences}</b> · Sezioni: <b>${x.sections_with_votes}</b> · Incidenza lista: <b>${x.preference_on_list_pct}%</b></p><button onclick="copyCard('${encodeURIComponent(x.share_text)}')">Copia card</button></article>`).join('')}
function copyPublicUrl(){publicUrl.select(); document.execCommand('copy')}
function copyCard(t){navigator.clipboard?.writeText(decodeURIComponent(t)); alert('Testo card copiato')}
function generateSocialPost(){const top=(SOCIAL.social_cards||[]).slice(0,5); socialText.value=`POLITICAL SCORE - aggiornamento live\n\n${top.map(x=>`#${x.rank} ${x.candidate} (${x.list}) - Score ${x.political_score}/100 - ${x.badges.join(', ')}`).join('\n')}\n\nDashboard pubblica: ${publicUrl.value}`}
function copySocialPost(){socialText.select();document.execCommand('copy')}
socialSearch.oninput=renderCards; cardLimit.oninput=renderCards; loadSocial();
