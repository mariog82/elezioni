"""
Focus360 Political Intelligence - Multitenant Edition
====================================================
Reingegnerizzazione SaaS reale della precedente piattaforma elettorale.

Caratteristiche principali:
- SuperAdmin di piattaforma: crea tenant/organizzazioni politiche, admin, moduli, piani, scadenze e API key.
- Multitenancy applicativo: ogni tabella operativa contiene tenant_id; utenti, dati elettorali, voti, report e configurazioni sono isolati.
- Compatibilità UI esistente: mantiene gli endpoint /api/... già usati dal frontend, ma li filtra sempre sul tenant corrente.
- API pubbliche versionate: /api/v1/... con autenticazione Bearer tramite API key di tenant.
- Moduli AI reali: statistiche descrittive, proiezione Bayes/Laplace, regressione lineare per turnout e predizione voti, clustering euristico territoriale, alert anomalie.

Nota produzione: SQLite resta supportato per demo e piccoli clienti. Per decine/centinaia di tenant usare DATABASE_URL PostgreSQL,
processi worker separati, HTTPS, rate limit e backup automatici.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import math
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except Exception:  # fallback per ambienti minimi
    np = None
    KMeans = None
    RandomForestRegressor = None
    LinearRegression = None
    SKLEARN_AVAILABLE = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_SQLITE_PATH", os.path.join(APP_DIR, "database.sqlite"))
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.environ.get("APP_SECRET_KEY", secrets.token_hex(32))

MODULE_CATALOG = {
    "intelligence": {"title": "Political Intelligence AI", "area": "Premium", "path": "/admin/intelligence", "description": "Heatmap, regressione, clustering, anomalie e peso politico."},
    "social": {"title": "Dashboard social", "area": "Growth", "path": "/admin/social", "description": "Card pubbliche e sintesi condivisibili."},
    "blockchain": {"title": "Electoral Audit", "area": "Trust", "path": "/admin/blockchain", "description": "Hash chain tenant-aware e registro audit."},
    "osint": {"title": "OSINT politico", "area": "Investigativo", "path": "/admin/osint", "description": "Dossier, fonti aperte e alert reputazionali."},
    "simulator": {"title": "Simulatore predittivo", "area": "Scenario", "path": "/admin/simulator", "description": "Swing, scenari affluenza e proiezioni."},
}
DEFAULT_MODULES = {k: True for k in MODULE_CATALOG}
DEFAULT_ELECTION_DATA = {"mayors": [], "lists": {}}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def safe_json_loads(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def slugify(text: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    base = "-".join(part for part in base.split("-") if part)
    return base or secrets.token_hex(3)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def table_cols(conn: sqlite3.Connection, table: str) -> List[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def add_col(conn: sqlite3.Connection, table: str, col: str, sql_type: str, default_sql: str = "") -> None:
    if col not in table_cols(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type} {default_sql}")


def init_db() -> None:
    conn = db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tenants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        organization_type TEXT DEFAULT 'organizzazione politica',
        place TEXT, cap TEXT, province TEXT, region TEXT,
        plan TEXT DEFAULT 'trial',
        status TEXT DEFAULT 'active',
        expires_at TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        qr_token TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        section TEXT,
        allowed_lists TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    )""")
    # migrazioni su vecchie installazioni
    for col, typ in [("tenant_id", "INTEGER"), ("allowed_lists", "TEXT")]:
        add_col(conn, "users", col, typ)

    c.execute("""CREATE TABLE IF NOT EXISTS tenant_settings(
        tenant_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY(tenant_id,key),
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tenant_modules(
        tenant_id INTEGER NOT NULL,
        module_key TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        expires_at TEXT,
        updated_at TEXT,
        PRIMARY KEY(tenant_id,module_key),
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admin_module_permissions(
        user_id INTEGER NOT NULL,
        module_key TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT,
        PRIMARY KEY(user_id,module_key),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        prefix TEXT NOT NULL,
        scopes TEXT NOT NULL DEFAULT 'read',
        active INTEGER NOT NULL DEFAULT 1,
        last_used_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        user_id INTEGER,
        section TEXT NOT NULL,
        voters INTEGER NOT NULL DEFAULT 0,
        blank_ballots INTEGER NOT NULL DEFAULT 0,
        null_ballots INTEGER NOT NULL DEFAULT 0,
        contested_ballots INTEGER NOT NULL DEFAULT 0,
        split_votes_json TEXT NOT NULL DEFAULT '[]',
        closed INTEGER NOT NULL DEFAULT 0,
        closed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    add_col(conn, "reports", "tenant_id", "INTEGER", "DEFAULT 1")
    for col, typ, default in [("voters","INTEGER","DEFAULT 0"),("blank_ballots","INTEGER","DEFAULT 0"),("null_ballots","INTEGER","DEFAULT 0"),("contested_ballots","INTEGER","DEFAULT 0"),("split_votes_json","TEXT","DEFAULT '[]'"),("closed","INTEGER","DEFAULT 0"),("closed_at","TEXT","")]:
        add_col(conn, "reports", col, typ, default)

    c.execute("""CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        report_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL,
        list_name TEXT,
        name TEXT NOT NULL,
        votes INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )""")
    add_col(conn, "votes", "tenant_id", "INTEGER", "DEFAULT 1")

    c.execute("""CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        user_id INTEGER,
        action TEXT NOT NULL,
        resource TEXT,
        payload_hash TEXT,
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS payment_methods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        mode TEXT NOT NULL DEFAULT 'test',
        public_key TEXT,
        webhook_url TEXT,
        notes TEXT,
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admin_profiles(
        user_id INTEGER PRIMARY KEY,
        organization TEXT, place TEXT, cap TEXT, province TEXT, region TEXT,
        usage_reason TEXT, beneficiaries TEXT, notes TEXT, updated_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # default tenant + superadmin
    if not c.execute("SELECT id FROM tenants WHERE slug='platform-demo'").fetchone():
        c.execute("INSERT INTO tenants(name,slug,place,province,region,plan,status,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("Tenant Demo Piattaforma", "platform-demo", "Barcellona Pozzo di Gotto", "ME", "Sicilia", "enterprise", "active", (datetime.now()+timedelta(days=365)).date().isoformat(), now(), now()))
    demo_tenant = c.execute("SELECT id FROM tenants WHERE slug='platform-demo'").fetchone()["id"]

    # assegna a demo vecchi record senza tenant
    c.execute("UPDATE users SET tenant_id=? WHERE tenant_id IS NULL AND role!='superadmin'", (demo_tenant,))
    c.execute("UPDATE reports SET tenant_id=? WHERE tenant_id IS NULL", (demo_tenant,))
    c.execute("UPDATE votes SET tenant_id=? WHERE tenant_id IS NULL", (demo_tenant,))

    if not c.execute("SELECT id FROM users WHERE phone='super'").fetchone():
        c.execute("INSERT INTO users(tenant_id,name,phone,pin_hash,qr_token,role,section,allowed_lists,active,created_at) VALUES(NULL,?,?,?,?,?,?,?,1,?)",
                  ("Super Utente Piattaforma", "super", generate_password_hash("0000"), secrets.token_urlsafe(24), "superadmin", None, "", now()))
    if not c.execute("SELECT id FROM users WHERE phone='admin'").fetchone():
        c.execute("INSERT INTO users(tenant_id,name,phone,pin_hash,qr_token,role,section,allowed_lists,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",
                  (demo_tenant, "Admin Tenant Demo", "admin", generate_password_hash("1234"), secrets.token_urlsafe(24), "admin", None, "", now()))

    # settings e moduli tenant
    defaults = {
        "total_electors": "0", "total_voters": "0", "council_seats": "24", "winner_mayor": "", "mode": "first",
        "election_data_json": json.dumps(DEFAULT_ELECTION_DATA, ensure_ascii=False),
    }
    for t in c.execute("SELECT id FROM tenants").fetchall():
        tid = t["id"]
        for k,v in defaults.items():
            c.execute("INSERT OR IGNORE INTO tenant_settings(tenant_id,key,value) VALUES(?,?,?)", (tid,k,v))
        for mk,en in DEFAULT_MODULES.items():
            c.execute("INSERT OR IGNORE INTO tenant_modules(tenant_id,module_key,enabled,updated_at) VALUES(?,?,?,?)", (tid,mk,int(en),now()))

    # indici tenant-aware
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_tenant_section ON reports(tenant_id, section)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_votes_tenant_report ON votes(tenant_id, report_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant_role ON users(tenant_id, role)")
    conn.commit(); conn.close()


@app.before_request
def before_request() -> None:
    init_db()


def audit(conn: sqlite3.Connection, tenant_id: Optional[int], user_id: Optional[int], action: str, resource: str, payload: Any = None) -> None:
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    conn.execute("INSERT INTO audit_log(tenant_id,user_id,action,resource,payload_hash,created_at) VALUES(?,?,?,?,?,?)",
                 (tenant_id, user_id, action, resource, hashlib.sha256(raw.encode()).hexdigest(), now()))


def current_user() -> Optional[sqlite3.Row]:
    uid = session.get("uid")
    if not uid: return None
    conn = db(); row = conn.execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone(); conn.close(); return row


def current_tenant_id() -> Optional[int]:
    u = current_user()
    return None if not u else u["tenant_id"]


def public_user(u: sqlite3.Row) -> Dict[str, Any]:
    tenant = None
    conn = db()
    if u["tenant_id"]:
        tenant = dict(conn.execute("SELECT * FROM tenants WHERE id=?", (u["tenant_id"],)).fetchone())
    mods = []
    if u["role"] == "superadmin":
        mods = list(MODULE_CATALOG.keys())
    elif u["role"] == "admin":
        mods = [k for k,v in get_user_modules(conn, u).items() if v]
    conn.close()
    return {"id":u["id"],"tenant_id":u["tenant_id"],"tenant":tenant,"name":u["name"],"phone":u["phone"],"role":u["role"],"section":u["section"],"is_super":u["role"]=="superadmin","enabled_modules":mods}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return jsonify({"ok":False,"error":"Accesso non autorizzato"}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u=current_user()
        if not u: return jsonify({"ok":False,"error":"Accesso non autorizzato"}),401
        if u["role"] not in ("admin","superadmin"): return jsonify({"ok":False,"error":"Funzione riservata all'amministratore"}),403
        if u["role"]!="superadmin" and tenant_expired(u["tenant_id"]): return jsonify({"ok":False,"error":"Tenant scaduto o disattivato"}),402
        return fn(*args, **kwargs)
    return wrapper


def super_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u=current_user()
        if not u: return jsonify({"ok":False,"error":"Accesso non autorizzato"}),401
        if u["role"]!="superadmin": return jsonify({"ok":False,"error":"Funzione riservata al SuperAdmin"}),403
        return fn(*args, **kwargs)
    return wrapper


def tenant_expired(tid: Optional[int]) -> bool:
    if not tid: return False
    conn=db(); t=conn.execute("SELECT status,expires_at FROM tenants WHERE id=?",(tid,)).fetchone(); conn.close()
    if not t: return True
    if t["status"] != "active": return True
    if t["expires_at"]:
        try: return datetime.fromisoformat(t["expires_at"]).date() < datetime.now().date()
        except Exception: return False
    return False


def tenant_query_id() -> int:
    u=current_user()
    if not u: raise PermissionError()
    if u["role"]=="superadmin":
        tid = request.args.get("tenant_id") or request.headers.get("X-Tenant-ID") or session.get("tenant_id")
        if tid: return int(tid)
        conn=db(); row=conn.execute("SELECT id FROM tenants ORDER BY id LIMIT 1").fetchone(); conn.close(); return int(row["id"])
    return int(u["tenant_id"])


def get_tenant_settings(conn: sqlite3.Connection, tid: int) -> Dict[str, Any]:
    rows = conn.execute("SELECT key,value FROM tenant_settings WHERE tenant_id=?", (tid,)).fetchall()
    raw = {r["key"]: r["value"] for r in rows}
    return {"total_electors": int(raw.get("total_electors",0) or 0), "total_voters": int(raw.get("total_voters",0) or 0), "council_seats": int(raw.get("council_seats",24) or 24), "winner_mayor": raw.get("winner_mayor",""), "mode": raw.get("mode","first")}


def get_election_data(conn: sqlite3.Connection, tid: int) -> Dict[str, Any]:
    r=conn.execute("SELECT value FROM tenant_settings WHERE tenant_id=? AND key='election_data_json'",(tid,)).fetchone()
    return safe_json_loads(r["value"] if r else None, DEFAULT_ELECTION_DATA)


def save_election_data(conn: sqlite3.Connection, tid: int, data: Dict[str, Any]) -> None:
    conn.execute("INSERT OR REPLACE INTO tenant_settings(tenant_id,key,value) VALUES(?,?,?)", (tid,"election_data_json",json.dumps(data,ensure_ascii=False)))


def anagraphics_loaded(conn: sqlite3.Connection, tid: int) -> bool:
    data = get_election_data(conn,tid); return bool(data.get("mayors")) and bool(data.get("lists")) and any(v.get("candidates") for v in data.get("lists",{}).values())


def get_tenant_modules(conn: sqlite3.Connection, tid: int) -> Dict[str,bool]:
    rows=conn.execute("SELECT module_key,enabled,expires_at FROM tenant_modules WHERE tenant_id=?",(tid,)).fetchall()
    d={k:False for k in MODULE_CATALOG}
    today=datetime.now().date()
    for r in rows:
        exp_ok=True
        if r["expires_at"]:
            try: exp_ok = datetime.fromisoformat(r["expires_at"]).date() >= today
            except Exception: exp_ok=True
        if r["module_key"] in d: d[r["module_key"]]=bool(r["enabled"]) and exp_ok
    return d


def get_user_modules(conn: sqlite3.Connection, u: sqlite3.Row) -> Dict[str,bool]:
    if u["role"] == "superadmin": return {k: True for k in MODULE_CATALOG}
    tenant_mods = get_tenant_modules(conn, u["tenant_id"])
    rows=conn.execute("SELECT module_key,enabled FROM admin_module_permissions WHERE user_id=?",(u["id"],)).fetchall()
    if not rows: return tenant_mods
    user_mods={r["module_key"]:bool(r["enabled"]) for r in rows}
    return {k: bool(tenant_mods.get(k)) and bool(user_mods.get(k,False)) for k in MODULE_CATALOG}


def module_required(key: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u=current_user()
            if not u: return jsonify({"ok":False,"error":"Accesso non autorizzato"}),401
            if u["role"]!="superadmin":
                conn=db(); allowed=get_user_modules(conn,u).get(key,False); conn.close()
                if not allowed: return jsonify({"ok":False,"error":f"Modulo {key} non abilitato per questo tenant/admin"}),403
            return fn(*args, **kwargs)
        return wrapper
    return deco


def api_auth(scopes_required: str = "read"):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth=request.headers.get("Authorization","")
            if not auth.startswith("Bearer "): return jsonify({"ok":False,"error":"API key mancante"}),401
            raw=auth.split(" ",1)[1].strip(); h=hash_api_key(raw)
            conn=db(); row=conn.execute("SELECT * FROM api_keys WHERE key_hash=? AND active=1",(h,)).fetchone()
            if not row: conn.close(); return jsonify({"ok":False,"error":"API key non valida"}),401
            scopes=set((row["scopes"] or "read").split(","))
            if scopes_required not in scopes and "admin" not in scopes: conn.close(); return jsonify({"ok":False,"error":"Scope API insufficiente"}),403
            conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?",(now(),row["id"])); conn.commit(); conn.close()
            request.tenant_id=int(row["tenant_id"]); request.api_key_id=int(row["id"])
            return fn(*args, **kwargs)
        return wrapper
    return deco

# Pagine statiche
@app.route("/")
def login_page():
    u=current_user()
    if u: return redirect("/super" if u["role"]=="superadmin" else ("/admin" if u["role"]=="admin" else "/app"))
    return send_from_directory(STATIC_DIR,"login.html")
@app.route("/app")
def app_page(): return send_from_directory(STATIC_DIR,"index.html") if current_user() else redirect("/")
@app.route("/super")
def super_page():
    u=current_user(); return send_from_directory(STATIC_DIR,"super.html") if u and u["role"]=="superadmin" else redirect("/")
@app.route("/admin")
def admin_page(): return send_from_directory(STATIC_DIR,"admin.html") if current_user() else redirect("/")
for route, fn in [("/admin/charts","admin_charts.html"),("/admin/imports","admin_imports.html"),("/admin/users","admin_users.html"),("/admin/tools","admin_tools.html"),("/admin/modules","admin_modules.html"),("/admin/blockchain","admin_blockchain.html"),("/admin/osint","admin_osint.html"),("/admin/simulator","admin_simulator.html"),("/admin/intelligence","admin_intelligence.html"),("/admin/social","admin_social.html"),("/public-dashboard","public_dashboard.html")]:
    app.add_url_rule(route, route.replace('/','_'), lambda fn=fn: send_from_directory(STATIC_DIR, fn))

# Auth
@app.post("/api/login")
def login():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip(); pin=str(data.get("pin","")).strip(); token=str(data.get("token","")).strip()
    conn=db(); u=None
    if token: u=conn.execute("SELECT * FROM users WHERE qr_token=? AND active=1",(token,)).fetchone()
    elif phone and pin:
        u=conn.execute("SELECT * FROM users WHERE phone=? AND active=1",(phone,)).fetchone()
        if u and not check_password_hash(u["pin_hash"],pin): u=None
    if u and u["role"]!="superadmin" and tenant_expired(u["tenant_id"]): conn.close(); return jsonify({"ok":False,"error":"Organizzazione scaduta o disattivata"}),402
    conn.close()
    if not u: return jsonify({"ok":False,"error":"Credenziali non valide"}),401
    session["uid"]=u["id"]; session["tenant_id"]=u["tenant_id"]
    return jsonify({"ok":True,"user":public_user(u)})
@app.post("/api/logout")
def logout(): session.clear(); return jsonify({"ok":True})
@app.get("/logout")
def logout_get(): session.clear(); return redirect("/")
@app.get("/api/me")
@login_required
def me(): return jsonify({"ok":True,"user":public_user(current_user())})

# Tenant-aware operational APIs
@app.get("/api/config")
@login_required
def config():
    tid=tenant_query_id(); conn=db(); data=get_election_data(conn,tid); settings=get_tenant_settings(conn,tid); conn.close()
    loaded=bool(data.get("mayors")) and bool(data.get("lists"))
    return jsonify({"ok":True,"tenant_id":tid,"data":data,"all_data":data,"settings":settings,"anagraphics":{"loaded":loaded,"message":"Caricare anagrafiche per questo tenant"}})

@app.get("/api/election-data")
@admin_required
def get_election_data_api():
    tid=tenant_query_id(); conn=db(); data=get_election_data(conn,tid); conn.close(); return jsonify({"ok":True,"tenant_id":tid,"data":data})
@app.post("/api/election-data")
@admin_required
def save_election_data_api():
    tid=tenant_query_id(); data=request.get_json(force=True).get("data")
    if not isinstance(data,dict) or not isinstance(data.get("mayors"),list) or not isinstance(data.get("lists"),dict): return jsonify({"ok":False,"error":"Formato non valido"}),400
    conn=db(); save_election_data(conn,tid,data); audit(conn,tid,current_user()["id"],"save_election_data","tenant_settings",data); conn.commit(); conn.close(); return jsonify({"ok":True,"message":"Anagrafiche tenant aggiornate"})

@app.post("/api/settings")
@admin_required
def settings_api():
    tid=tenant_query_id(); data=request.get_json(force=True); allowed={"total_electors","total_voters","council_seats","winner_mayor","mode"}
    conn=db()
    for k in allowed:
        if k in data: conn.execute("INSERT OR REPLACE INTO tenant_settings(tenant_id,key,value) VALUES(?,?,?)",(tid,k,str(data[k])))
    audit(conn,tid,current_user()["id"],"update_settings","tenant_settings",data); conn.commit(); s=get_tenant_settings(conn,tid); conn.close(); return jsonify({"ok":True,"settings":s})

@app.get("/api/my-report")
@login_required
def my_report():
    u=current_user(); tid=tenant_query_id(); section=(request.args.get("section") or u["section"] or "").strip()
    if not section: return jsonify({"ok":True,"exists":False})
    if u["role"] not in ("admin","superadmin") and u["section"] and section!=u["section"]: return jsonify({"ok":False,"error":"Sezione non autorizzata"}),403
    conn=db(); rep=conn.execute("SELECT * FROM reports WHERE tenant_id=? AND section=?",(tid,section)).fetchone()
    if not rep: conn.close(); return jsonify({"ok":True,"exists":False,"section":section})
    rows=conn.execute("SELECT * FROM votes WHERE tenant_id=? AND report_id=?",(tid,rep["id"])).fetchall(); conn.close()
    mayors={}; list_votes={}; prefs={}
    for r in rows:
        if r["vote_type"]=="sindaco": mayors[r["name"]]=r["votes"]
        elif r["vote_type"]=="lista": list_votes[r["list_name"]]=r["votes"]
        elif r["vote_type"]=="preferenza": prefs.setdefault(r["list_name"],{})[r["name"]]=r["votes"]
    return jsonify({"ok":True,"exists":True,"section":section,"voters":rep["voters"],"blank_ballots":rep["blank_ballots"],"null_ballots":rep["null_ballots"],"contested_ballots":rep["contested_ballots"],"section_electors":rep["contested_ballots"],"split_votes":safe_json_loads(rep["split_votes_json"],[]),"closed":bool(rep["closed"]),"closed_at":rep["closed_at"],"mayors":mayors,"list_votes":list_votes,"preferences":prefs,"updated_at":rep["updated_at"]})


def _save_report_payload(tid:int, user_id:int, data:Dict[str,Any], close:bool=False) -> Tuple[bool,Dict[str,Any],int]:
    section=str(data.get("section","")).strip(); voters=int(data.get("voters",0) or 0); blank=int(data.get("blank_ballots",0) or 0); null=int(data.get("null_ballots",0) or 0); contested=int(data.get("section_electors", data.get("contested_ballots",0)) or 0)
    if not section: return False,{"ok":False,"error":"Inserire sezione"},400
    conn=db(); ed=get_election_data(conn,tid)
    if not anagraphics_loaded(conn,tid): conn.close(); return False,{"ok":False,"error":"Caricare prima anagrafiche del tenant"},400
    mayor_votes=data.get("mayors",{}); list_votes=data.get("list_votes",{}); prefs=data.get("preferences",{}); split=safe_json_loads(data.get("split_votes",[]),[])
    valid=max(sum(int(v or 0) for v in mayor_votes.values()), sum(int(v or 0) for v in list_votes.values()))
    if close and voters != valid+blank+null:
        conn.close(); return False,{"ok":False,"error":f"Quadratura non valida: votanti={voters}, valido+bianche+nulle={valid+blank+null}"},400
    existing=conn.execute("SELECT id,closed FROM reports WHERE tenant_id=? AND section=?",(tid,section)).fetchone(); n=now()
    if existing:
        rid=existing["id"]; conn.execute("UPDATE reports SET user_id=?,voters=?,blank_ballots=?,null_ballots=?,contested_ballots=?,split_votes_json=?,closed=?,closed_at=?,updated_at=? WHERE tenant_id=? AND id=?",(user_id,voters,blank,null,contested,json.dumps(split,ensure_ascii=False),1 if close else existing["closed"],n if close else existing["closed_at"],n,tid,rid)); conn.execute("DELETE FROM votes WHERE tenant_id=? AND report_id=?",(tid,rid))
    else:
        conn.execute("INSERT INTO reports(tenant_id,user_id,section,voters,blank_ballots,null_ballots,contested_ballots,split_votes_json,closed,closed_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(tid,user_id,section,voters,blank,null,contested,json.dumps(split,ensure_ascii=False),1 if close else 0,n if close else None,n,n)); rid=conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    for name in ed.get("mayors",[]): conn.execute("INSERT INTO votes(tenant_id,report_id,vote_type,list_name,name,votes) VALUES(?,?,?,?,?,?)",(tid,rid,"sindaco",None,name,int(mayor_votes.get(name,0) or 0)))
    for lname,lobj in ed.get("lists",{}).items():
        conn.execute("INSERT INTO votes(tenant_id,report_id,vote_type,list_name,name,votes) VALUES(?,?,?,?,?,?)",(tid,rid,"lista",lname,lname,int(list_votes.get(lname,0) or 0)))
        for cand in lobj.get("candidates",[]): conn.execute("INSERT INTO votes(tenant_id,report_id,vote_type,list_name,name,votes) VALUES(?,?,?,?,?,?)",(tid,rid,"preferenza",lname,cand,int(prefs.get(lname,{}).get(cand,0) or 0)))
    audit(conn,tid,user_id,"close_report" if close else "save_report","reports",{"section":section}); conn.commit(); conn.close(); return True,{"ok":True,"message":"Seggio chiuso" if close else "Dati salvati"},200

@app.post("/api/report")
@login_required
def save_report():
    u=current_user(); tid=tenant_query_id(); data=request.get_json(force=True)
    if u["role"] not in ("admin","superadmin") and u["section"] and str(data.get("section","")).strip()!=u["section"]: return jsonify({"ok":False,"error":"Sezione non autorizzata"}),403
    ok,p,code=_save_report_payload(tid,u["id"],data,False); return jsonify(p),code
@app.post("/api/close-seat")
@login_required
def close_seat():
    u=current_user(); tid=tenant_query_id(); data=request.get_json(force=True)
    if u["role"]=="admin": return jsonify({"ok":False,"error":"La chiusura seggio è riservata al rappresentante"}),403
    ok,p,code=_save_report_payload(tid,u["id"],data,True); return jsonify(p),code
@app.get("/api/section-status")
@login_required
def section_status():
    tid=tenant_query_id(); section=request.args.get("section","").strip(); conn=db(); r=conn.execute("SELECT closed,closed_at FROM reports WHERE tenant_id=? AND section=?",(tid,section)).fetchone(); conn.close(); return jsonify({"ok":True,"section":section,"closed":bool(r["closed"]) if r else False,"closed_at":r["closed_at"] if r else None})

@app.get("/api/users")
@admin_required
def users_api():
    u=current_user(); tid=tenant_query_id(); conn=db();
    if u["role"]=="superadmin": rows=conn.execute("SELECT id,tenant_id,name,phone,role,section,allowed_lists,qr_token,active FROM users ORDER BY tenant_id,id").fetchall()
    else: rows=conn.execute("SELECT id,tenant_id,name,phone,role,section,allowed_lists,qr_token,active FROM users WHERE tenant_id=? ORDER BY id",(tid,)).fetchall()
    ed=get_election_data(conn,tid); conn.close(); return jsonify({"ok":True,"users":[dict(r) for r in rows],"lists":sorted(ed.get("lists",{}).keys())})
@app.post("/api/users")
@admin_required
def create_user_api():
    tid=tenant_query_id(); data=request.get_json(force=True); name=str(data.get("name","")).strip(); phone=str(data.get("phone","")).strip(); pin=str(data.get("pin","")).strip(); role=str(data.get("role","rappresentante")).strip(); section=str(data.get("section","")).strip() or None
    if role=="superadmin": return jsonify({"ok":False,"error":"Non puoi creare SuperAdmin da qui"}),403
    if not name or not phone or not pin: return jsonify({"ok":False,"error":"Nome, codice/telefono e PIN obbligatori"}),400
    allowed="|".join(data.get("allowed_lists",[]) if isinstance(data.get("allowed_lists",[]),list) else [])
    conn=db(); conn.execute("INSERT INTO users(tenant_id,name,phone,pin_hash,qr_token,role,section,allowed_lists,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",(tid,name,phone,generate_password_hash(pin),secrets.token_urlsafe(24),role,section,allowed,now())); audit(conn,tid,current_user()["id"],"create_user","users",data); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.post("/api/reset-votes")
@admin_required
def reset_votes():
    tid=tenant_query_id(); confirm=str(request.get_json(force=True).get("confirm","")).strip()
    if confirm!="AZZERA": return jsonify({"ok":False,"error":"Scrivere AZZERA"}),400
    conn=db(); conn.execute("DELETE FROM votes WHERE tenant_id=?",(tid,)); conn.execute("DELETE FROM reports WHERE tenant_id=?",(tid,)); audit(conn,tid,current_user()["id"],"reset_votes","reports"); conn.commit(); conn.close(); return jsonify({"ok":True,"message":"Voti del tenant azzerati"})

# AI / BI

def _aggregate(conn: sqlite3.Connection, tid:int) -> Dict[str,Any]:
    ed=get_election_data(conn,tid); settings=get_tenant_settings(conn,tid)
    reps=conn.execute("SELECT * FROM reports WHERE tenant_id=? ORDER BY CAST(section AS INTEGER), section",(tid,)).fetchall()
    rows=conn.execute("SELECT v.*, r.section, r.voters, r.closed FROM votes v JOIN reports r ON r.id=v.report_id WHERE v.tenant_id=?",(tid,)).fetchall()
    list_tot={}; mayor_tot={}; pref_tot={}; sections={}
    for r in reps: sections[r["section"]]={"section":r["section"],"voters":r["voters"],"closed":bool(r["closed"]),"valid_lists":0,"valid_mayors":0,"blank":r["blank_ballots"],"null":r["null_ballots"]}
    for v in rows:
        sec=v["section"]; votes=int(v["votes"] or 0)
        if v["vote_type"]=="lista": list_tot[v["list_name"]]=list_tot.get(v["list_name"],0)+votes; sections.setdefault(sec,{"section":sec,"voters":v["voters"],"closed":bool(v["closed"]),"valid_lists":0,"valid_mayors":0})["valid_lists"]+=votes
        elif v["vote_type"]=="sindaco": mayor_tot[v["name"]]=mayor_tot.get(v["name"],0)+votes; sections.setdefault(sec,{"section":sec,"voters":v["voters"],"closed":bool(v["closed"]),"valid_lists":0,"valid_mayors":0})["valid_mayors"]+=votes
        elif v["vote_type"]=="preferenza": pref_tot[(v["list_name"],v["name"])]=pref_tot.get((v["list_name"],v["name"]),0)+votes
    return {"election_data":ed,"settings":settings,"reports":[dict(r) for r in reps],"sections":list(sections.values()),"list_totals":list_tot,"mayor_totals":mayor_tot,"pref_totals":pref_tot}


def ai_payload(conn: sqlite3.Connection, tid:int) -> Dict[str,Any]:
    ag=_aggregate(conn,tid); sections=ag["sections"]; total_voters=sum(s.get("voters",0) for s in sections); total_lists=sum(ag["list_totals"].values()); total_mayors=sum(ag["mayor_totals"].values())
    heat=[]
    for s in sections:
        voters=s.get("voters",0); invalid=s.get("blank",0)+s.get("null",0); valid=s.get("valid_lists",0) or s.get("valid_mayors",0)
        heat.append({**s,"valid_votes":valid,"invalid_rate_pct":round(invalid/voters*100,2) if voters else 0,"turnout_on_observed_pct":round(voters/total_voters*100,2) if total_voters else 0})
    # Bayesian/Laplace projection
    target=ag["settings"].get("total_voters") or max(total_voters,total_lists,total_mayors)
    missing=max(0,target-total_lists)
    k=max(1,len(ag["list_totals"]))
    bayes_lists=[]
    for name,val in ag["list_totals"].items():
        p=(val+1)/(total_lists+k) if total_lists+k else 0
        bayes_lists.append({"name":name,"current":val,"probability_pct":round(p*100,2),"projected":round(val+missing*p),"method":"Laplace/Bayes multinomiale"})
    bayes_lists.sort(key=lambda x:x["projected"], reverse=True)
    # ML turnout regression over section index
    ml={"available":SKLEARN_AVAILABLE,"turnout_regression":[],"winner_prediction":None,"clusters":[],"anomalies":[]}
    if sections:
        xs=[]; y=[]
        for i,s in enumerate(sections,1):
            try: idx=float(str(s["section"]).replace("bis",".5"))
            except Exception: idx=float(i)
            xs.append([idx, 1 if s.get("closed") else 0, s.get("valid_lists",0)]); y.append(float(s.get("voters",0)))
        if SKLEARN_AVAILABLE and len(xs)>=2:
            X=np.array(xs); Y=np.array(y); model=LinearRegression().fit(X,Y)
            for i,s in enumerate(sections,1):
                pred=max(0,float(model.predict(np.array([xs[i-1]]))[0])); ml["turnout_regression"].append({"section":s["section"],"actual_voters":s.get("voters",0),"predicted_voters":round(pred,1),"residual":round(s.get("voters",0)-pred,1)})
            if len(sections)>=3:
                features=np.array([[s.get("voters",0),s.get("valid_lists",0),s.get("invalid_rate_pct",0)] for s in heat])
                n=min(3,len(sections)); labels=KMeans(n_clusters=n, n_init=10, random_state=7).fit_predict(features)
                for lab,s in zip(labels,heat): ml["clusters"].append({"section":s["section"],"cluster":int(lab),"profile":"alta intensità" if s.get("voters",0)> (total_voters/len(sections) if sections else 0) else "bassa/media intensità"})
        avg_invalid=sum(h["invalid_rate_pct"] for h in heat)/len(heat) if heat else 0
        for h in heat:
            if h["invalid_rate_pct"] > avg_invalid+8 or (total_voters and h.get("voters",0)>2*(total_voters/len(heat))):
                ml["anomalies"].append({"section":h["section"],"reason":"scostamento statistico su invalidità/affluenza", "invalid_rate_pct":h["invalid_rate_pct"], "voters":h.get("voters",0)})
    if bayes_lists: ml["winner_prediction"]={"leader":bayes_lists[0]["name"],"projected_votes":bayes_lists[0]["projected"],"confidence":"media" if len(sections)>=5 else "bassa: poche sezioni caricate"}
    # political weight
    political=[]
    for (lname,cand),votes in ag["pref_totals"].items():
        ltot=ag["list_totals"].get(lname,0); score=min(100, round((votes/(ltot or 1))*55 + math.log1p(votes)*9,2))
        political.append({"candidate":cand,"list":lname,"preferences":votes,"list_total":ltot,"preference_on_list_pct":round(votes/(ltot or 1)*100,2),"body_index":score})
    political.sort(key=lambda x:(-x["body_index"],-x["preferences"]))
    return {"ok":True,"tenant_id":tid,"summary":{"sections_loaded":len(sections),"sections_closed":sum(1 for s in sections if s.get("closed")),"observed_voters":total_voters,"total_list_votes":total_lists,"total_mayor_votes":total_mayors,"sklearn_available":SKLEARN_AVAILABLE},"heatmap":heat,"prediction":{"lists":bayes_lists,"method":"proiezione Bayes/Laplace con target votanti configurato; non è un sondaggio"},"machine_learning":ml,"political_weight":political,"social_cards":[{"rank":i+1,**p,"political_score":p["body_index"],"share_text":f"{p['candidate']} · {p['list']} · Political Score {p['body_index']}/100"} for i,p in enumerate(political[:50])],"data":ag["election_data"]}

@app.get("/api/intelligence")
@admin_required
@module_required("intelligence")
def intelligence():
    tid=tenant_query_id(); conn=db(); p=ai_payload(conn,tid); conn.close(); return jsonify(p)
@app.get("/api/public-dashboard")
def public_dash():
    tid=int(request.args.get("tenant_id") or 1); conn=db(); p=ai_payload(conn,tid); conn.close(); return jsonify({"ok":True,"tenant_id":tid,"summary":p["summary"],"heatmap":p["heatmap"],"prediction":p["prediction"],"social_cards":p["social_cards"][:30]})
@app.get("/api/ai/predictive")
@admin_required
@module_required("intelligence")
def ai_predictive():
    tid=tenant_query_id(); conn=db(); p=ai_payload(conn,tid); conn.close(); return jsonify({"ok":True,"tenant_id":tid,"prediction":p["prediction"],"machine_learning":p["machine_learning"]})

# SuperAdmin SaaS
@app.get("/api/super/overview")
@super_required
def super_overview():
    conn=db(); tenants=[dict(r) for r in conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()]; users=[dict(r) for r in conn.execute("SELECT id,tenant_id,name,phone,role,section,active FROM users ORDER BY tenant_id,id").fetchall()]; payments=[dict(r) for r in conn.execute("SELECT * FROM payment_methods ORDER BY id DESC").fetchall()]
    profiles={str(r["user_id"]):dict(r) for r in conn.execute("SELECT * FROM admin_profiles").fetchall()}
    permissions={}
    for u in users:
        if u["role"]=="admin":
            fake=conn.execute("SELECT * FROM users WHERE id=?",(u["id"],)).fetchone(); permissions[str(u["id"])] = get_user_modules(conn,fake)
    modules=[]
    for k,v in MODULE_CATALOG.items(): modules.append({"key":k,**v,"enabled":True})
    conn.close(); return jsonify({"ok":True,"tenants":tenants,"modules":modules,"users":users,"profiles":profiles,"payments":payments,"permissions":permissions})

@app.post("/api/super/tenants")
@super_required
def create_tenant():
    data=request.get_json(force=True); name=str(data.get("name") or data.get("organization") or "Nuova organizzazione").strip(); slug=slugify(data.get("slug") or name); exp=data.get("expires_at") or (datetime.now()+timedelta(days=90)).date().isoformat()
    conn=db(); conn.execute("INSERT INTO tenants(name,slug,organization_type,place,cap,province,region,plan,status,expires_at,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(name,slug,data.get("organization_type","organizzazione politica"),data.get("place"),data.get("cap"),data.get("province"),data.get("region"),data.get("plan","trial"),data.get("status","active"),exp,data.get("notes"),now(),now()))
    tid=conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    for k,en in DEFAULT_MODULES.items(): conn.execute("INSERT INTO tenant_modules(tenant_id,module_key,enabled,updated_at) VALUES(?,?,?,?)",(tid,k,int(en),now()))
    for k,v in {"total_electors":"0","total_voters":"0","council_seats":"24","winner_mayor":"","mode":"first","election_data_json":json.dumps(DEFAULT_ELECTION_DATA,ensure_ascii=False)}.items(): conn.execute("INSERT INTO tenant_settings(tenant_id,key,value) VALUES(?,?,?)",(tid,k,v))
    audit(conn,tid,current_user()["id"],"create_tenant","tenants",data); conn.commit(); conn.close(); return jsonify({"ok":True,"tenant_id":tid,"slug":slug})

@app.post("/api/super/admins")
@super_required
def create_admin_super():
    data=request.get_json(force=True); tenant_id=data.get("tenant_id")
    if not tenant_id:
        # crea tenant automaticamente dai dati commerciali, stile Focus360AI
        res_data={"name":data.get("organization") or data.get("name") or "Organizzazione politica", "place":data.get("place"),"cap":data.get("cap"),"province":data.get("province"),"region":data.get("region"),"plan":data.get("plan","trial")}
        conn=db(); slug=slugify(res_data["name"]); conn.execute("INSERT INTO tenants(name,slug,place,cap,province,region,plan,status,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(res_data["name"],slug,res_data.get("place"),res_data.get("cap"),res_data.get("province"),res_data.get("region"),res_data.get("plan"),"active",(datetime.now()+timedelta(days=90)).date().isoformat(),now(),now())); tenant_id=conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        for k,en in DEFAULT_MODULES.items(): conn.execute("INSERT INTO tenant_modules(tenant_id,module_key,enabled,updated_at) VALUES(?,?,?,?)",(tenant_id,k,int(en),now()))
        for k,v in {"total_electors":"0","total_voters":"0","council_seats":"24","winner_mayor":"","mode":"first","election_data_json":json.dumps(DEFAULT_ELECTION_DATA,ensure_ascii=False)}.items(): conn.execute("INSERT INTO tenant_settings(tenant_id,key,value) VALUES(?,?,?)",(tenant_id,k,v))
    else: conn=db()
    name=str(data.get("name","")).strip(); phone=str(data.get("phone","")).strip(); pin=str(data.get("pin","")).strip()
    if not name or not phone or not pin: conn.close(); return jsonify({"ok":False,"error":"Nome, codice e PIN obbligatori"}),400
    conn.execute("INSERT INTO users(tenant_id,name,phone,pin_hash,qr_token,role,section,allowed_lists,active,created_at) VALUES(?,?,?,?,?,?,?, ?,1,?)",(tenant_id,name,phone,generate_password_hash(pin),secrets.token_urlsafe(24),"admin",None,"",now()))
    uid=conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.execute("INSERT OR REPLACE INTO admin_profiles(user_id,organization,place,cap,province,region,usage_reason,beneficiaries,notes,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(uid,data.get("organization"),data.get("place"),data.get("cap"),data.get("province"),data.get("region"),data.get("usage_reason"),data.get("beneficiaries"),data.get("notes"),now()))
    mods=data.get("modules") or DEFAULT_MODULES
    for k in MODULE_CATALOG: conn.execute("INSERT OR REPLACE INTO admin_module_permissions(user_id,module_key,enabled,updated_at) VALUES(?,?,?,?)",(uid,k,int(bool(mods.get(k,False))),now()))
    audit(conn,tenant_id,current_user()["id"],"create_admin","users",data); conn.commit(); conn.close(); return jsonify({"ok":True,"user_id":uid,"tenant_id":tenant_id})

@app.post("/api/super/admins/<int:user_id>/modules")
@super_required
def admin_modules_super(user_id:int):
    mods=request.get_json(force=True).get("modules",{}); conn=db()
    for k in MODULE_CATALOG: conn.execute("INSERT OR REPLACE INTO admin_module_permissions(user_id,module_key,enabled,updated_at) VALUES(?,?,?,?)",(user_id,k,int(bool(mods.get(k,False))),now()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.post("/api/modules")
@super_required
def global_modules_compat(): return jsonify({"ok":True,"message":"In modalità multitenant i moduli si gestiscono per tenant/admin"})
@app.post("/api/super/payments")
@super_required
def payments():
    d=request.get_json(force=True); conn=db(); conn.execute("INSERT INTO payment_methods(provider,enabled,mode,public_key,webhook_url,notes,updated_at) VALUES(?,?,?,?,?,?,?)",(d.get("provider"),int(bool(d.get("enabled"))),d.get("mode","test"),d.get("public_key"),d.get("webhook_url"),d.get("notes"),now())); conn.commit(); conn.close(); return jsonify({"ok":True})
@app.get("/api/super/payment-providers")
@super_required
def providers():
    return jsonify({"ok":True,"providers":[{"provider":"Stripe","api":"Checkout + Webhook","env":["STRIPE_PUBLIC_KEY","STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET"],"use":"abbonamenti mensili/annuali"},{"provider":"PayPal","api":"Orders/Subscriptions","env":["PAYPAL_CLIENT_ID","PAYPAL_SECRET"],"use":"pagamento piano o moduli"},{"provider":"PagoPA","api":"integrazione PSP","env":["PAGOPA_API_KEY"],"use":"enti/associazioni strutturate"}]})

@app.post("/api/super/api-keys")
@super_required
def create_api_key():
    d=request.get_json(force=True); tid=int(d.get("tenant_id")); raw="fp_"+secrets.token_urlsafe(32); prefix=raw[:10]
    conn=db(); conn.execute("INSERT INTO api_keys(tenant_id,name,key_hash,prefix,scopes,active,created_at) VALUES(?,?,?,?,?,?,?)",(tid,d.get("name","API Key"),hash_api_key(raw),prefix,d.get("scopes","read"),1,now())); conn.commit(); conn.close(); return jsonify({"ok":True,"api_key":raw,"prefix":prefix,"warning":"Salvare ora la chiave: non sarà più mostrata."})

# Public API v1
@app.get("/api/v1/tenant")
@api_auth("read")
def api_tenant():
    conn=db(); t=dict(conn.execute("SELECT * FROM tenants WHERE id=?",(request.tenant_id,)).fetchone()); conn.close(); return jsonify({"ok":True,"tenant":t})
@app.get("/api/v1/results")
@api_auth("read")
def api_results():
    conn=db(); p=ai_payload(conn,request.tenant_id); conn.close(); return jsonify({"ok":True,"tenant_id":request.tenant_id,"summary":p["summary"],"prediction":p["prediction"],"heatmap":p["heatmap"]})
@app.get("/api/v1/ai/predictions")
@api_auth("read")
def api_ai():
    conn=db(); p=ai_payload(conn,request.tenant_id); conn.close(); return jsonify({"ok":True,"prediction":p["prediction"],"machine_learning":p["machine_learning"],"political_weight":p["political_weight"][:100]})
@app.post("/api/v1/reports")
@api_auth("write")
def api_write_report():
    ok,p,code=_save_report_payload(request.tenant_id, None, request.get_json(force=True), False); return jsonify(p),code

# Compat modules APIs
@app.get("/api/blockchain")
@admin_required
@module_required("blockchain")
def blockchain_api():
    tid=tenant_query_id(); conn=db(); rows=conn.execute("SELECT * FROM audit_log WHERE tenant_id=? ORDER BY id DESC LIMIT 100",(tid,)).fetchall(); chain=[]; prev="0"
    for r in reversed(rows):
        block_hash=hashlib.sha256(f"{prev}|{r['id']}|{r['payload_hash']}|{r['created_at']}".encode()).hexdigest(); chain.append({"id":r["id"],"action":r["action"],"resource":r["resource"],"created_at":r["created_at"],"prev_hash":prev,"hash":block_hash}); prev=block_hash
    conn.close(); return jsonify({"ok":True,"tenant_id":tid,"chain":chain,"note":"Hash chain tenant-aware per audit interno"})
@app.get("/api/osint")
@admin_required
@module_required("osint")
def osint_api(): return jsonify({"ok":True,"signals":[],"message":"Modulo predisposto: inserire fonti OSINT pubbliche e policy privacy prima del crawling automatico."})
@app.get("/api/simulator")
@admin_required
@module_required("simulator")
def simulator_api():
    tid=tenant_query_id(); swing=float(request.args.get("swing",0) or 0); conn=db(); p=ai_payload(conn,tid); conn.close(); lists=[]
    for x in p["prediction"]["lists"]: lists.append({**x,"scenario_projected":round(x["projected"]*(1+swing/100))})
    return jsonify({"ok":True,"swing_pct":swing,"lists":lists})

if __name__ == "__main__":
    init_db(); app.run(debug=True)
