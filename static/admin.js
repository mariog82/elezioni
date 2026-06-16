async function adminLogout(){
  try{await fetch('/api/logout',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:'{}'});}catch(e){}
  location.href='/';
}


let mayorPieChart=null,listPieChart=null,listBarChart=null,lastData=null;
let detailCharts=[];
let currentPrefTableList=null;
let electionListNames=[];
// Le tab dei grafici e delle tabelle non sono più limitate a poche liste predefinite.
// Vengono generate dinamicamente da tutte le liste presenti nelle anagrafiche/caricamenti CSV.
function getAllListNamesFromDashboard(d){
  return Object.keys(d?.data?.lists || {}).sort((a,b)=>a.localeCompare(b));
}

function hasEl(id){ return document.getElementById(id)!==null; }
function safeEl(id){ return document.getElementById(id); }

async function api(url, options={}){
  const res=await fetch(url,{credentials:"include",headers:{"Content-Type":"application/json"},...options});
  const data=await res.json();
  if(!res.ok||data.ok===false)throw new Error(data.error||"Errore server");
  return data;
}

function adminModuleLabel(key, title){
  const labels={
    intelligence:"Political Intelligence",
    social:"Social & Viral",
    blockchain:"Blockchain/DAO/NFT",
    osint:"OSINT politico",
    simulator:"Simulatore"
  };
  return labels[key] || title;
}

async function loadAdminModuleButtons(){
  const box=document.getElementById("adminModuleButtons");
  if(!box || box.dataset.loaded==="1") return;
  const base=[
    {label:"Grafici", path:"/admin/charts", cls:""},
    {label:"Importazione", path:"/admin/imports", cls:""},
    {label:"Gestione utenti", path:"/admin/users", cls:""},
    {label:"Esporta CSV", path:"/api/export.csv", cls:"secondary"}
  ];
  const d=await api("/api/admin/available-modules");
  const premium=(d.modules||[]).map(m=>({label:adminModuleLabel(m.key,m.title), path:m.path, cls:""}));
  box.innerHTML=[...base,...premium].map(b=>`<button class="${b.cls||""}" onclick="location.href='${b.path}'">${b.label}</button>`).join("");
  box.dataset.loaded="1";
}

async function loadAdminPaymentBox(){
  const box=document.getElementById("adminPaymentBox");
  if(!box || box.dataset.loaded==="1") return;
  const d=await api("/api/admin/payment-info");
  const profile=d.profile||{};
  const payments=d.payments||[];
  const paymentRows=payments.length ? payments.map(p=>`<tr><td><b>${p.provider}</b><br><span class="small">${p.mode||"test"}</span></td><td>${p.public_key||"—"}</td><td>${p.webhook_url||"—"}</td><td>${p.notes||"—"}</td></tr>`).join("") : `<tr><td colspan="4">Nessun metodo di pagamento abilitato. Contattare il Super Utente.</td></tr>`;
  box.innerHTML=`
    <div class="grid two">
      <div>
        <h3>Profilo cliente</h3>
        <p><b>Organizzazione:</b> ${profile.organization||"—"}<br>
        <b>Territorio:</b> ${(profile.place||"—")} ${(profile.cap||"")} ${(profile.province||"")}<br>
        <b>Motivo:</b> ${profile.usage_reason||"—"}<br>
        <b>Beneficiari:</b> ${profile.beneficiaries||"—"}</p>
      </div>
      <div>
        <h3>Come pagare</h3>
        <ol>${(d.instructions||[]).map(x=>`<li>${x}</li>`).join("")}</ol>
      </div>
    </div>
    <div class="tablewrap"><table><thead><tr><th>Metodo</th><th>Chiave/link/alias</th><th>Webhook/link operativo</th><th>Note</th></tr></thead><tbody>${paymentRows}</tbody></table></div>`;
  box.dataset.loaded="1";
}

async function loadDashboard(){
  try{
    const d=await api("/api/dashboard");
    lastData=d;

    if(hasEl("totalElectors")) prepareSettings(d);
    if(hasEl("ballotSummary")) renderBallotSummary(d);
    if(hasEl("mayorPieChart") || hasEl("listPieChart") || hasEl("listBarChart")) drawMainCharts(d);
    if(hasEl("sections")) renderSections(d);
    if(hasEl("prefTableTabs") && hasEl("prefTables")) renderPrefTableTabs(d);
    if(hasEl("electedBox")) renderElected(d);
    if(hasEl("chartTabLists") || hasEl("chartTabPrefs")) await renderDetailCharts();
    if(hasEl("users")) await loadUsers();
    if(hasEl("adminModuleButtons")) await loadAdminModuleButtons();
    if(hasEl("adminPaymentBox")) await loadAdminPaymentBox();

  }catch(e){
    alert(e.message+"\nAccedi come amministratore.");
    location.href="/";
  }
}
function prepareSettings(d){
  const s=d.election.settings;
  const totalElectors=safeEl("totalElectors");
  const totalVoters=safeEl("totalVoters");
  const councilSeats=safeEl("councilSeats");
  const mode=safeEl("mode");
  if(totalElectors) totalElectors.value=s.total_electors;
  if(totalVoters) totalVoters.value=s.total_voters;
  if(councilSeats) councilSeats.value=s.council_seats;

  const sel=safeEl("winnerMayor");
  if(sel){
    if(!sel.dataset.ready){
      d.data.mayors.forEach(m=>{
        const o=document.createElement("option");
        o.value=m; o.textContent=m; sel.appendChild(o);
      });
      sel.dataset.ready="1";
    }
    sel.value=s.winner_mayor;
  }
  if(mode) mode.value=s.mode;
}
async function saveSettings(){
  try{
    await api("/api/settings",{method:"POST",body:JSON.stringify({
      total_electors:document.getElementById("totalElectors").value,
      total_voters:document.getElementById("totalVoters").value,
      council_seats:document.getElementById("councilSeats").value,
      winner_mayor:document.getElementById("winnerMayor").value,
      mode:document.getElementById("mode").value
    })});
    alert("Parametri salvati");
    await loadDashboard();
  }catch(e){alert(e.message)}
}

function renderBallotSummary(d){
  const b=d.ballot_totals||{};
  const validLists=d.lists.reduce((a,x)=>a+(x.total||0),0);
  const calculated=validLists+(b.blank_ballots||0)+(b.null_ballots||0);
  const voters=b.voters||0;
  const settingVoters=d.election.settings.total_voters||0;
  const turnout=d.election.settings.total_electors ? (settingVoters/d.election.settings.total_electors*100).toFixed(2) : "0.00";
  document.getElementById("ballotSummary").innerHTML=`
  <p><b>Elettori:</b> ${d.election.settings.total_electors} &nbsp; <b>Votanti impostati:</b> ${settingVoters} &nbsp; <b>Affluenza:</b> ${turnout}%</p>
  <p><b>Votanti rilevati:</b> ${voters}<br>
  <b>Voti validi lista:</b> ${validLists}<br>
  <b>Bianche:</b> ${b.blank_ballots||0} &nbsp; <b>Nulle:</b> ${b.null_ballots||0} &nbsp; <b>Elettori sezioni:</b> ${b.section_electors||b.contested_ballots||0}<br>
  <b>Voti disgiunti censiti:</b> ${b.split_vote_count||0}<br>
  <b>Totale controllo senza elettori:</b> ${calculated}<br>
  <b>Quadratura:</b> ${calculated===voters ? "OK" : "NON QUADRA"}</p>`;
}

function destroyChart(ch){ if(ch) ch.destroy(); }

function colorPalette(count){
  const base=[
    "#8b1e1e","#1976d2","#388e3c","#f57c00","#7b1fa2","#c2185b",
    "#00796b","#fbc02d","#5d4037","#455a64","#d32f2f","#303f9f",
    "#689f38","#ffa000","#512da8","#0097a7","#795548","#607d8b",
    "#e64a19","#0288d1","#afb42b","#f06292","#4e342e","#00695c"
  ];
  const colors=[];
  for(let i=0;i<count;i++) colors.push(base[i % base.length]);
  return colors;
}
function totalVotersForCharts(d){
  const fromSettings = d.election && d.election.settings ? parseInt(d.election.settings.total_voters || 0, 10) : 0;
  const fromSections = d.ballot_totals ? parseInt(d.ballot_totals.voters || 0, 10) : 0;
  return fromSettings > 0 ? fromSettings : fromSections;
}

function pctOnVoters(value, total){
  if(!total || total <= 0) return "0.00%";
  return ((value / total) * 100).toFixed(2) + "%";
}

function listSeatsFor(d, listName){
  return d.election && d.election.list_seats ? (d.election.list_seats[listName] || 0) : 0;
}

function drawMainCharts(d){
  if(!hasEl("mayorPieChart") && !hasEl("listPieChart") && !hasEl("listBarChart")) return;
  destroyChart(mayorPieChart); destroyChart(listPieChart); destroyChart(listBarChart);

  const mayorLabels=d.mayors.map(x=>x.name);
  const mayorValues=d.mayors.map(x=>x.total||0);
  if(hasEl("mayorPieChart")){
    mayorPieChart=new Chart(document.getElementById("mayorPieChart"),{
      type:"pie",
      data:{labels:mayorLabels,datasets:[{data:mayorValues,backgroundColor:typeof colorPalette==="function"?colorPalette(mayorLabels.length):undefined}]},
      options:{responsive:true,plugins:{legend:{position:"bottom"}}}
    });
  }

  const listLabels=d.lists.map(x=>x.name);
  const listValues=d.lists.map(x=>x.total||0);
  if(hasEl("listPieChart")){
    listPieChart=new Chart(document.getElementById("listPieChart"),{
      type:"pie",
      data:{labels:listLabels,datasets:[{data:listValues,backgroundColor:typeof colorPalette==="function"?colorPalette(listLabels.length):undefined}]},
      options:{responsive:true,plugins:{legend:{position:"bottom"}}}
    });
  }

  if(hasEl("listBarChart")){
    listBarChart=new Chart(document.getElementById("listBarChart"),{
      type:"bar",
      data:{labels:listLabels,datasets:[{data:listValues,label:"Voti lista",backgroundColor:typeof colorPalette==="function"?colorPalette(listLabels.length):undefined}]},
      options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{autoSkip:false,maxRotation:70,minRotation:30}},y:{beginAtZero:true}}}
    });
  }
}
function renderSections(d){
  const tb=document.getElementById("sections");
  if(!tb) return;
  tb.innerHTML="";
  d.sections.forEach(s=>{
    const calculated=(s.total_lists||0)+(s.blank_ballots||0)+(s.null_ballots||0);
    const ok=calculated===(s.voters||0);
    const statusHtml = s.closed
      ? `<span class="badge">CHIUSO</span><br>
         <button class="secondary" onclick="reopenSection('${s.section}')">
           Riapri seggio al rappresentante
         </button>`
      : `<span class="muted">aperto</span>`;

    const tr=document.createElement("tr");
    tr.innerHTML=`
      <td>${s.section}</td>
      <td>${s.representative}</td>
      <td>${s.voters||0}</td>
      <td>${s.total_lists||0}</td>
      <td>${s.blank_ballots||0}</td>
      <td>${s.null_ballots||0}</td>
      <td>${s.section_electors||s.contested_ballots||0}</td>
      <td>${s.split_vote_count||0}</td>
      <td>${ok?"OK":"NO ("+calculated+")"}<br>${statusHtml}</td>
      <td>${s.updated_at}</td>`;
    tb.appendChild(tr);
  });
}


function availableDetailLists(d){
  return getAllListNamesFromDashboard(d);
}

function renderPrefTableTabs(d){
  const tabs=document.getElementById("prefTableTabs");
  const box=document.getElementById("prefTables");
  if(!tabs || !box) return;
  tabs.innerHTML="";
  const available=availableDetailLists(d);
  if(!available.length){
    tabs.innerHTML="<p class='small'>Nessuna lista caricata. Importare prima liste e candidati consiglieri.</p>";
    box.innerHTML="";
    return;
  }
  if(!currentPrefTableList || !available.includes(currentPrefTableList)) currentPrefTableList=available[0];

  available.forEach(listName=>{
    const btn=document.createElement("button");
    btn.className="tab"+(listName===currentPrefTableList?" active":"");
    btn.textContent=listName;
    btn.onclick=()=>{currentPrefTableList=listName; renderPrefTableTabs(lastData);};
    tabs.appendChild(btn);
  });

  const listName=currentPrefTableList;
  const totals={};
  d.preferences.filter(x=>x.list_name===listName).forEach(x=>totals[x.name]=x.total||0);
  const ranked=d.data.lists[listName].candidates.map((name,idx)=>({name,total:totals[name]||0,order:idx+1}))
    .sort((a,b)=>b.total-a.total || a.order-b.order);

  let html=`<div class="card"><h3>${listName}</h3><div class="tablewrap"><table><tr><th>Pos.</th><th>Candidato</th><th>Preferenze</th></tr>`;
  ranked.forEach((r,i)=>html+=`<tr><td>${i+1}</td><td>${r.name}</td><td>${r.total}</td></tr>`);
  html+="</table></div></div>";
  box.innerHTML=html;
}

function renderElected(d){
  if(!hasEl("electedBox")) return;
  const e=d.election, s=e.settings;
  let html=`<p><b>Sindaco/coalizione vincente:</b> ${s.winner_mayor}<br>
  <b>Premio di maggioranza:</b> ${e.premium_applied?"APPLICATO":"NON applicato"} ${e.premium_applied?`(${e.premium_seats} seggi)`:""}<br>
  <span class="small">Coalizione vincente: ${e.winner_pct.toFixed(2)}%. Maggior altra coalizione: ${e.other_max_pct.toFixed(2)}%.</span></p>`;

  html+=`<h3>Seggi per coalizione</h3><div class="tablewrap"><table><tr><th>Coalizione</th><th>Voti liste ammesse</th><th>Seggi</th></tr>`;
  Object.entries(e.coalition_seats).sort((a,b)=>b[1]-a[1]).forEach(([c,seats])=>html+=`<tr><td>${c}</td><td>${e.coalition_votes[c]||0}</td><td><b>${seats}</b></td></tr>`);
  html+=`</table></div><h3>Seggi per lista ed eletti simulati</h3><div class="tablewrap"><table><tr><th>Lista</th><th>Coalizione</th><th>Voti</th><th>Seggi</th><th>Eletti</th></tr>`;

  Object.entries(d.data.lists).forEach(([l,obj])=>{
    const seats=e.list_seats[l]||0;
    const elected=(e.elected[l]||[]).map(x=>`<div class="elected">${x.name} (${x.votes})</div>`).join("");
    const under=(e.list_votes[l]||0)>0 && !e.admitted_lists[l] ? ` <span class="badge">sotto soglia 5%</span>`:"";
    html+=`<tr><td>${l}${under}</td><td>${obj.coalition}</td><td>${e.list_votes[l]||0}</td><td><b>${seats}</b></td><td>${elected||"<span class='muted'>Nessun candidato consigliere gestito</span>"}</td></tr>`;
  });
  html+=`</table></div>`;
  document.getElementById("electedBox").innerHTML=html;
}

function destroyDetailCharts(){ detailCharts.forEach(c=>c.destroy()); detailCharts=[]; }
function showChartTab(tab){
  ["lists","prefs"].forEach(t=>{
    const panel=document.getElementById("chartTab"+cap(t));
    const button=document.getElementById("tabCharts"+cap(t));
    if(panel) panel.classList.toggle("hidden", t!==tab);
    if(button) button.classList.toggle("active", t===tab);
  });
}
function cap(s){ return s.charAt(0).toUpperCase()+s.slice(1); }
function makeCanvasCard(title,id){ const d=document.createElement("div"); d.className="card"; d.innerHTML=`<h3>${title}</h3><canvas id="${id}"></canvas>`; return d; }
function chartOn(id,labels,values,label){
  const ch=new Chart(document.getElementById(id),{
    type:"bar", data:{labels,datasets:[{label,data:values}]},
    options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{autoSkip:false,maxRotation:70,minRotation:30}}}}
  });
  detailCharts.push(ch);
}

async function renderDetailCharts(){
  if(!hasEl("chartTabLists") && !hasEl("chartTabPrefs")) return;
  destroyDetailCharts();
  const listsBox=document.getElementById("chartTabLists");
  const prefsBox=document.getElementById("chartTabPrefs");
  if(listsBox) listsBox.innerHTML="";
  if(prefsBox) prefsBox.innerHTML="";
  const d=await api("/api/section-details");
  const sections=Object.keys(d.sections).sort((a,b)=>(parseInt(a)||0)-(parseInt(b)||0) || a.localeCompare(b));
  const available=availableDetailLists(d);
  if(sections.length===0){ if(listsBox) listsBox.innerHTML="<p class='small'>Nessun dato di sezione.</p>"; if(prefsBox) prefsBox.innerHTML="<p class='small'>Nessun dato di sezione.</p>"; return; }
  if(!available.length){ if(listsBox) listsBox.innerHTML="<p class='small'>Nessuna lista caricata.</p>"; if(prefsBox) prefsBox.innerHTML="<p class='small'>Nessun candidato caricato.</p>"; return; }


  const listTabBar=document.createElement("div"), listContent=document.createElement("div");
  listTabBar.className="tabs"; listsBox.append(listTabBar,listContent);
  function showList(listName,idx){
    [...listTabBar.children].forEach(b=>b.classList.remove("active"));
    if(listTabBar.children[idx]) listTabBar.children[idx].classList.add("active");
    listContent.innerHTML="";
    const id=`chart_list_${idx}`;
    listContent.appendChild(makeCanvasCard(listName,id));
    chartOn(id,sections,sections.map(sec=>d.sections[sec].lists[listName]||0),"Voti lista");
  }
  available.forEach((listName,idx)=>{
    const b=document.createElement("button"); b.className="tab"+(idx===0?" active":""); b.textContent=listName; b.onclick=()=>showList(listName,idx); listTabBar.appendChild(b);
  });
  if(available[0]) showList(available[0],0);

  const prefTabBar=document.createElement("div"), prefContent=document.createElement("div");
  prefTabBar.className="tabs"; prefsBox.append(prefTabBar,prefContent);
  function showPrefs(listName,idx){
    [...prefTabBar.children].forEach(b=>b.classList.remove("active"));
    if(prefTabBar.children[idx]) prefTabBar.children[idx].classList.add("active");
    prefContent.innerHTML="";
    const wrap=document.createElement("div"); wrap.className="card"; wrap.innerHTML=`<h3>${listName}</h3>`;
    prefContent.appendChild(wrap);
    d.data.lists[listName].candidates.forEach((candidate,cidx)=>{
      const id=`chart_pref_${idx}_${cidx}`;
      wrap.appendChild(makeCanvasCard(candidate,id));
      chartOn(id,sections,sections.map(sec=>((d.sections[sec].preferences[listName]||{})[candidate])||0),"Preferenze");
    });
  }
  available.forEach((listName,idx)=>{
    const b=document.createElement("button"); b.className="tab"+(idx===0?" active":""); b.textContent=listName; b.onclick=()=>showPrefs(listName,idx); prefTabBar.appendChild(b);
  });
  if(available[0]) showPrefs(available[0],0);
}

let usersCache=[];

async function loadUsers(){
  if(!hasEl("users")) return;
  const d=await api("/api/users");
  usersCache=d.users || [];
  electionListNames=d.lists || [];
  renderNewUserListChecks();
  const box=document.getElementById("users");
  box.innerHTML="";

  usersCache.forEach(u=>{
    const link=`${location.origin}/?token=${u.qr_token}`;
    const div=document.createElement("div");
    div.className="card";
    div.innerHTML=`
      <h3>${escapeHtml(u.name)}</h3>
      <p class="small">
        <b>Codice:</b> ${escapeHtml(u.phone)}<br>
        <b>Ruolo:</b> ${escapeHtml(u.role)}<br>
        <b>Sezione:</b> ${escapeHtml(u.section||"tutte")}<br>
        <b>Liste autorizzate:</b> ${escapeHtml(u.allowed_lists||"tutte")}<br>
        <b>Stato:</b> ${u.active?"attivo":"disattivato"}
      </p>
      <label>Link QR/accesso</label>
      <input value="${escapeAttr(link)}" readonly onclick="this.select()">
      <div class="actions">
        <button onclick="openEditUserPopup(${u.id})">Edit</button>
        <button class="secondary" onclick="toggleUser(${u.id})">${u.active?"Disattiva":"Riattiva"}</button>
        <button class="danger" onclick="deleteUser(${u.id})">Rimuovi</button>
      </div>
    `;
    box.appendChild(div);
  });
}

function escapeHtml(value){
  return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

function escapeAttr(value){
  return String(value ?? "").replaceAll("&","&amp;").replaceAll('"',"&quot;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}


function splitAllowedListsText(value){
  return String(value||"").split("|").map(x=>x.trim()).filter(Boolean);
}
function renderListPermissionChecks(containerId, inputId, selected=[]){
  const box=document.getElementById(containerId);
  const input=document.getElementById(inputId);
  if(!box || !input) return;
  const selectedSet=new Set(selected);
  if(!electionListNames.length){
    box.innerHTML='<p class="small warn">Carica prima le liste da Importazioni CSV per poterle assegnare ai rilevatori.</p>';
    return;
  }
  box.innerHTML=electionListNames.map((name,i)=>`<label class="checkItem"><input type="checkbox" value="${escapeAttr(name)}" ${selectedSet.has(name)?'checked':''}> ${escapeHtml(name)}</label>`).join("");
  const sync=()=>{ input.value=Array.from(box.querySelectorAll('input[type="checkbox"]:checked')).map(x=>x.value).join('|'); };
  box.querySelectorAll('input[type="checkbox"]').forEach(cb=>cb.addEventListener('change', sync));
  input.addEventListener('input', ()=>renderListPermissionChecks(containerId,inputId,splitAllowedListsText(input.value)), {once:true});
}
function renderNewUserListChecks(){ renderListPermissionChecks('newAllowedListsChecks','newAllowedLists', splitAllowedListsText(document.getElementById('newAllowedLists')?.value)); }

function openEditUserPopup(id){
  const u=usersCache.find(x=>x.id===id);
  if(!u){ alert("Utente non trovato."); return; }
  document.getElementById("editUserId").value=u.id;
  document.getElementById("editUserName").value=u.name || "";
  document.getElementById("editUserPhone").value=u.phone || "";
  document.getElementById("editUserSection").value=u.section || "";
  document.getElementById("editUserRole").value=u.role || "rappresentante";
  document.getElementById("editUserPin").value="";
  if(document.getElementById("editUserAllowedLists")) document.getElementById("editUserAllowedLists").value=u.allowed_lists||"";
  renderListPermissionChecks("editAllowedListsChecks","editUserAllowedLists", splitAllowedListsText(u.allowed_lists));
  document.getElementById("editUserModal").classList.remove("hidden");
}

function closeEditUserPopup(){
  document.getElementById("editUserModal").classList.add("hidden");
}

async function saveEditUserPopup(){
  const id=document.getElementById("editUserId").value;
  const payload={
    name:document.getElementById("editUserName").value.trim(),
    phone:document.getElementById("editUserPhone").value.trim(),
    section:document.getElementById("editUserSection").value.trim(),
    role:document.getElementById("editUserRole").value,
    pin:document.getElementById("editUserPin").value.trim(),
    allowed_lists: splitAllowedListsText(document.getElementById("editUserAllowedLists")?.value)
  };
  if(!payload.name || !payload.phone){
    alert("Nome e telefono/codice sono obbligatori.");
    return;
  }
  try{
    const res=await api(`/api/users/${id}`,{method:"PATCH",body:JSON.stringify(payload)});
    alert(res.message || "Utente aggiornato.");
    closeEditUserPopup();
    await loadUsers();
  }catch(e){ alert(e.message); }
}


async function createUser(){try{await api("/api/users",{method:"POST",body:JSON.stringify({name:document.getElementById("newName").value.trim(),phone:document.getElementById("newPhone").value.trim(),pin:document.getElementById("newPin").value.trim(),section:document.getElementById("newSection").value.trim(),role:document.getElementById("newRole").value,allowed_lists:(document.getElementById("newAllowedLists")?.value||"").split("|").map(x=>x.trim()).filter(Boolean)})});alert("Utente creato");await loadUsers()}catch(e){alert(e.message)}}
async function deleteUser(id){if(!confirm("Rimuovere definitivamente questo utente?"))return;try{await api(`/api/users/${id}`,{method:"DELETE"});await loadUsers()}catch(e){alert(e.message)}}
async function toggleUser(id){if(!confirm("Cambiare stato utente?"))return;try{await api(`/api/users/${id}/toggle`,{method:"PATCH",body:"{}"});await loadUsers()}catch(e){alert(e.message)}}
async function reopenSection(section){if(!confirm(`Riaprire il seggio ${section}?`))return;try{await api("/api/reopen-section",{method:"POST",body:JSON.stringify({section})});alert("Seggio riaperto");await loadDashboard()}catch(e){alert(e.message)}}
async function resetVotes(){const c=prompt("Per confermare scrivi: AZZERA");if(c!=="AZZERA")return alert("Operazione annullata");try{await api("/api/reset-votes",{method:"POST",body:JSON.stringify({confirm:"AZZERA"})});alert("Voti azzerati");await loadDashboard()}catch(e){alert(e.message)}}

async function loadElectionEditor(){
  if(!hasEl("electionDataEditor")) return;
  const d=await api("/api/election-data");
  document.getElementById("electionDataEditor").value=JSON.stringify(d.data,null,2);
}
function formatElectionEditor(){
  try{const el=document.getElementById("electionDataEditor"); el.value=JSON.stringify(JSON.parse(el.value),null,2);}catch(e){alert("JSON non valido: "+e.message)}
}
async function saveElectionEditor(){
  try{const data=JSON.parse(document.getElementById("electionDataEditor").value); const r=await api("/api/election-data",{method:"POST",body:JSON.stringify({data})}); alert(r.message||"Configurazione salvata"); await loadDashboard();}
  catch(e){alert(e.message)}
}

loadDashboard();
if(hasEl("electionDataEditor")) loadElectionEditor();
setInterval(loadDashboard,30000);




window.addEventListener('unhandledrejection', function(e){
  console.error(e.reason || e);
});


async function importUsersCsv(){
  const input = document.getElementById("csvUsersFile");

  if(!input || !input.files || !input.files.length){
    alert("Seleziona un file CSV.");
    return;
  }

  const fd = new FormData();
  fd.append("file", input.files[0]);

  try{
    const res = await fetch("/api/users/import-csv", {
      method: "POST",
      body: fd,
      credentials: "include",
      headers: {"Accept": "application/json"}
    });

    const text = await res.text();
    let data = null;

    try{
      data = JSON.parse(text);
    }catch(e){
      console.error("Risposta non JSON:", text);
      throw new Error("Endpoint CSV non disponibile o errore server. Controlla il deploy Render e i log.");
    }

    if(!res.ok || !data.ok){
      throw new Error(data.error || "Errore import CSV");
    }

    let msg = data.message || "CSV importato.";
    if(data.errors && data.errors.length){
      msg += "\n\nPrime righe saltate:\n" + data.errors.join("\n");
    }

    alert(msg);
    input.value = "";
    await loadUsers();

  }catch(e){
    alert(e.message);
  }
}


async function importSectionsCsv(){
  const input = document.getElementById("csvSectionsFile");

  if(!input || !input.files || !input.files.length){
    alert("Seleziona un file CSV sezioni.");
    return;
  }

  const fd = new FormData();
  fd.append("file", input.files[0]);

  try{
    const res = await fetch("/api/sections/import-csv", {
      method: "POST",
      body: fd,
      credentials: "include",
      headers: {"Accept": "application/json"}
    });

    const text = await res.text();
    let data = null;

    try{
      data = JSON.parse(text);
    }catch(e){
      console.error("Risposta non JSON:", text);
      throw new Error("Endpoint import sezioni non disponibile o errore server.");
    }

    if(!res.ok || !data.ok){
      throw new Error(data.error || "Errore import CSV sezioni");
    }

    let msg = data.message || "CSV sezioni importato.";
    if(data.errors && data.errors.length){
      msg += "\n\nPrime righe saltate:\n" + data.errors.join("\n");
    }

    alert(msg);
    input.value = "";
    await loadDashboard();

  }catch(e){
    alert(e.message);
  }
}


async function importGenericCsv(inputId, endpoint){
  const input=document.getElementById(inputId);
  if(!input || !input.files || !input.files.length){ alert("Seleziona un file CSV."); return; }
  const fd=new FormData(); fd.append("file", input.files[0]);
  try{
    const res=await fetch(endpoint,{method:"POST",body:fd,credentials:"include",headers:{"Accept":"application/json"}});
    const text=await res.text();
    let data;
    try{ data=JSON.parse(text); }catch(e){ console.error(text); throw new Error("Risposta non valida dal server. Controlla i log Render."); }
    if(!res.ok || !data.ok) throw new Error(data.error || "Errore import CSV");
    let msg=data.message || "Import completato.";
    if(data.errors && data.errors.length){ msg += "\n\nPrime righe saltate:\n" + data.errors.join("\n"); }
    alert(msg); input.value=""; await loadDashboard();
  }catch(e){ alert(e.message); }
}
