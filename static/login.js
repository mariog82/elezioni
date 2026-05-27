async function api(url, options={}){
  const res = await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json'},...options});
  const data = await res.json();
  if(!res.ok || data.ok===false) throw new Error(data.error || 'Errore server');
  return data;
}
function setMsg(text, kind=''){
  const el=document.getElementById('loginMsg');
  el.className='loginMsg small '+kind; el.textContent=text||'';
}
async function login(){
  const phone=document.getElementById('phone').value.trim();
  const pin=document.getElementById('pin').value.trim();
  const btn=document.getElementById('loginBtn');
  if(!phone || !pin){ setMsg('Compila telefono/codice e PIN.', 'bad'); return; }
  btn.disabled=true; btn.textContent='Accesso in corso...'; setMsg('Verifica credenziali...', '');
  try{
    const d=await api('/api/login',{method:'POST',body:JSON.stringify({phone,pin})});
    setMsg('Accesso riuscito. Apertura area di lavoro...', 'ok');
    location.href = d.user && d.user.role === 'admin' ? '/admin' : '/app';
  }catch(e){ setMsg(e.message, 'bad'); }
  finally{ btn.disabled=false; btn.textContent='Entra'; }
}
async function boot(){
  const token=new URLSearchParams(location.search).get('token');
  if(token){
    try{ const d=await api('/api/login',{method:'POST',body:JSON.stringify({token})}); location.href=d.user.role==='admin'?'/admin':'/app'; return; }
    catch(e){ setMsg('QR/token non valido o non più attivo.', 'bad'); }
  }
  try{ const me=await api('/api/me'); location.href = me.user.role==='admin'?'/admin':'/app'; }catch(e){}
}
document.addEventListener('keydown', e=>{ if(e.key==='Enter') login(); });
boot();
