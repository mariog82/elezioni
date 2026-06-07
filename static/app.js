let user=null, DATA=null, settings=null, currentList=null, anagraphics=null;
let mayorVotes={}, listVotes={}, prefs={}, splitVotes=[];
let autosaveTimer=null, autosaveBusy=false, lastSavedPayload="";

async function api(url, options={}){
  const res=await fetch(url,{credentials:"include",headers:{"Content-Type":"application/json"},...options});
  const data=await res.json();
  if(!res.ok||data.ok===false) throw new Error(data.error||"Errore server");
  return data;
}
const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/=/g,'').replace(/\+/g,'_').replace(/\//g,'-');
const nval=id=>Math.max(0,parseInt(document.getElementById(id)?.value||"0",10)||0);
const sum=o=>Object.values(o||{}).reduce((a,b)=>a+(parseInt(b||0,10)||0),0);
const esc=s=>String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
function isAdmin(){return user && user.role==="admin";}
function allowedListNames(){ return Object.keys(DATA?.lists||{}); }

function buildPayload(){
  return {
    section:document.getElementById("section")?.value.trim()||"",
    voters:nval("voters"),
    blank_ballots:nval("blankBallots"),
    null_ballots:nval("nullBallots"),
    section_electors:nval("sectionElectors"),
    mayors:mayorVotes,
    list_votes:listVotes,
    preferences:prefs,
    split_votes:splitVotes
  };
}

function markDirty(){
  updateValidationBox();
  setSaveStatus("Modifiche non ancora salvate", "warn");
  if(autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer=setTimeout(autoSave, 1200);
}
function setSaveStatus(text, cls=""){
  const el=document.getElementById("saveStatus");
  if(!el) return;
  el.className="statusPill "+cls;
  el.textContent=text;
}
async function autoSave(){
  if(autosaveBusy) return;
  const payload=buildPayload();
  if(!payload.section) return;
  const serialized=JSON.stringify(payload);
  if(serialized===lastSavedPayload) return;
  autosaveBusy=true; setSaveStatus("Salvataggio automatico...", "");
  try{
    const d=await api("/api/report",{method:"POST",body:serialized});
    lastSavedPayload=serialized;
    setSaveStatus("Salvato automaticamente", "okpill");
    if(d.updated_at) document.getElementById("lastUpdate").textContent=d.updated_at;
  }catch(e){ setSaveStatus("Autosave non riuscito: "+e.message, "badpill"); }
  finally{ autosaveBusy=false; }
}

async function start(){
  const token=new URLSearchParams(location.search).get("token");
  if(token){try{await api("/api/login",{method:"POST",body:JSON.stringify({token})});history.replaceState({},"","/app")}catch(e){alert("QR non valido")}}
  try{const me=await api("/api/me");user=me.user;await showApp()}catch(e){ location.href="/" }
}
async function login(){
  try{const d=await api("/api/login",{method:"POST",body:JSON.stringify({phone:phone.value.trim(),pin:pin.value.trim()})});user=d.user;await showApp()}catch(e){alert(e.message)}
}
async function logout(){try{await api("/api/logout",{method:"POST",body:"{}"});}catch(e){} location.href="/logout"}
async function logoutClosed(){await logout()}

async function showApp(){
  loginBox.classList.add("hidden"); appBox.classList.remove("hidden");
  userName.textContent=user.name;
  userInfo.textContent=`Ruolo: ${user.role} - Sezione: ${user.section||"tutte"} - Liste autorizzate: ${(user.allowed_lists||[]).length?(user.allowed_lists||[]).join(", "):"tutte"}`;
  if(isAdmin()){ document.getElementById("adminBtn")?.classList.remove("hidden"); document.getElementById("topAdminLink")?.classList.remove("hidden"); }
  const cfg=await api("/api/config"); DATA=cfg.data; settings=cfg.settings; anagraphics=cfg.anagraphics;
  if(!anagraphics?.loaded){ showMissingAnagraphics(); return; }
  initState(); renderAll(); renderAnagraphicsOverview(); bindInputs(); lockRepresentativeSection(); await loadExisting(); await checkClosedStatus(); updateValidationBox();
}
function showMissingAnagraphics(){
  const app=document.getElementById("appBox");
  const msg=anagraphics?.message || "Caricare prima candidati sindaco e liste/consiglieri.";
  const steps=(anagraphics?.required_order||[]).map(x=>`<li>${esc(x)}</li>`).join("");
  app.innerHTML=`<div class="card warningCard"><h2>Configurazione elettorale obbligatoria</h2><p>${esc(msg)}</p><ul>${steps}</ul><p><b>Stato attuale:</b> ${anagraphics?.mayors_count||0} sindaci, ${anagraphics?.lists_count||0} liste, ${anagraphics?.candidates_count||0} candidati consiglieri.</p>${isAdmin()?'<a class="btn primary" href="/admin/imports">Vai alle importazioni CSV</a>':'<p>Contattare l'amministratore della piattaforma.</p>'}</div>`;
}

function initState(){
  mayorVotes={}; listVotes={}; prefs={};
  DATA.mayors.forEach(m=>mayorVotes[m]=0);
  Object.entries(DATA.lists).forEach(([l,o])=>{listVotes[l]=0; prefs[l]={}; o.candidates.forEach(c=>prefs[l][c]=0)});
  currentList=Object.keys(DATA.lists)[0]||null;
}
function bindInputs(){
  ["section","voters","blankBallots","nullBallots","sectionElectors"].forEach(id=>document.getElementById(id)?.addEventListener("input",markDirty));
}
function lockRepresentativeSection(){
  const el=document.getElementById("section");
  if(user.role!=="admin" && user.section){el.value=user.section; el.readOnly=true; el.classList.add("readonly")}
}
async function checkClosedStatus(){
  if(isAdmin()) return;
  const section=sectionInput(); if(!section) return;
  const st=await api(`/api/section-status?section=${encodeURIComponent(section)}`);
  if(st.closed){appBox.classList.add("hidden");closedBox.classList.remove("hidden")}
}
function sectionInput(){return document.getElementById("section")?.value.trim() || user?.section || ""}
async function loadExisting(){
  const section=sectionInput(); if(!section) return;
  const d=await api(`/api/my-report?section=${encodeURIComponent(section)}`);
  if(!d.exists) return;
  voters.value=d.voters||0; blankBallots.value=d.blank_ballots||0; nullBallots.value=d.null_ballots||0; sectionElectors.value=d.section_electors||0;
  Object.assign(mayorVotes,d.mayors||{}); Object.assign(listVotes,d.list_votes||{});
  Object.entries(d.preferences||{}).forEach(([l,obj])=>{prefs[l]=prefs[l]||{}; Object.assign(prefs[l],obj)});
  splitVotes=d.split_votes||[];
  lastSavedPayload=JSON.stringify(buildPayload());
  if(d.updated_at) lastUpdate.textContent=d.updated_at;
  renderAll(); setSaveStatus("Dati caricati dal server", "okpill");
}

function renderAnagraphicsOverview(){
  const box=document.getElementById("anagraphicsOverview");
  if(!box || !DATA) return;
  const mayors=(DATA.mayors||[]).map(m=>`<span class="badge">${esc(m)}</span>`).join(" ") || "<span class='small'>Nessun sindaco caricato.</span>";
  const lists=Object.entries(DATA.lists||{}).map(([lname,obj])=>{
    const candidates=(obj.candidates||[]).map(c=>`<li>${esc(c)}</li>`).join("");
    return `<details class="listDetails"><summary><b>${esc(lname)}</b> <span class="small">Coalizione/Sindaco: ${esc(obj.coalition||'—')} · ${(obj.candidates||[]).length} candidati</span></summary><ol>${candidates}</ol></details>`;
  }).join("") || "<p class='small'>Nessuna lista caricata.</p>";
  box.innerHTML=`<div class="overviewBlock"><h3>Candidati sindaco</h3><div class="badgeWrap">${mayors}</div></div><div class="overviewBlock"><h3>Liste e consiglieri</h3>${lists}</div>`;
}

function renderAll(){ renderMayors(); renderTabs(); renderListPanel(); renderSplitVotes(); renderAnagraphicsOverview(); }
function renderMayors(){
  const box=mayorList; box.innerHTML="";
  DATA.mayors.forEach(m=>box.appendChild(voteRow(m,"mayor",null)));
}
function renderTabs(){
  tabs.innerHTML="";
  Object.keys(DATA.lists).forEach(l=>{
    const b=document.createElement("button"); b.className="tab"+(l===currentList?" active":""); b.textContent=l; b.onclick=()=>{currentList=l; renderTabs(); renderListPanel();}; tabs.appendChild(b);
  });
}
function renderListPanel(){
  const panel=listPanel; panel.innerHTML=""; if(!currentList) return;
  const obj=DATA.lists[currentList];
  const head=document.createElement("div"); head.className="listHeader"; head.innerHTML=`<div><b>${esc(currentList)}</b><br><span class="small">Coalizione/Sindaco: ${esc(obj.coalition)}</span></div>`; panel.appendChild(head);
  panel.appendChild(voteRow(currentList,"list",currentList));
  const search=document.createElement("input"); search.placeholder="Filtra candidato consigliere..."; search.className="search"; panel.appendChild(search);
  const candidates=document.createElement("div"); panel.appendChild(candidates);
  const draw=()=>{candidates.innerHTML=""; const q=search.value.toLowerCase(); obj.candidates.filter(c=>c.toLowerCase().includes(q)).forEach(c=>candidates.appendChild(voteRow(c,"pref",currentList)));};
  search.oninput=draw; draw();
}
function voteRow(name,type,list){
  const r=document.createElement("div"); r.className="row adminrow";
  const val= type==="mayor"?mayorVotes[name]||0:type==="list"?listVotes[list]||0:prefs[list]?.[name]||0;
  r.innerHTML=`<div class="name">${esc(name)}</div><div class="votes">${val}</div><input class="adminVoteInput" type="number" min="0" value="${val}"><button class="plus">+</button><button class="minus">-</button>`;
  const input=r.querySelector("input"), out=r.querySelector(".votes");
  const set=v=>{v=Math.max(0,parseInt(v||0,10)||0); if(type==="mayor") mayorVotes[name]=v; else if(type==="list") listVotes[list]=v; else {prefs[list]=prefs[list]||{}; prefs[list][name]=v;} input.value=v; out.textContent=v; markDirty();};
  input.oninput=()=>set(input.value); r.querySelector(".plus").onclick=()=>set((parseInt(input.value)||0)+1); r.querySelector(".minus").onclick=()=>set((parseInt(input.value)||0)-1);
  return r;
}
function updateValidationBox(){
  const validMayor=sum(mayorVotes), validLists=sum(listVotes), blank=nval("blankBallots"), nul=nval("nullBallots"), voters=nval("voters"), electors=nval("sectionElectors");
  const valid=Math.max(validMayor,validLists); const expected=valid+blank+nul; const split=sumSplitVotes();
  const diff=voters-expected;
  validationBox.innerHTML=`<b>Quadratura sezione</b><br>Elettori: ${electors} · Votanti: ${voters} · Voti sindaco: ${validMayor} · Voti lista: ${validLists} · Bianche: ${blank} · Nulle: ${nul}<br>Controllo: votanti - (validi max + bianche + nulle) = <b>${diff}</b> ${diff===0?"✅ OK":"⚠️ da verificare"}<br>Voti disgiunti censiti: <b>${split}</b>`;
}
function sumSplitVotes(){return splitVotes.reduce((a,x)=>a+(parseInt(x.votes||0,10)||0),0)}

function renderSplitSelectors(){
  splitMayor.innerHTML=DATA.mayors.map(m=>`<option value="${esc(m)}">${esc(m)}</option>`).join("");
  splitList.innerHTML=Object.keys(DATA.lists).map(l=>`<option value="${esc(l)}">${esc(l)}</option>`).join("");
  splitList.onchange=()=>{ const l=splitList.value; splitCandidate.innerHTML=(DATA.lists[l]?.candidates||[]).map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join(""); };
  splitList.onchange();
}
function addSplitVote(){
  const mayor=splitMayor.value, list=splitList.value, candidate=splitCandidate.value, votes=Math.max(1,parseInt(splitCount.value||1,10)||1);
  const coalition=DATA.lists[list]?.coalition;
  const isSplit= mayor && list && coalition && mayor!==coalition;
  splitVotes.push({mayor,list,candidate,votes,is_split:isSplit,coalition});
  splitCount.value=1; renderSplitVotes(); markDirty();
}
function removeSplitVote(i){ splitVotes.splice(i,1); renderSplitVotes(); markDirty(); }
function renderSplitVotes(){
  renderSplitSelectors(); const box=splitTable; box.innerHTML="";
  splitVotes.forEach((x,i)=>{ const div=document.createElement("div"); div.className="splitRow"; div.innerHTML=`<span class="badge ${x.is_split?'splitYes':'splitNo'}">${x.is_split?'DISGIUNTO':'NON DISGIUNTO'}</span><b>${esc(x.votes)}</b> voto/i · Sindaco ${esc(x.mayor)} + ${esc(x.list)} ${x.candidate?' / '+esc(x.candidate):''}<button class="danger" onclick="removeSplitVote(${i})">Rimuovi</button>`; box.appendChild(div); });
  updateValidationBox();
}
async function sendReport(){
  try{const payload=buildPayload(); const d=await api("/api/report",{method:"POST",body:JSON.stringify(payload)}); lastSavedPayload=JSON.stringify(payload); setSaveStatus("Invio manuale completato", "okpill"); alert(d.message||"Dati inviati")}catch(e){alert(e.message)}
}
async function closeSeat(){
  if(!confirm("Chiudere definitivamente il seggio? Dopo la chiusura il rappresentante non potrà più modificare i dati.")) return;
  try{const d=await api("/api/close-seat",{method:"POST",body:JSON.stringify(buildPayload())}); alert(d.message); location.reload()}catch(e){alert(e.message)}
}
function generateMessage(){
  const p=buildPayload();
  messageBox.value=`SEZIONE ${p.section}\nElettori: ${p.section_electors}\nVotanti: ${p.voters}\nBianche: ${p.blank_ballots}\nNulle: ${p.null_ballots}\nVoti sindaco: ${sum(p.mayors)}\nVoti lista: ${sum(p.list_votes)}\nVoti disgiunti censiti: ${sumSplitVotes()}\nUltimo aggiornamento: ${new Date().toLocaleString('it-IT')}`;
}
function copyMessage(){messageBox.select();document.execCommand("copy")}
function clearMessage(){messageBox.value=""}

start();
