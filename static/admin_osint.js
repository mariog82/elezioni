/*
Modulo investigativo / OSINT politico
- visualizza alert derivati da concentrazioni territoriali, voto disgiunto e reti candidato-sezione;
- non effettua scraping aggressivo: lavora su dati leciti e fonti aperte;
- può essere esteso con connettori a rassegna stampa, albo pretorio, social API e open data.
*/
async function api(url){const r=await fetch(url,{credentials:'include'});const d=await r.json();if(!r.ok||d.ok===false)throw new Error(d.error||'Errore server');return d}function esc(s){return String(s??'').replace(/[&<>\"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[m]))}
async function loadOsint(){const d=await api('/api/osint'); disclaimer.textContent=d.disclaimer; sourceBox.innerHTML=d.sources.map(s=>`<div class="card"><h3>${esc(s.name)}</h3><p>${esc(s.use)}</p></div>`).join(''); alertBox.innerHTML=`<table><tr><th>Tipo</th><th>Soggetto</th><th>Area</th><th>Rischio</th><th>Evidenza</th></tr>${d.alerts.map(a=>`<tr><td>${esc(a.type)}</td><td><b>${esc(a.subject)}</b></td><td>${esc(a.area)}</td><td><span class="badge">${esc(a.risk)}</span></td><td>${esc(a.evidence)}</td></tr>`).join('')}</table>`;}
loadOsint().catch(e=>alert(e.message));
