import unicodedata
import csv
import re
import io
import json

from flask import Flask, request, jsonify, send_from_directory, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3, os, secrets, math

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.sqlite")
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.environ.get("APP_SECRET_KEY", secrets.token_hex(32))

ELECTION_DATA = {
  "mayors": [
    "NICOLA BARBERA",
    "DAVID BONGIOVANNI",
    "MELANGELA SCOLARO"
  ],
  "lists": {
    "CITTA' APERTA - CONTROCORRENTE": {
      "coalition": "DAVID BONGIOVANNI",
      "candidates": [
        "BEN R'HOUMA MONIA",
        "CAMPO RAFFAELLA",
        "CENTINEO PIETRO",
        "CHIOFALO GAETANO",
        "CICERO ANTONINO",
        "CRINÒ PIETRO",
        "GATTIGNOLO ELISA",
        "GIGLIO ANTONIO MARIO",
        "MAIO ANTONINO",
        "MAMÌ ANTONIO DARIO",
        "MATERIA CLAUDIO",
        "MIRABILE KATIA",
        "NASELLI DOMENICA ADELE DETTA MIMMA",
        "PARATORE SEBASTIANO GIUSEPPE MARCO",
        "POMA ELENA ALBERTINA",
        "PULIAFITO SALVATORE GIOVANNI",
        "PUTZU GIOVANNA",
        "RIVILLI NOELIA JACQUELINE",
        "SALERNI ANGELO",
        "SIDOTI GABRIELE",
        "SIRACUSA CARMELA",
        "TORRE GIOVANNA",
        "VALENTI MARIA CARMEN",
        "YAHIAOUI AYOUB"
      ]
    },
    "MOVIMENTO 5STELLE": {
      "coalition": "DAVID BONGIOVANNI",
      "candidates": [
        "ARRIGO ANTONINO",
        "CAMBRIA ANGELINO DETTO LINUCCIO",
        "CIMINELLI ERIKA",
        "COPPOLINO MARIA PIA",
        "CORRADO FABRIZIO",
        "DONNINA GIOVANNI",
        "EL HESSANIA ABDELKRIM DETTO KARIM",
        "GENOVESE BIAGIO",
        "GIGLIO RUGGERO DETTO RUGGERO",
        "GIORGIANNI VERA DETTA VERA",
        "GIUNTA ANTONINO",
        "GIUNTA GABRIELLA",
        "INFANTINO MARCO",
        "MAZZEO ANGELO",
        "MIRABILE ALESSANDRA ROSARIA",
        "PRESTI STEFANIA",
        "RECUPERO GAETANO",
        "TURRISI GIUSEPPE DETTO GEPI"
      ]
    },
    "PARTITO DEMOCRATICO": {
      "coalition": "DAVID BONGIOVANNI",
      "candidates": [
        "BONGIOVANNI DAVID",
        "CALAMUNERI ORAZIO",
        "CERAOLO CARMELO MICHELE",
        "CUCUMO STEFANIA",
        "DI PASQUALE FRANCESCO DETTO FRANCO",
        "EPIFANIO STEFANIA",
        "FLORAMO DOMENICA DETTA DOMINGA",
        "FRANCHINA LOREDANA",
        "GAROFALO MARIO",
        "GITTO LORENZO",
        "IMBESI GIANLUCA",
        "IMMESI ILENIA DETTA ILENIA",
        "LEMBO GIUSY DETTA GIUSI",
        "MANCUSO FELICE",
        "MOSTACCIO DOMENICA",
        "NICHITELLEA NICOLETA MARIANA DETTA NICOLETTA",
        "SAIJA STEFANO ANTONIO",
        "SANTANOCITA FRANCESCA",
        "SPINELLA PAOLO",
        "TORRE ROSARIA DETTA SARA",
        "TUJIRI KHADIJA DETTA GIGIA",
        "TURRISI ANTONIO",
        "VAZZA MILENA",
        "ZANGLA ANGELA"
      ]
    },
    "DE LUCA SINDACO DI SICILIA": {
      "coalition": "MELANGELA SCOLARO",
      "candidates": [
        "DOMINGA ACCETTA",
        "SEBASTIANO BORGHESE",
        "ANGELA MARIA CALATOZZO",
        "CLAUDIA CAPPELLANO",
        "PRANVERA CECAJ",
        "GIUSEPPE CRISAFULLI",
        "LUCA CUCINOTTA",
        "NUNZIATA GRAZIELLA D’AMICO DETTA D’AMICO NANCY",
        "CLAUDIO FEBO",
        "SIMONA GITTO",
        "VANESSA LO MONACO",
        "FRANCESCA LUCIA MANDANICI DETTA FRANCESCA MANDANICI",
        "CLARISSA MARCINI",
        "ANNALISA MUNAFÒ",
        "CELESTINA NANIA",
        "PAOLO PINO",
        "GIUSEPPE PULIAFITO DETTO RUBENS",
        "FEDERICO SCARPACI",
        "SERGIO VITO SCOLARO DETTO SERGIO SCOLARO",
        "GIULIA MARIA SIDOTI DETTA GIULIA",
        "FABIANA SIMONETTA",
        "ANTONIO SOFIA",
        "RITA SPICCIA",
        "NICOLA TORRE"
      ]
    },
    "AVREMO CURA DI TE": {
      "coalition": "MELANGELA SCOLARO",
      "candidates": [
        "GRAZIANO ANGELO ACCETTA DETTO GRAZIANO",
        "MARIADRIANA ALOISI",
        "CRISTIAN BAMBACI",
        "GIAN FRANCO BRIGANDÌ",
        "EMANUELA BUCCA",
        "CARMELO BUCCA",
        "SANTA CALIRI",
        "SALVATORE CALLISTO",
        "BARBARA CAVALLARO",
        "SERENA MARIA CONSOLI",
        "SEBASTIANO CORICA",
        "VINCENZO FOTI",
        "GIUSEPPE ISGRÒ",
        "GIUSEPPE LAQUIDARA DETTO GIUSEPPE LAGUIDARA DETTO GIUSEPPE LA GUIDARA",
        "EMANUELE MUNAFÒ",
        "ROSARIO CARMELO NATALE DETTO ROSARIO NATALE",
        "VALENTINA GIUSY PANTÈ",
        "MAURIZIO PIZZUTO",
        "GISELLA PUDDU",
        "GABRIELE SPINA"
      ]
    },
    "SCOLARO SINDACO": {
      "coalition": "MELANGELA SCOLARO",
      "candidates": [
        "NIEVIS MARIA ACCETTA DETTA NIVES ACCETTA",
        "CONCETTA ALOSI DETTA CETTY ALOSI",
        "ANASTASI MARCO DETTO MARCO NASTASI",
        "FORTUNATO BARBARO",
        "SARA ASSUNTA AGOSTINA BASILICÒ DETTA SARA BASILICÒ",
        "GIOVANNI BENENATI",
        "VINCENZA BRIGANDÌ",
        "FILIPPO CASTELLANO",
        "ORAZIO CICCIARI",
        "TINDARO DI PASQUALE",
        "COSTANZA GALLO",
        "LUANA CARMEN MACCARI DETTA LUANA MACCARI",
        "ALESSIA MERLINO",
        "ALESSANDRO NANIA",
        "SALVATORE PRESTI",
        "CARMELITA PREVITI",
        "SALVATORE PULIAFITO",
        "GIOVANNA STEFANIA PUNTURO DETTA GIOVANNA",
        "SIMONA CLEMENTINA ROSINA DETTA SIMONA ROSINA",
        "SANDY SIRACUSA DETTA SENDY SIRACUSA",
        "ROSALBA CINZIA SMEDILE DETTA CINZIA SMEDILE",
        "GIUSEPPE SOTTILE",
        "STEFANO STURNIOLO",
        "GIOVANNI VALENTI"
      ]
    },
    "UNA MARCIA IN PIU'": {
      "coalition": "MELANGELA SCOLARO",
      "candidates": [
        "AMALIA ABBATE",
        "LUCA ARCORACI",
        "CARMELO BILARDO",
        "ANTONINO BIONDO",
        "COSIMO BUCCA",
        "CARMELA CALABRESE",
        "LUCIA CALIRI",
        "ANTONINO COMPOSTO",
        "ROSARIO CONDIPODERO",
        "VINCENZO CRINÒ",
        "MIRKO FORTUNATO DE PASQUALE",
        "HABDERRAMIN EL HORCHE DETTO ABRAMO",
        "ELIDA GURAY",
        "ZEZEM IBTISEM DETTA SEM",
        "GIOVANNA LO CASCIO",
        "DARIO ANGELO MAIMONE",
        "ROBERTA MARIA MANCUSO DETTA ROBERTA",
        "SALVATORE RAGUSA",
        "IGNAZIO ROTELLA",
        "BENEDETTO RUSSO",
        "MELANGELA SCOLARO",
        "ANTONINO SOTTILE",
        "GUGLIELMO TORRE",
        "JOSÈ ANGELO VIRGILLITO DETTO VIRGILLITO"
      ]
    },
    "BARCELLONA POZZO DI GOTTO IN COMUNE": {
      "coalition": "MELANGELA SCOLARO",
      "candidates": [
        "GIUSEPPE ABBATE",
        "PAOLO CALABRÒ",
        "CARMELO FABIO CAPPELLANO DETTO FABIO",
        "LEONE CASILE",
        "WALTER GIUSEPPE COPPOLINO",
        "GIUSEPPE CRISAFULLI",
        "GIAN PAOLO GENOVESE",
        "FRANCESCA MARIAPIA GIUNTA",
        "FRANCESCO GIUNTA",
        "SANTINA GIUNTA",
        "GIUSEPPA PASQUA GRASSO DETTA GIUSY",
        "ANTONINO LIZIO DETTO ANTHONY",
        "ALESSANDRA MAIO",
        "GIUSEPPE MANDANICI",
        "MELANIA ANTONELLA MAZZEO",
        "GAETANO MERCADANTE",
        "CRISTINA MIANO",
        "ROSARIO MOLICA FRANCO",
        "STEFANO ANTONINO PELLEGRINO",
        "DONATO RAIMONDO",
        "FILIPPO RUSSO",
        "MARIA DONATELLA SOTTILE",
        "ILENIA TORRE",
        "DANIELE TROVATO"
      ]
    },
    "FRATELLI D’ITALIA": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "EDUARDO BARCA DETTO EDUARDO",
        "GIORGIO LEONARDO CATALFAMO",
        "SALVATORE CHILLEMI",
        "VERA CUCÉ",
        "FORTUNATO D’AMICO",
        "LUIGI SEBASTIANO DALIA",
        "ERIKA DE FRANCESCO",
        "GRETA DI NUZZO DETTA DINUZZO",
        "CARMELO GIUNTA",
        "CARMELA IMBESI DETTA CARMEN DETTA GUERCIO",
        "VANESSA CHRISTINE ISGRÒ",
        "GIAMPIERO LA ROSA DETTO LAROSA",
        "ANTONINA LEPRO DETTA ANTONELLA",
        "FRANCESCA TINDARA LO PRESTI",
        "ALESSANDRA MIRABILE",
        "CESARE MOLINO",
        "DAISY FRANCESCA MUNNIA",
        "ANNA MUSCARA'",
        "ANGELO PARIDE PINO DETTO PARIDE DETTO ANGELO",
        "AGOSTINA RECUPERO",
        "AURORA STINCONE",
        "CONCETTA SAPORITA",
        "MARIA GABRIELA TORRE",
        "EVELYN TINDARA TRAPANI"
      ]
    },
    "NICOLA BARBERA SINDACO": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "SEBASTIANO BAURO",
        "MICHELE BENGALA",
        "GIOVANNI BATTISTA BUCALO DETTO TITTA DETTO BUCOLO",
        "TIZIANO CHIOFALO",
        "CETTINA CICCIARI",
        "MARIA CICERO",
        "DOMENICO GIUNTA",
        "MARIA GRANATA",
        "FRANCESCO FAZIO",
        "GIULIA FLORAMO",
        "CHIARA ITALIANO",
        "TINDARA LABOZZETTA DETTA TINA",
        "SONIA LANZA",
        "LUCIA MAZZEO",
        "PATRIZIA ANTONELLA MILONE",
        "LORENZO MUNAFÒ",
        "GIUSEPPE OCCELLO",
        "FRANCESCO PERDICHIZZI",
        "CARMELO PIRRI",
        "DANIELA PORCINO",
        "CARMELO RAVIDA'",
        "ANTONINO STEFANO SOTTILE",
        "ANDREANA FRANCESCA SPECIALE",
        "IRENE STAGNO"
      ]
    },
    "LA CIVICA BARCELLONA P.G.": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "SANDRA ALESCI",
        "CARMEN ALESCI",
        "MARIA CARMELA BUCCHERI",
        "COSIMO CALVO",
        "PAMELA CAMPO",
        "ANTONELLA CAPONE",
        "VINCENZO CATANESI",
        "MARIA CHILLEMI",
        "ANTONINA ROSALIA SMERALDA COSTANTINO",
        "IRENE FAZIO",
        "GIORGIO FERRARA",
        "GIANLUCA ANGELO GRASSO",
        "COSIMO GLIELMI",
        "GIUSEPPINA LIOTTA",
        "MARTINA MAIO",
        "CARMELO MUNAFÒ",
        "CATERINA PULIAFITO",
        "ANGELA SALMERI",
        "LUCIANO SAMUELE SCARPACI",
        "MARIA SCOLARO",
        "VELIO ANDREA SPARTA'",
        "SALVATORE TRASACCO",
        "MICHELE LETTERIO ZANGLA",
        "CARMELINA ZARCONE"
      ]
    },
    "FUORI DAL CORO": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "ROBERTO MOLINO",
        "MICHELE MANDANICI",
        "ANTONINO TINDARO MANGANO DETTO NINO",
        "LAURA ANTONELLA ALIBERTI",
        "ROSA SALVO",
        "FRANCESCA CALIRI",
        "FILIPPA SIMONA MAGGISTRO CONTENTA",
        "WAFAA ZANBIB",
        "CORRADA SIRACUSA",
        "CARMELO VIOLA",
        "SHPRESA SENAJ DETTA SPERANZA",
        "CATERINA AGRILLO DETTA KATRINE",
        "FEDERICO DI SALVO",
        "LUCIA GERBINO DETTA LUCIA PULEJO",
        "SEBASTIANA CALABRÒ DETTA LILIANA",
        "TINDARO GRASSO",
        "GIUSEPPINA SOTTILE",
        "CATERINA BARTOLONE",
        "MAURO BRANCIFORTE",
        "ANDREA GIULIO GIORGIANNI",
        "ELEONORA MARIA ILACQUA",
        "MARIA VANESSA SINDONI",
        "AURORA TORRE",
        "ROSALIA PAGANO"
      ]
    },
    "ASCOLTIAMO BARCELLONA": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "ENRICO ALFIO BACCARINI",
        "VITTORIA BERTAMI",
        "DOMENICO MIRKO BONACETO",
        "GIUSEPPE CAMBRIA",
        "MARIA CONTI",
        "FRANCESCO CORDARO",
        "CATERINA CHIOFALO",
        "PROVVIDENZA ANTONINA CHIOFALO",
        "MARIA TINDARA GULLO",
        "MYRIAM IUCULANO",
        "NUNZIO LA MACCHIA",
        "GIUSEPPE LEMBO",
        "DOMENICA MILONE",
        "MICHELE PINO",
        "LUDOVICA RAFFA",
        "NATALE TINDARO PARATORE",
        "CLAUDIO PASCALONE",
        "LUCA TALAMO"
      ]
    },
    "NOI CI SIAMO": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "MARIA CARMELA ABBATE",
        "GIOVANNI ALESCI",
        "SALVATORE BENENATI",
        "ORNELLA TINDARA CANNATA",
        "GIUSEPPE CATALANO",
        "VIVIANNA COPPOLINO",
        "DORIANA D’AMICO",
        "MARTIN ELIAS FAZIO",
        "STEFANO GIORGIANNI",
        "FRANCESCO GIUNTA",
        "ARLETA TERESA LIS",
        "GIUSEPPE MAIO",
        "MARIA GRAZIA MAZZEO",
        "SEBASTIANO SALVATORE MIANO",
        "VINCENZO NANIA",
        "MARIA OTERA",
        "DANIELE PICCOLO",
        "CLELIA PUDDU",
        "DANIELA SAFFIOTI",
        "GIUSEPPE ANTONINO SCARPACI",
        "SALVATORE TORRE",
        "SALVATORE TRIFILÒ",
        "MARCO VIOLA"
      ]
    },
    "FORZA ITALIA": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "ALFREDO GIOVANNI ASPA",
        "LUIGI BAMBACI",
        "MARIO BARRESI",
        "ORAZIO BENINATI",
        "ANTONIO BIONDO",
        "PAOLA BUCCA",
        "ANGELA BUCOLO",
        "CARMELO CALDERONE",
        "MARIA CARUSO",
        "TINDARO GIOVINAZZO",
        "DANIELA IANNELLO",
        "ANDREANA IMPOLLINO DETTA LILIANA",
        "MARIKA LAX DETTA CATALFAMO",
        "SEBASTIANO MIGLIORE",
        "CARMELA PERDICHIZZI DETTA CARMELINA",
        "TOMMASO MARIA PINO",
        "LIDIA PIRRI",
        "FRANCESCO PULIAFITO",
        "CARMEN ELENA ROMINU",
        "DANIELA SCARPACI",
        "JASMINE SCIACCA",
        "GIANLUCA SIDOTI",
        "ELISABETTA SOFIA",
        "DOMENICO TRIO DETTO MIMMO"
      ]
    },
    "AZZURRI PER BARCELLONA P.G.": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "ALESSANDRO ABBATE",
        "GIUSEPPE ANTONIO ALIQUÒ",
        "FABIANA BARTOLOTTA DETTA FABIANA",
        "GIANFRANCO BENENATI",
        "GIOVANNI CAMPANELLA",
        "COSIMA ANNA CARANNA",
        "FRANCO SALVATORE CARUSO",
        "GIUSEPPE COPPOLINO",
        "RICCARDO D’AMICO",
        "GIOVANNI DE PASQUALE",
        "ANTONELLA DRAGO FERRANTE",
        "GRAZIELLA GENOVESE",
        "LORENZO GITTO",
        "CATERINA VANESSA GIUNTA",
        "FERDINANDO GROSSO",
        "VALERIA ITALIANO",
        "OKSANA KRAVCHENKO DETTA OXA",
        "DIEGO LANZA",
        "LUANA CONCETTA MARCHESE",
        "ELEONORA MARIA ANTONINA MARZULLO",
        "SEBASTIANO MAZZEO",
        "ALESSANDRO MIANO",
        "YVONNE SAJA",
        "ANTONINO SCIACCA"
      ]
    },
    "VAMOS! CON BARBERA SINDACO": {
      "coalition": "NICOLA BARBERA",
      "candidates": [
        "GIUSEPPE GIOVANNI ALOSI DETTO PEPPINO",
        "ANDREA BARRESI",
        "ROSARIO BILARDO",
        "MARIA TINDARA BIONDO",
        "FULVIO LUCA BUCCA",
        "CARMELO CALDERONE",
        "SANTINA ELVIRA CAPONE",
        "NICOLÒ CHILLEMI",
        "ANTONINO D’AMICO",
        "GIUSI D’ANGELO",
        "MARISA DI SALVO",
        "ANTONINO FAMA'",
        "ROSARIO INGEGNERI",
        "FRANCESCO LA ROCCA DETTO FRANCO",
        "PIETRO MARCHESE",
        "ANGELA MENDOLIA",
        "ELIBJONDA METUSHAJ DETTA ELI",
        "MARIA CARMELA MIANO",
        "CARMELINA MILONE",
        "PAOLO PICCOLO",
        "ANGELA TELLERI",
        "RITA TORRE",
        "DENISE TRAVIGLIA",
        "CARMELA VILLALBA DETTA CARMEN"
      ]
    }
  }
}


def load_election_data_from_settings():
    """Carica eventuali liste/candidati personalizzati salvati dall'amministratore."""
    global ELECTION_DATA
    try:
        if not os.path.exists(DB_PATH):
            return
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT value FROM settings WHERE key='election_data_json'").fetchone()
        conn.close()
        if row and row[0]:
            data = json.loads(row[0])
            if isinstance(data, dict) and isinstance(data.get('mayors'), list) and isinstance(data.get('lists'), dict):
                ELECTION_DATA = data
    except Exception:
        pass

def _allowed_lists_from_user(user):
    raw = ''
    try:
        raw = user['allowed_lists'] or ''
    except Exception:
        raw = ''
    if not raw:
        return []
    return [x.strip() for x in raw.split('|') if x.strip()]

def election_data_for_user(user):
    if not user or user['role'] == 'admin':
        return ELECTION_DATA
    allowed = _allowed_lists_from_user(user)
    if not allowed:
        return ELECTION_DATA
    lists = {k:v for k,v in ELECTION_DATA['lists'].items() if k in allowed}
    mayors = sorted(set(ELECTION_DATA['mayors']) | {v.get('coalition') for v in lists.values() if v.get('coalition')})
    return {'mayors': mayors, 'lists': lists}

def _safe_split_votes(value):
    if isinstance(value, list):
        return value
    try:
        return json.loads(value or '[]')
    except Exception:
        return []

def fast_pin_hash(pin):
    # Import CSV: hashing volutamente leggero per evitare timeout su Render.
    # check_password_hash resta compatibile con questo formato Werkzeug.
    return generate_password_hash(str(pin), method="pbkdf2:sha256:1", salt_length=4)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        qr_token TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        section TEXT,
        allowed_lists TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
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
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL,
        list_name TEXT,
        name TEXT NOT NULL,
        votes INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )""")

    user_cols = [row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()]
    if "allowed_lists" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN allowed_lists TEXT")

    report_cols = [row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()]
    migrations = {
        "voters": "ALTER TABLE reports ADD COLUMN voters INTEGER NOT NULL DEFAULT 0",
        "blank_ballots": "ALTER TABLE reports ADD COLUMN blank_ballots INTEGER NOT NULL DEFAULT 0",
        "null_ballots": "ALTER TABLE reports ADD COLUMN null_ballots INTEGER NOT NULL DEFAULT 0",
        "contested_ballots": "ALTER TABLE reports ADD COLUMN contested_ballots INTEGER NOT NULL DEFAULT 0",
        "split_votes_json": "ALTER TABLE reports ADD COLUMN split_votes_json TEXT NOT NULL DEFAULT '[]'",
        "closed": "ALTER TABLE reports ADD COLUMN closed INTEGER NOT NULL DEFAULT 0",
        "closed_at": "ALTER TABLE reports ADD COLUMN closed_at TEXT"
    }
    for col, sql in migrations.items():
        if col not in report_cols:
            cur.execute(sql)

    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    defaults = {
        "total_electors": "0",
        "total_voters": "0",
        "council_seats": "24",
        "winner_mayor": "NICOLA BARBERA",
        "mode": "first",
        "election_data_json": json.dumps(ELECTION_DATA, ensure_ascii=False)
    }
    for key, value in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))
    cur.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        demo_users = [
            ("Amministratore Centrale", "admin", "1234", "admin", None),
            ("Rappresentante Sezione 1", "3330000001", "1111", "rappresentante", "1"),
            ("Rappresentante Sezione 2", "3330000002", "2222", "rappresentante", "2"),
        ]
        for name, phone, pin, role, section in demo_users:
            cur.execute(
                "INSERT INTO users(name, phone, pin_hash, qr_token, role, section, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, now),
            )

    # Un solo record logico per sezione/seggio:
    # primo inserimento = INSERT, salvataggi successivi = UPDATE.
    cur.execute("""
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM reports
            GROUP BY section
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_section_unique ON reports(section)")


    # Deduplica voti storici: conserva l'ultimo record per report/tipo/lista/nome.
    cur.execute("""
        DELETE FROM votes
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM votes
            GROUP BY report_id, vote_type, COALESCE(list_name,''), name
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_unique_update_import ON votes(report_id, vote_type, COALESCE(list_name,''), name)")


    # Deduplica report storici: un solo report per sezione/TOTALE.
    cur.execute("""
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM reports
            GROUP BY section
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_section_update_import ON reports(section)")


    # Deduplica voti importati: un solo record per report/tipo/lista/nome.
    cur.execute("""
        DELETE FROM votes
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM votes
            GROUP BY report_id, vote_type, COALESCE(list_name,''), name
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_update_csv_unique_v56 ON votes(report_id, vote_type, COALESCE(list_name,''), name)")

    conn.commit()
    conn.close()

@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()
    load_election_data_from_settings()

def current_user():
    user_id = session.get("uid")
    if not user_id:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
    conn.close()
    return user

def public_user(user):
    allowed = []
    try:
        allowed = _allowed_lists_from_user(user)
    except Exception:
        allowed = []
    return {"id": user["id"], "name": user["name"], "phone": user["phone"], "role": user["role"], "section": user["section"], "allowed_lists": allowed}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"ok": False, "error": "Accesso non autorizzato"}), 401
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Accesso non autorizzato"}), 401
        if user["role"] != "admin":
            return jsonify({"ok": False, "error": "Funzione riservata all'amministratore"}), 403
        return fn(*args, **kwargs)
    return wrapper

def get_settings(conn):
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {r["key"]: r["value"] for r in rows}
    return {
        "total_electors": int(settings.get("total_electors", "0") or 0),
        "total_voters": int(settings.get("total_voters", "0") or 0),
        "council_seats": int(settings.get("council_seats", "24") or 24),
        "winner_mayor": settings.get("winner_mayor", "NICOLA BARBERA"),
        "mode": settings.get("mode", "first"),
    }

def d_hondt(votes, seats):
    result = {key: 0 for key in votes}
    quotients = []
    for key, value in votes.items():
        for divisor in range(1, seats + 1):
            quotients.append((value / divisor if divisor else 0, key, value, divisor))
    quotients.sort(key=lambda item: (-item[0], -item[2], item[1]))
    for _, key, _, _ in quotients[:seats]:
        result[key] += 1
    return result

def compute_elected(conn):
    settings = get_settings(conn)
    seats = max(1, settings["council_seats"])
    winner = settings["winner_mayor"]
    mode = settings["mode"]
    list_rows = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name").fetchall()
    pref_rows = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name").fetchall()
    mayor_rows = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name").fetchall()
    mayor_votes = {row["name"]: int(row["total"] or 0) for row in mayor_rows}
    list_votes = {row["name"]: int(row["total"] or 0) for row in list_rows}
    total_list_votes = sum(list_votes.values())
    threshold = total_list_votes * 0.05
    admitted_lists = {name: votes for name, votes in list_votes.items() if votes > 0 and votes >= threshold}
    coalition_votes = {}
    for list_name, votes in admitted_lists.items():
        coalition = ELECTION_DATA["lists"][list_name]["coalition"]
        coalition_votes[coalition] = coalition_votes.get(coalition, 0) + votes
    coalition_seats = d_hondt(coalition_votes, seats) if coalition_votes else {}
    winner_coal_votes = coalition_votes.get(winner, 0)
    winner_pct = (winner_coal_votes / total_list_votes * 100) if total_list_votes else 0
    other_max_pct = max([v / total_list_votes * 100 for c, v in coalition_votes.items() if c != winner] or [0]) if total_list_votes else 0
    premium_seats = math.ceil(seats * 0.60)
    natural_winner_seats = coalition_seats.get(winner, 0)
    premium_applied = natural_winner_seats < premium_seats and other_max_pct <= 50 and (mode == "runoff" or winner_pct >= 40)
    if premium_applied:
        coalition_seats[winner] = premium_seats
        remaining_seats = seats - premium_seats
        other_coalitions = {coalition: votes for coalition, votes in coalition_votes.items() if coalition != winner}
        other_seats = d_hondt(other_coalitions, remaining_seats) if other_coalitions and remaining_seats > 0 else {}
        for coalition in other_coalitions:
            coalition_seats[coalition] = other_seats.get(coalition, 0)
    list_seats = {}
    for coalition, coalition_seat_count in coalition_seats.items():
        lists_in_coalition = {list_name: votes for list_name, votes in admitted_lists.items() if ELECTION_DATA["lists"][list_name]["coalition"] == coalition}
        assigned = d_hondt(lists_in_coalition, coalition_seat_count) if lists_in_coalition and coalition_seat_count > 0 else {}
        list_seats.update(assigned)
    preferences = {}
    for row in pref_rows:
        preferences.setdefault(row["list_name"], {})[row["name"]] = int(row["total"] or 0)
    elected = {}
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        count = list_seats.get(list_name, 0)
        ranked = []
        for index, candidate in enumerate(list_obj["candidates"]):
            ranked.append({"name": candidate, "votes": preferences.get(list_name, {}).get(candidate, 0), "order": index + 1})
        ranked.sort(key=lambda item: (-item["votes"], item["order"]))
        elected[list_name] = ranked[:count]
    losing_mayors = sorted([{"name": name, "votes": mayor_votes.get(name, 0)} for name in ELECTION_DATA["mayors"] if name != winner], key=lambda item: -item["votes"])
    return {
        "settings": settings, "mayor_votes": mayor_votes, "list_votes": list_votes,
        "total_list_votes": total_list_votes, "threshold": threshold,
        "admitted_lists": admitted_lists, "coalition_votes": coalition_votes,
        "coalition_seats": coalition_seats, "list_seats": list_seats,
        "elected": elected, "premium_applied": premium_applied,
        "premium_seats": premium_seats, "winner_pct": winner_pct,
        "other_max_pct": other_max_pct, "losing_mayors": losing_mayors,
    }

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/admin")
def admin_page():
    return send_from_directory(STATIC_DIR, "admin.html")


@app.route("/admin/charts")
def admin_charts_page():
    return send_from_directory(STATIC_DIR, "admin_charts.html")

@app.route("/admin/imports")
def admin_imports_page():
    return send_from_directory(STATIC_DIR, "admin_imports.html")

@app.route("/admin/users")
def admin_users_page():
    return send_from_directory(STATIC_DIR, "admin_users.html")


@app.route("/admin/tools")
def admin_tools_page():
    return send_from_directory(STATIC_DIR, "admin_tools.html")


@app.route("/admin/intelligence")
def admin_intelligence_page():
    return send_from_directory(STATIC_DIR, "admin_intelligence.html")

@app.route("/admin/social")
def admin_social_page():
    return send_from_directory(STATIC_DIR, "admin_social.html")

@app.route("/public-dashboard")
def public_dashboard_page():
    return send_from_directory(STATIC_DIR, "public_dashboard.html")

@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    phone = str(data.get("phone", "")).strip()
    pin = str(data.get("pin", "")).strip()
    token = str(data.get("token", "")).strip()
    conn = db()
    user = None
    if token:
        user = conn.execute("SELECT * FROM users WHERE qr_token=? AND active=1", (token,)).fetchone()
    elif phone and pin:
        user = conn.execute("SELECT * FROM users WHERE phone=? AND active=1", (phone,)).fetchone()
        if user and not check_password_hash(user["pin_hash"], pin):
            user = None
    conn.close()
    if not user:
        return jsonify({"ok": False, "error": "Credenziali non valide"}), 401
    session["uid"] = user["id"]
    return jsonify({"ok": True, "user": public_user(user)})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
@login_required
def me():
    return jsonify({"ok": True, "user": public_user(current_user())})

@app.get("/api/config")
@login_required
def config():
    conn = db()
    settings = get_settings(conn)
    conn.close()
    return jsonify({"ok": True, "data": election_data_for_user(current_user()), "all_data": ELECTION_DATA if current_user()["role"] == "admin" else None, "settings": settings})


@app.get("/api/my-report")
@login_required
def my_report():
    user = current_user()
    section = request.args.get("section", user["section"] or "").strip()

    if not section:
        return jsonify({"ok": True, "exists": False})

    if user["role"] != "admin" and user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403

    conn = db()
    report = conn.execute(
        "SELECT * FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1",
        (section,)
    ).fetchone()

    if not report:
        conn.close()
        return jsonify({"ok": True, "exists": False, "section": section})

    votes = conn.execute(
        "SELECT vote_type, list_name, name, votes FROM votes WHERE report_id=?",
        (report["id"],)
    ).fetchall()
    conn.close()

    mayors = {}
    list_votes = {}
    preferences = {}

    for row in votes:
        if row["vote_type"] == "sindaco":
            mayors[row["name"]] = row["votes"]
        elif row["vote_type"] == "lista":
            list_votes[row["list_name"]] = row["votes"]
        elif row["vote_type"] == "preferenza":
            preferences.setdefault(row["list_name"], {})
            preferences[row["list_name"]][row["name"]] = row["votes"]

    return jsonify({
        "ok": True,
        "exists": True,
        "section": report["section"],
        "voters": report["voters"],
        "blank_ballots": report["blank_ballots"],
        "null_ballots": report["null_ballots"],
        "section_electors": report["contested_ballots"],
        "contested_ballots": report["contested_ballots"],
        "split_votes": _safe_split_votes(report["split_votes_json"] if "split_votes_json" in report.keys() else "[]"),
        "closed": bool(report["closed"]),
        "closed_at": report["closed_at"],
        "mayors": mayors,
        "list_votes": list_votes,
        "preferences": preferences,
        "updated_at": report["updated_at"]
    })

@app.post("/api/report")
@login_required
def save_report():
    user = current_user()
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    voters = int(data.get("voters", 0) or 0)
    blank_ballots = int(data.get("blank_ballots", 0) or 0)
    null_ballots = int(data.get("null_ballots", 0) or 0)
    section_electors = int(data.get("section_electors", data.get("contested_ballots", 0)) or 0)
    mayor_votes = data.get("mayors", {})
    list_votes = data.get("list_votes", {})
    preferences = data.get("preferences", {})
    split_votes = _safe_split_votes(data.get("split_votes", []))
    if not section:
        return jsonify({"ok": False, "error": "Inserire la sezione"}), 400
    if user["role"] != "admin" and user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403
    valid_mayor_votes = sum(int(v or 0) for v in mayor_votes.values())
    valid_list_votes = sum(int(v or 0) for v in list_votes.values())
    valid_votes = max(valid_mayor_votes, valid_list_votes)
    expected_voters = valid_votes + blank_ballots + null_ballots
    # Invio parziale consentito anche se la quadratura non è definitiva.
    # Il controllo bloccante avviene solo con il pulsante Chiudi seggio.
    now = datetime.now().isoformat(timespec="seconds")
    conn = db()
    cur = conn.cursor()
    existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()
    if existing and user["role"] != "admin" and existing["closed"]:
        conn.close()
        return jsonify({"ok": False, "error": "Il seggio risulta gia' chiuso. Non puoi piu' modificare o inviare dati."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, split_votes_json=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, section_electors, json.dumps(split_votes, ensure_ascii=False), now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, split_votes_json, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, section_electors, json.dumps(split_votes, ensure_ascii=False), now, now))
        report_id = cur.lastrowid
    for name in ELECTION_DATA["mayors"]:
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "sindaco", None, name, int(mayor_votes.get(name, 0) or 0)))
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "lista", list_name, list_name, int(list_votes.get(list_name, 0) or 0)))
        pref_for_list = preferences.get(list_name, {})
        for candidate in list_obj["candidates"]:
            cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "preferenza", list_name, candidate, int(pref_for_list.get(candidate, 0) or 0)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Dati inviati al server centrale"})


@app.get("/api/section-status")
@login_required
def section_status():
    user = current_user()
    section = request.args.get("section", user["section"] or "").strip()
    if not section:
        return jsonify({"ok": True, "closed": False, "section": section})
    conn = db()
    row = conn.execute("SELECT closed, closed_at FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1", (section,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "section": section, "closed": bool(row["closed"]) if row else False, "closed_at": row["closed_at"] if row else None})

@app.post("/api/close-seat")
@login_required
def close_seat():
    user = current_user()
    if user["role"] == "admin":
        return jsonify({"ok": False, "error": "La chiusura seggio è riservata al rappresentante."}), 403
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    voters = int(data.get("voters", 0) or 0)
    blank_ballots = int(data.get("blank_ballots", 0) or 0)
    null_ballots = int(data.get("null_ballots", 0) or 0)
    section_electors = int(data.get("section_electors", data.get("contested_ballots", 0)) or 0)
    mayor_votes = data.get("mayors", {})
    list_votes = data.get("list_votes", {})
    preferences = data.get("preferences", {})
    split_votes = _safe_split_votes(data.get("split_votes", []))
    if not section:
        return jsonify({"ok": False, "error": "Inserire la sezione"}), 400
    if user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403
    valid_mayor_votes = sum(int(v or 0) for v in mayor_votes.values())
    valid_list_votes = sum(int(v or 0) for v in list_votes.values())
    valid_votes = max(valid_mayor_votes, valid_list_votes)
    expected_voters = valid_votes + blank_ballots + null_ballots
    if voters != expected_voters:
        return jsonify({"ok": False, "error": f"Non è possibile chiudere il seggio: votanti={voters}, totale valido + bianche + nulle={expected_voters}. Le contestate sono solo indicative."}), 400
    now = datetime.now().isoformat(timespec="seconds")
    conn = db(); cur = conn.cursor()
    existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()
    if existing and existing["closed"]:
        conn.close(); return jsonify({"ok": False, "error": "Il seggio è gia' chiuso."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, split_votes_json=?, closed=1, closed_at=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, section_electors, json.dumps(split_votes, ensure_ascii=False), now, now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, split_votes_json, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, section_electors, json.dumps(split_votes, ensure_ascii=False), 1, now, now, now))
        report_id = cur.lastrowid
    for name in ELECTION_DATA["mayors"]:
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "sindaco", None, name, int(mayor_votes.get(name, 0) or 0)))
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "lista", list_name, list_name, int(list_votes.get(list_name, 0) or 0)))
        pref_for_list = preferences.get(list_name, {})
        for candidate in list_obj["candidates"]:
            cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "preferenza", list_name, candidate, int(pref_for_list.get(candidate, 0) or 0)))
    conn.commit(); conn.close(); session.clear()
    return jsonify({"ok": True, "message": "Grazie per il tuo contributo. Il seggio è stato chiuso correttamente."})

@app.post("/api/reopen-section")
@admin_required
def reopen_section():
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()

    if not section:
        return jsonify({"ok": False, "error": "Sezione obbligatoria"}), 400

    now = datetime.now().isoformat(timespec="seconds")

    conn = db()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT id FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1",
        (section,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Nessuna rilevazione trovata per questo seggio"}), 404

    # Riattiva il seggio mantenendo tutti i dati gia' aggiornati presenti nel database.
    cur.execute(
        "UPDATE reports SET closed=0, closed_at=NULL, updated_at=? WHERE section=?",
        (now, section)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Seggio riattivato con i dati aggiornati gia' presenti. Il rappresentante può nuovamente accedere e modificare."
    })



@app.get("/api/dashboard")
@admin_required
def dashboard():
    conn = db()
    mayors = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name ORDER BY total DESC").fetchall()
    lists = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name ORDER BY total DESC").fetchall()
    preferences = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name ORDER BY total DESC").fetchall()
    sections = conn.execute("""
        SELECT r.section, u.name AS representative, r.updated_at,
          r.voters, r.blank_ballots, r.null_ballots, r.contested_ballots, r.split_votes_json, r.closed, r.closed_at,
          SUM(CASE WHEN v.vote_type='sindaco' THEN v.votes ELSE 0 END) AS total_mayors,
          SUM(CASE WHEN v.vote_type='lista' THEN v.votes ELSE 0 END) AS total_lists,
          SUM(CASE WHEN v.vote_type='preferenza' THEN v.votes ELSE 0 END) AS total_preferences
        FROM reports r
        JOIN users u ON u.id=r.user_id
        JOIN votes v ON v.report_id=r.id
        GROUP BY r.id
        ORDER BY CAST(r.section AS INTEGER), r.section
    """).fetchall()
    ballot_totals = conn.execute("SELECT COALESCE(SUM(voters),0) AS voters, COALESCE(SUM(blank_ballots),0) AS blank_ballots, COALESCE(SUM(null_ballots),0) AS null_ballots, COALESCE(SUM(contested_ballots),0) AS section_electors FROM reports").fetchone()
    election = compute_elected(conn)
    conn.close()
    
    section_dicts = []
    split_total = 0
    for row in sections:
        item = dict(row)
        sv = _safe_split_votes(item.get("split_votes_json", "[]"))
        item["split_vote_count"] = sum(int(x.get("votes", 0) or 0) for x in sv if isinstance(x, dict))
        item.pop("split_votes_json", None)
        split_total += item["split_vote_count"]
        section_dicts.append(item)
    bt = dict(ballot_totals)
    bt["split_vote_count"] = split_total
    return jsonify({"ok": True, "mayors": [dict(row) for row in mayors], "lists": [dict(row) for row in lists], "preferences": [dict(row) for row in preferences], "sections": section_dicts, "ballot_totals": bt, "data": ELECTION_DATA, "election": election})



def _intelligence_payload(conn):
    settings = get_settings(conn)
    # Totali generali
    mayor_rows = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name ORDER BY total DESC").fetchall()
    list_rows = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name ORDER BY total DESC").fetchall()
    pref_rows = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name ORDER BY total DESC").fetchall()
    section_rows = conn.execute("""
        SELECT r.id, r.section, r.voters, r.blank_ballots, r.null_ballots, r.contested_ballots, r.split_votes_json, r.closed, r.updated_at,
               u.name AS representative
        FROM reports r LEFT JOIN users u ON u.id=r.user_id
        ORDER BY CAST(r.section AS INTEGER), r.section
    """).fetchall()
    vote_rows = conn.execute("""
        SELECT r.section, v.vote_type, v.list_name, v.name, v.votes
        FROM votes v JOIN reports r ON r.id=v.report_id
    """).fetchall()

    sections = {str(r["section"]): dict(r) for r in section_rows}
    for sec, item in sections.items():
        item["mayors"] = {}
        item["lists"] = {}
        item["preferences"] = {}
        split = _safe_split_votes(item.get("split_votes_json", "[]"))
        item["split_vote_count"] = sum(int(x.get("votes", 0) or 0) for x in split if isinstance(x, dict))
        item["split_votes"] = split
        item.pop("split_votes_json", None)

    for v in vote_rows:
        sec = str(v["section"])
        if sec not in sections:
            continue
        if v["vote_type"] == "sindaco":
            sections[sec]["mayors"][v["name"]] = int(v["votes"] or 0)
        elif v["vote_type"] == "lista":
            sections[sec]["lists"][v["list_name"]] = int(v["votes"] or 0)
        elif v["vote_type"] == "preferenza":
            sections[sec]["preferences"].setdefault(v["list_name"], {})[v["name"]] = int(v["votes"] or 0)

    total_list_votes = sum(int(r["total"] or 0) for r in list_rows)
    total_mayor_votes = sum(int(r["total"] or 0) for r in mayor_rows)
    total_voters = settings.get("total_voters") or sum(int(r["voters"] or 0) for r in section_rows)
    total_electors = settings.get("total_electors") or sum(int(r["contested_ballots"] or 0) for r in section_rows)
    split_total = sum(x.get("split_vote_count",0) for x in sections.values())

    # 1) Heatmap territoriale: intensità consenso per sezione/lista/coalizione/sindaco.
    heatmap = []
    for sec, item in sections.items():
        voters = int(item.get("voters") or 0)
        electors = int(item.get("contested_ballots") or 0)
        list_total = sum(item["lists"].values())
        mayor_total = sum(item["mayors"].values())
        turnout = (voters / electors * 100) if electors else 0
        top_list, top_list_votes = (None, 0)
        if item["lists"]:
            top_list, top_list_votes = max(item["lists"].items(), key=lambda kv: kv[1])
        top_mayor, top_mayor_votes = (None, 0)
        if item["mayors"]:
            top_mayor, top_mayor_votes = max(item["mayors"].items(), key=lambda kv: kv[1])
        coalition_votes = {}
        for lname, votes in item["lists"].items():
            coalition = ELECTION_DATA["lists"].get(lname, {}).get("coalition", "Non classificata")
            coalition_votes[coalition] = coalition_votes.get(coalition, 0) + votes
        top_coalition, top_coalition_votes = (None, 0)
        if coalition_votes:
            top_coalition, top_coalition_votes = max(coalition_votes.items(), key=lambda kv: kv[1])
        heatmap.append({
            "section": sec,
            "representative": item.get("representative") or "",
            "voters": voters,
            "electors": electors,
            "turnout_pct": round(turnout,2),
            "valid_lists": list_total,
            "valid_mayors": mayor_total,
            "top_list": top_list,
            "top_list_votes": top_list_votes,
            "top_list_pct": round((top_list_votes/list_total*100),2) if list_total else 0,
            "top_mayor": top_mayor,
            "top_mayor_votes": top_mayor_votes,
            "top_mayor_pct": round((top_mayor_votes/mayor_total*100),2) if mayor_total else 0,
            "top_coalition": top_coalition,
            "top_coalition_votes": top_coalition_votes,
            "top_coalition_pct": round((top_coalition_votes/list_total*100),2) if list_total else 0,
            "split_vote_count": item.get("split_vote_count",0),
            "split_rate_pct": round((item.get("split_vote_count",0)/voters*100),2) if voters else 0,
            "closed": bool(item.get("closed")),
            "updated_at": item.get("updated_at")
        })

    # 2) Reti clientelari/body politico: grafo candidato -> sezione -> lista con alert concentrazione.
    body_nodes = {}
    body_edges = []
    concentration_alerts = []
    for sec, item in sections.items():
        for list_name, prefs in item["preferences"].items():
            for cand, votes in prefs.items():
                votes = int(votes or 0)
                if votes <= 0: continue
                key_c = "cand::"+cand
                key_s = "sec::"+sec
                key_l = "list::"+list_name
                body_nodes[key_c] = {"id": key_c, "label": cand, "type": "candidate", "weight": body_nodes.get(key_c,{}).get("weight",0)+votes}
                body_nodes[key_s] = {"id": key_s, "label": "Sez. "+sec, "type": "section", "weight": body_nodes.get(key_s,{}).get("weight",0)+votes}
                body_nodes[key_l] = {"id": key_l, "label": list_name, "type": "list", "weight": body_nodes.get(key_l,{}).get("weight",0)+votes}
                body_edges.append({"source": key_c, "target": key_s, "votes": votes})
                body_edges.append({"source": key_c, "target": key_l, "votes": votes})
                sec_total_pref = sum(int(v or 0) for all_prefs in item["preferences"].values() for v in all_prefs.values())
                rate = (votes/sec_total_pref*100) if sec_total_pref else 0
                if votes >= 10 and rate >= 25:
                    concentration_alerts.append({"candidate": cand, "list": list_name, "section": sec, "votes": votes, "section_pref_share_pct": round(rate,2), "level": "alta" if rate >= 40 else "media"})
    top_edges = sorted(body_edges, key=lambda e:e["votes"], reverse=True)[:120]
    top_node_ids = set()
    for e in top_edges:
        top_node_ids.add(e["source"]); top_node_ids.add(e["target"])
    body_graph = {"nodes": [n for k,n in body_nodes.items() if k in top_node_ids], "edges": top_edges, "alerts": sorted(concentration_alerts, key=lambda x:(-x["section_pref_share_pct"], -x["votes"]))[:80]}

    # 3) Predizione elettorale AI-like: proiezione deterministica su sezioni mancanti, scenario prudente.
    closed_sections = [h for h in heatmap if h["closed"]]
    loaded_sections = [h for h in heatmap if h["valid_lists"] or h["valid_mayors"]]
    avg_voters = (sum(h["voters"] for h in loaded_sections)/len(loaded_sections)) if loaded_sections else 0
    target_voters = total_voters or sum(h["voters"] for h in loaded_sections)
    observed_voters = sum(h["voters"] for h in loaded_sections)
    missing_voters = max(0, target_voters - observed_voters)
    list_totals = {r["name"]: int(r["total"] or 0) for r in list_rows}
    mayor_totals = {r["name"]: int(r["total"] or 0) for r in mayor_rows}
    def project(totals, observed_total):
        out=[]
        for name, val in totals.items():
            share = val/observed_total if observed_total else 0
            projected = val + round(missing_voters * share)
            out.append({"name": name, "current": val, "share_pct": round(share*100,2), "projected": projected})
        return sorted(out, key=lambda x:x["projected"], reverse=True)
    prediction = {
        "method": "Proiezione proporzionale sulle sezioni caricate con correzione dei votanti mancanti; usare come scenario operativo, non come sondaggio.",
        "loaded_sections": len(loaded_sections),
        "closed_sections": len(closed_sections),
        "observed_voters": observed_voters,
        "target_voters": target_voters,
        "missing_voters_estimate": missing_voters,
        "average_voters_loaded_section": round(avg_voters,2),
        "mayors": project(mayor_totals, total_mayor_votes),
        "lists": project(list_totals, total_list_votes)
    }

    # 4) Peso politico reale: traino, efficienza, radicamento, dispersione preferenze.
    pref_totals = {}
    candidate_sections = {}
    for sec, item in sections.items():
        for list_name, prefs in item["preferences"].items():
            for cand, votes in prefs.items():
                votes=int(votes or 0)
                if votes<=0: continue
                key=(list_name,cand)
                pref_totals[key]=pref_totals.get(key,0)+votes
                candidate_sections.setdefault(key,{})[sec]=votes
    political_weight=[]
    for (list_name,cand), votes in pref_totals.items():
        list_total = list_totals.get(list_name,0)
        sections_map = candidate_sections.get((list_name,cand),{})
        max_section = max(sections_map.values()) if sections_map else 0
        spread = len([v for v in sections_map.values() if v>0])
        concentration = (max_section/votes*100) if votes else 0
        eff = (votes/list_total*100) if list_total else 0
        body_index = min(100, round(eff*4 + spread*3 + (100-concentration)*0.25,2))
        political_weight.append({
            "candidate": cand, "list": list_name, "coalition": ELECTION_DATA["lists"].get(list_name,{}).get("coalition",""),
            "preferences": votes, "list_total": list_total, "preference_on_list_pct": round(eff,2),
            "sections_with_votes": spread, "max_section_votes": max_section, "concentration_pct": round(concentration,2),
            "body_index": body_index,
            "profile": "leader territoriale" if votes>=30 and concentration>=45 else ("diffuso" if spread>=5 and concentration<40 else "presidio locale")
        })
    political_weight.sort(key=lambda x:(-x["body_index"], -x["preferences"]))

    # Social score: ranking comunicabile pubblicamente.
    social_cards=[]
    for i,x in enumerate(political_weight[:60], start=1):
        score = min(100, round(x["body_index"]*0.65 + x["preference_on_list_pct"]*1.8 + x["sections_with_votes"]*1.2,2))
        badges=[]
        if x["profile"]=="leader territoriale": badges.append("Leader territoriale")
        if x["sections_with_votes"]>=5: badges.append("Consenso diffuso")
        if x["concentration_pct"]>=45: badges.append("Sezione forte")
        if not badges: badges.append("Candidato emergente")
        social_cards.append({**x, "rank": i, "political_score": score, "badges": badges, "share_text": f"{x['candidate']} · {x['list']} · Political Score {score}/100 · {', '.join(badges)}"})

    return {
        "ok": True,
        "summary": {"total_electors": total_electors, "total_voters": total_voters, "observed_voters": observed_voters, "total_list_votes": total_list_votes, "total_mayor_votes": total_mayor_votes, "split_vote_count": split_total, "sections_loaded": len(loaded_sections), "sections_closed": len(closed_sections)},
        "heatmap": heatmap,
        "body_graph": body_graph,
        "prediction": prediction,
        "political_weight": political_weight,
        "social_cards": social_cards,
        "data": ELECTION_DATA
    }

@app.get("/api/intelligence")
@admin_required
def intelligence_api():
    conn = db()
    payload = _intelligence_payload(conn)
    conn.close()
    return jsonify(payload)

@app.get("/api/public-dashboard")
def public_dashboard_api():
    conn = db()
    payload = _intelligence_payload(conn)
    conn.close()
    # Endpoint pensato per dashboard condivisibili: niente utenti, telefoni o note operative interne.
    return jsonify({
        "ok": True,
        "summary": payload["summary"],
        "heatmap": payload["heatmap"],
        "prediction": payload["prediction"],
        "social_cards": payload["social_cards"][:30]
    })

@app.post("/api/settings")
@admin_required
def update_settings():
    data = request.get_json(force=True)
    allowed = ["total_electors", "total_voters", "council_seats", "winner_mayor", "mode"]
    conn = db()
    cur = conn.cursor()
    for key in allowed:
        if key in data:
            cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, str(data[key])))
    conn.commit()
    settings = get_settings(conn)
    conn.close()
    return jsonify({"ok": True, "settings": settings})

@app.get("/api/election-data")
@admin_required
def get_election_data_admin():
    return jsonify({"ok": True, "data": ELECTION_DATA})

@app.post("/api/election-data")
@admin_required
def save_election_data_admin():
    global ELECTION_DATA
    data = request.get_json(force=True).get("data")
    if not isinstance(data, dict) or not isinstance(data.get("mayors"), list) or not isinstance(data.get("lists"), dict):
        return jsonify({"ok": False, "error": "Formato non valido: servono mayors[] e lists{}"}), 400
    for list_name, obj in data["lists"].items():
        if not isinstance(obj, dict) or not obj.get("coalition") or not isinstance(obj.get("candidates"), list):
            return jsonify({"ok": False, "error": f"Lista non valida: {list_name}"}), 400
    ELECTION_DATA = data
    conn = db()
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('election_data_json', ?)", (json.dumps(data, ensure_ascii=False),))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "message": "Liste e candidati aggiornati"})

@app.post("/api/reset-votes")
@admin_required
def reset_votes():
    data = request.get_json(force=True)
    confirm = str(data.get("confirm", "")).strip()
    if confirm != "AZZERA":
        return jsonify({"ok": False, "error": "Conferma non valida. Scrivere AZZERA."}), 400
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM votes")
    cur.execute("DELETE FROM reports")
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Voti azzerati"})

@app.get("/api/users")
@admin_required
def users():
    conn = db()
    rows = conn.execute("SELECT id, name, phone, role, section, allowed_lists, qr_token, active FROM users ORDER BY id").fetchall()
    conn.close()
    return jsonify({"ok": True, "users": [dict(row) for row in rows]})

@app.post("/api/users")
@admin_required
def create_user():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    pin = str(data.get("pin", "")).strip()
    section = str(data.get("section", "")).strip() or None
    role = str(data.get("role", "rappresentante")).strip()
    allowed_lists = "|".join(data.get("allowed_lists", []) if isinstance(data.get("allowed_lists", []), list) else [x.strip() for x in str(data.get("allowed_lists", "")).split("|") if x.strip()])
    if not name or not phone or not pin:
        return jsonify({"ok": False, "error": "Nome, telefono/codice e PIN sono obbligatori"}), 400
    conn = db()
    try:
        conn.execute("INSERT INTO users(name, phone, pin_hash, qr_token, role, section, allowed_lists, active, created_at) VALUES(?,?,?,?,?,?,?,1,?)", (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, allowed_lists, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Telefono/codice gia' esistente"}), 409
    conn.close()
    return jsonify({"ok": True})









def _norm(value):
    value = str(value or "").strip().lower()
    value = value.replace("’", "'").replace("`", "'").replace("´", "'")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value

def _tokens(value):
    value = str(value or "").strip().lower()
    value = value.replace("’", "'").replace("`", "'").replace("´", "'")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", value)
    stop = {"detto","detta","di","de","del","della","dei","degli","delle","il","la","lo","le","i","gli","un","una","e","ed","con","per","sindaco","sindaca","lista"}
    return [t for t in tokens if t not in stop and len(t) > 1]

def _contains_flexible(csv_value, app_value):
    ck = _norm(csv_value)
    ak = _norm(app_value)
    if not ck or not ak:
        return False
    if ck == ak or ck in ak or ak in ck:
        return True
    ct = _tokens(csv_value)
    at = _tokens(app_value)
    if not ct or not at:
        return False
    csv_in_app = all(any(c == a or c in a or a in c for a in at) for c in ct)
    app_in_csv = all(any(a == c or a in c or c in a for c in ct) for a in at)
    return csv_in_app or app_in_csv

def _list_alias(key):
    aliases = {
        "movimento2050": "movimento5stelle",
        "movimento5stelle": "movimento5stelle",
        "m5s": "movimento5stelle",
        "pd": "partitodemocratico",
        "partitodemocratico": "partitodemocratico",
        "cittaaperta": "cittaapertacontrocorrente",
        "cittaapertacontrocorrente": "cittaapertacontrocorrente"
    }
    return aliases.get(key, key)

def _resolve_list(raw_name, raw_number=None):
    # Match per Nome Lista: numero lista usato solo se nessun nome combacia.
    raw_key = _list_alias(_norm(raw_name))
    matches = []
    for name in ELECTION_DATA["lists"].keys():
        app_key = _list_alias(_norm(name))
        if app_key == raw_key:
            return name
        if _contains_flexible(raw_name, name):
            matches.append(name)
    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        matches.sort(key=lambda n: len(raw_tokens & set(_tokens(n))), reverse=True)
        return matches[0]
    try:
        n = int(str(raw_number or "").strip())
        lists = list(ELECTION_DATA["lists"].keys())
        if 1 <= n <= len(lists):
            return lists[n-1]
    except Exception:
        pass
    return None

def _resolve_mayor(raw_name, raw_number=None):
    matches = [m for m in ELECTION_DATA["mayors"] if _contains_flexible(raw_name, m)]
    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        matches.sort(key=lambda n: len(raw_tokens & set(_tokens(n))), reverse=True)
        return matches[0]
    try:
        n = int(str(raw_number or "").strip())
        mayors = ELECTION_DATA["mayors"]
        if 1 <= n <= len(mayors):
            return mayors[n-1]
    except Exception:
        pass
    return None

def _resolve_candidate(list_name, raw_name, raw_number=None):
    candidates = ELECTION_DATA["lists"].get(list_name, {}).get("candidates", [])
    if not candidates:
        return None

    matches = []
    for cand in candidates:
        try:
            if _contains_flexible(raw_name, cand):
                matches.append(cand)
        except Exception:
            pass

    if not matches:
        raw_tokens = set(_tokens(raw_name))
        for cand in candidates:
            cand_tokens = set(_tokens(cand))
            if not raw_tokens or not cand_tokens:
                continue
            common = raw_tokens & cand_tokens
            min_required = 1 if min(len(raw_tokens), len(cand_tokens)) <= 1 else 2
            if len(common) >= min_required:
                matches.append(cand)

    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        def _score(cand):
            cand_tokens = set(_tokens(cand))
            common = raw_tokens & cand_tokens
            return (len(common), len(common) / max(len(raw_tokens), 1), -abs(len(cand_tokens) - len(raw_tokens)))
        matches.sort(key=_score, reverse=True)
        return matches[0]

    try:
        n = int(str(raw_number or "").strip())
        if 1 <= n <= len(candidates):
            return candidates[n - 1]
    except Exception:
        pass

    return None

def _ensure_report(cur, section, user_id):
    """
    Garantisce un solo report per sezione/TOTALE.
    Se esiste, aggiorna updated_at e restituisce l'id.
    Se non esiste, crea il report base.
    """
    now = datetime.now().isoformat(timespec="seconds")
    section = str(section or "").strip() or "TOTALE"

    row = cur.execute(
        "SELECT id FROM reports WHERE section=? ORDER BY id DESC LIMIT 1",
        (section,)
    ).fetchone()

    if row:
        cur.execute(
            "UPDATE reports SET user_id=?, updated_at=? WHERE id=?",
            (user_id, now, row["id"])
        )
        return row["id"]

    cur.execute(
        "INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (user_id, section, 0, 0, 0, 0, 0, None, now, now)
    )
    report_id = cur.lastrowid

    for mayor in ELECTION_DATA["mayors"]:
        _upsert_vote(cur, report_id, "sindaco", mayor, 0, None)

    for list_name, obj in ELECTION_DATA["lists"].items():
        _upsert_vote(cur, report_id, "lista", list_name, 0, list_name)
        for cand in obj.get("candidates", []):
            _upsert_vote(cur, report_id, "preferenza", cand, 0, list_name)

    return report_id

def _upsert_vote(cur, report_id, vote_type, name, votes, list_name=None):
    """
    UPDATE dei voti importati via CSV.
    Inserisce solo se il record non esiste.
    """
    votes = int(votes or 0)

    rows = cur.execute(
        """
        SELECT id FROM votes
        WHERE report_id=?
          AND vote_type=?
          AND COALESCE(list_name,'')=COALESCE(?, '')
          AND name=?
        ORDER BY id ASC
        """,
        (report_id, vote_type, list_name, name)
    ).fetchall()

    if rows:
        keep_id = rows[0]["id"]
        cur.execute("UPDATE votes SET votes=? WHERE id=?", (votes, keep_id))

        for duplicate in rows[1:]:
            cur.execute("DELETE FROM votes WHERE id=?", (duplicate["id"],))

        return keep_id

    cur.execute(
        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
        (report_id, vote_type, list_name, name, votes)
    )
    return cur.lastrowid

def _intv(value, default=0):
    """
    Conversione robusta a intero:
    - gestisce None;
    - stringhe vuote;
    - virgole/punti/spazi;
    - ritorna default in caso di errore.
    """
    try:
        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        text = text.replace(".", "").replace(",", ".")

        return int(float(text))
    except Exception:
        return default


def _read_csv_file(max_rows=10000):
    """
    Lettura CSV standardizzata per tutti gli import.
    Separatore obbligatorio: ;
    """
    if "file" not in request.files:
        raise ValueError("File CSV mancante")

    uploaded = request.files["file"]

    raw = uploaded.read()

    if not raw:
        raise ValueError("File CSV vuoto")

    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("File troppo grande (max 5MB)")

    text = raw.decode("utf-8-sig", errors="ignore")

    reader = csv.reader(io.StringIO(text), delimiter=";")

    rows = []

    for row in reader:
        cleaned = [str(x).strip() for x in row]

        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        raise ValueError("CSV senza dati")

    if len(rows) > max_rows:
        raise ValueError(f"CSV troppo grande. Massimo {max_rows} righe")

    # Rimozione automatica intestazione
    first_line = ";".join(rows[0]).lower()

    header_keywords = [
        "sezione",
        "numero liste",
        "nome lista",
        "voti validi",
        "numero sind",
        "candidato sindaco",
        "numero cons",
        "nome cons",
        "schede nulle",
        "schede bianche"
    ]

    if any(k in first_line for k in header_keywords):
        rows = rows[1:]

    return rows


def _import_votes(kind, by_section):
    try:
        rows = _read_csv_file()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Errore lettura CSV: {str(exc)}"}), 400

    admin_user = current_user()
    if not admin_user:
        return jsonify({"ok": False, "error": "Utente amministratore non riconosciuto"}), 401

    conn = db()
    cur = conn.cursor()
    imported = 0
    skipped = 0
    errors = []
    # Per import preferenze totali/per sezione: accumula i voti dei consiglieri per lista
    # per aggiornare anche i voti della lista collegata.
    list_totals_from_preferences = {}

    try:
        for idx, row in enumerate(rows, start=1):
            try:
                if not row or not any(str(x).strip() for x in row):
                    skipped += 1
                    continue

                section = "TOTALE"
                off = 0
                if by_section:
                    if len(row) < 1 or not str(row[0]).strip():
                        raise ValueError("sezione mancante")
                    section = str(row[0]).strip()
                    off = 1

                report_id = _ensure_report(cur, section, admin_user["id"])

                if kind == "liste":
                    if len(row) < off + 3:
                        raise ValueError("formato richiesto: [Sezione;]Numero Liste;Nome Lista;Voti validi")
                    nome_lista = str(row[off + 1]).strip()
                    list_name = _resolve_list(nome_lista, row[off])
                    if not list_name:
                        raise ValueError(f"Nome Lista non trovato in app.py: {nome_lista}")
                    votes = _intv(row[off + 2])
                    _upsert_vote(cur, report_id, "lista", list_name, votes, list_name)
                    imported += 1

                elif kind == "sindaci":
                    if len(row) < off + 4:
                        raise ValueError("formato richiesto: [Sezione;]Numero Sind;Candidato Sindaco;Voti validi;Voti solo Sind")
                    nome_sindaco = str(row[off + 1]).strip()
                    mayor = _resolve_mayor(nome_sindaco, row[off])
                    if not mayor:
                        raise ValueError(f"Candidato Sindaco non trovato in app.py: {nome_sindaco}")
                    votes = _intv(row[off + 2])
                    only = _intv(row[off + 3])
                    _upsert_vote(cur, report_id, "sindaco", mayor, votes + only, None)
                    imported += 1

                elif kind == "consiglieri":
                    if len(row) < off + 5:
                        raise ValueError("formato richiesto: [Sezione;]Numero Liste;Nome Lista;Numero Cons;Nome Cons;Voti validi")
                    nome_lista = str(row[off + 1]).strip()
                    list_name = _resolve_list(nome_lista, row[off])
                    if not list_name:
                        raise ValueError(f"Nome Lista non trovato in app.py: {nome_lista}")
                    nome_cons = str(row[off + 3]).strip()
                    candidate = _resolve_candidate(list_name, nome_cons, row[off + 2])
                    if not candidate:
                        raise ValueError(f"Nome Cons non trovato in app.py per lista {list_name}: {nome_cons}")
                    votes = _intv(row[off + 4])
                    _upsert_vote(cur, report_id, "preferenza", candidate, votes, list_name)
                    list_totals_from_preferences[(report_id, list_name)] = list_totals_from_preferences.get((report_id, list_name), 0) + votes
                    imported += 1

                elif kind == "schede":
                    if len(row) < off + 4:
                        raise ValueError("formato richiesto: [Sezione;]Voti nulli;Schede nulle;Schede bianche;V.cont.NoAss.")
                    voti_nulli = _intv(row[off])
                    schede_nulle = _intv(row[off + 1])
                    schede_bianche = _intv(row[off + 2])
                    v_cont_no_ass = _intv(row[off + 3])
                    now = datetime.now().isoformat(timespec="seconds")
                    cur.execute(
                        "UPDATE reports SET null_ballots=?, blank_ballots=?, updated_at=? WHERE id=?",
                        (voti_nulli + schede_nulle + v_cont_no_ass, schede_bianche, now, report_id)
                    )
                    imported += 1

            except Exception as exc:
                skipped += 1
                if len(errors) < 50:
                    errors.append(f"Riga {idx}: {str(exc)}")

        # Se il file importato contiene preferenze consiglieri, aggiorna anche i voti
        # delle liste collegate. In questo modo i grafici liste/statistiche si aggiornano
        # automaticamente anche caricando solo il CSV delle preferenze.
        if kind == "consiglieri":
            for (report_id, list_name), total_votes in list_totals_from_preferences.items():
                _upsert_vote(cur, report_id, "lista", list_name, total_votes, list_name)

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import {kind}: {str(exc)}"}), 500

    conn.close()
    return jsonify({
        "ok": True,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "message": f"Import completato. Righe assegnate {imported}, righe saltate {skipped}."
    })

@app.post("/api/import/liste")
@admin_required
def import_liste_totali():
    return _import_votes("liste", False)

@app.post("/api/import/liste-sezioni")
@admin_required
def import_liste_sezioni():
    return _import_votes("liste", True)

@app.post("/api/import/sindaci")
@admin_required
def import_sindaci_totali():
    return _import_votes("sindaci", False)

@app.post("/api/import/sindaci-sezioni")
@admin_required
def import_sindaci_sezioni():
    return _import_votes("sindaci", True)

@app.post("/api/import/consiglieri")
@admin_required
def import_consiglieri_totali():
    return _import_votes("consiglieri", False)

@app.post("/api/import/consiglieri-sezioni")
@admin_required
def import_consiglieri_sezioni():
    return _import_votes("consiglieri", True)

@app.post("/api/import/schede")
@admin_required
def import_schede_totali():
    return _import_votes("schede", False)

@app.post("/api/import/schede-sezioni")
@admin_required
def import_schede_sezioni():
    return _import_votes("schede", True)

@app.post("/api/sections/import-csv")
@admin_required
def import_sections_csv():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "File CSV mancante"}), 400

    uploaded_file = request.files["file"]

    try:
        raw = uploaded_file.read()
        if len(raw) > 512 * 1024:
            return jsonify({"ok": False, "error": "File troppo grande. Limite massimo: 512 KB"}), 400
        content = raw.decode("utf-8-sig", errors="ignore")
    except Exception:
        return jsonify({"ok": False, "error": "Impossibile leggere il file CSV"}), 400

    if not content.strip():
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    reader = csv.reader(io.StringIO(content), delimiter=";")
    rows = []
    for row in reader:
        cleaned = [cell.strip() for cell in row]
        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    first = ";".join(rows[0]).lower().replace(" ", "")
    if first.startswith("sezione;") or "elettori" in first or "votanti" in first:
        rows = rows[1:]

    imported = 0
    updated = 0
    skipped = 0
    errors = []
    now = datetime.now().isoformat(timespec="seconds")

    conn = db()
    cur = conn.cursor()
    admin_user = current_user()

    try:
        for idx, row in enumerate(rows, start=1):
            if len(row) < 3:
                skipped += 1
                errors.append(f"Riga {idx}: formato richiesto Sezione;Elettori;Votanti")
                continue

            section = row[0].strip()
            try:
                section_electors = int(str(row[1]).replace(".", "").replace(",", "").strip() or 0)
                voters = int(str(row[2]).replace(".", "").replace(",", "").strip() or 0)
            except ValueError:
                skipped += 1
                errors.append(f"Riga {idx}: elettori o votanti non numerici")
                continue

            if not section:
                skipped += 1
                errors.append(f"Riga {idx}: sezione mancante")
                continue

            existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()

            if existing:
                # Aggiorna solo elettori e votanti, preservando bianche, nulle, voti e stato chiusura.
                cur.execute(
                    "UPDATE reports SET voters=?, contested_ballots=?, updated_at=? WHERE section=?",
                    (voters, section_electors, now, section)
                )
                updated += 1
            else:
                # Crea record base per la sezione. I voti saranno inseriti/aggiornati in seguito.
                cur.execute(
                    "INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (admin_user["id"], section, voters, 0, 0, section_electors, 0, None, now, now)
                )
                report_id = cur.lastrowid

                for name in ELECTION_DATA["mayors"]:
                    cur.execute(
                        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                        (report_id, "sindaco", None, name, 0)
                    )

                for list_name, list_obj in ELECTION_DATA["lists"].items():
                    cur.execute(
                        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                        (report_id, "lista", list_name, list_name, 0)
                    )

                    for candidate in list_obj["candidates"]:
                        cur.execute(
                            "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                            (report_id, "preferenza", list_name, candidate, 0)
                        )

                imported += 1

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import sezioni CSV: {str(exc)}"}), 500

    conn.close()

    return jsonify({
        "ok": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],
        "message": f"Import sezioni completato. Create {imported}, aggiornate {updated}, saltate {skipped}."
    })

@app.post("/api/users/import-csv")
@admin_required
def import_users_csv():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "File CSV mancante"}), 400

    uploaded_file = request.files["file"]

    try:
        raw = uploaded_file.read()
        if len(raw) > 256 * 1024:
            return jsonify({"ok": False, "error": "File troppo grande. Limite massimo: 256 KB"}), 400
        content = raw.decode("utf-8-sig", errors="ignore")
    except Exception:
        return jsonify({"ok": False, "error": "Impossibile leggere il file CSV"}), 400

    if not content.strip():
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    reader = csv.reader(io.StringIO(content), delimiter=";")
    rows = []
    for row in reader:
        cleaned = [cell.strip() for cell in row]
        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    first = ";".join(rows[0]).lower().replace(" ", "")
    if first.startswith("nome;") or "telefono" in first or "codice" in first:
        rows = rows[1:]

    # Batch piccolo per evitare timeout Gunicorn su Render free.
    if len(rows) > 100:
        return jsonify({
            "ok": False,
            "error": "Troppe righe. Import massimo consentito: 100 utenti per volta. Dividi il CSV in piu' file."
        }), 400

    now = datetime.now().isoformat(timespec="seconds")
    imported = 0
    updated = 0
    skipped = 0
    errors = []

    conn = db()
    cur = conn.cursor()

    try:
        existing_rows = cur.execute("SELECT phone FROM users").fetchall()
        existing_phones = {r["phone"] for r in existing_rows}

        # Cache hashing: se piu' utenti hanno stesso PIN, l'hash si calcola una sola volta.
        pin_hash_cache = {}

        for idx, row in enumerate(rows, start=1):
            if len(row) < 3:
                skipped += 1
                errors.append(f"Riga {idx}: campi insufficienti")
                continue

            name = row[0].strip()
            phone = row[1].strip()
            section = row[2].strip() or None
            role = row[3].strip() if len(row) > 3 and row[3].strip() else "rappresentante"
            pin = row[4].strip() if len(row) > 4 and row[4].strip() else "1234"

            if role not in ["admin", "rappresentante"]:
                role = "rappresentante"

            if not name or not phone:
                skipped += 1
                errors.append(f"Riga {idx}: nome o telefono/codice mancante")
                continue

            if pin not in pin_hash_cache:
                pin_hash_cache[pin] = fast_pin_hash(pin)

            pin_hash = pin_hash_cache[pin]

            if phone in existing_phones:
                cur.execute(
                    "UPDATE users SET name=?, section=?, role=?, pin_hash=?, active=1 WHERE phone=?",
                    (name, section, role, pin_hash, phone)
                )
                updated += 1
            else:
                cur.execute(
                    "INSERT INTO users(name, phone, section, role, pin_hash, qr_token, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                    (name, phone, section, role, pin_hash, secrets.token_urlsafe(12), now)
                )
                existing_phones.add(phone)
                imported += 1

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import CSV: {str(exc)}"}), 500

    conn.close()

    return jsonify({
        "ok": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],
        "message": f"Import completato. Importati {imported}, aggiornati {updated}, saltati {skipped}."
    })


@app.patch("/api/users/<int:user_id>")
@admin_required
def update_user(user_id):
    data = request.get_json(force=True)

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    section = str(data.get("section", "")).strip() or None
    role = str(data.get("role", "rappresentante")).strip()
    pin = str(data.get("pin", "")).strip()
    allowed_lists = "|".join(data.get("allowed_lists", []) if isinstance(data.get("allowed_lists", []), list) else [x.strip() for x in str(data.get("allowed_lists", "")).split("|") if x.strip()])

    if not name or not phone:
        return jsonify({"ok": False, "error": "Nome e telefono/codice sono obbligatori"}), 400

    if role not in ["admin", "rappresentante"]:
        return jsonify({"ok": False, "error": "Ruolo non valido"}), 400

    conn = db()
    try:
        if pin:
            conn.execute(
                "UPDATE users SET name=?, phone=?, section=?, role=?, allowed_lists=?, pin_hash=? WHERE id=?",
                (name, phone, section, role, allowed_lists, generate_password_hash(pin), user_id)
            )
        else:
            conn.execute(
                "UPDATE users SET name=?, phone=?, section=?, role=?, allowed_lists=? WHERE id=?",
                (name, phone, section, role, allowed_lists, user_id)
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Telefono/codice gia' esistente"}), 409

    conn.close()
    return jsonify({"ok": True, "message": "Utente aggiornato correttamente"})

@app.delete("/api/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = current_user()
    if user["id"] == user_id:
        return jsonify({"ok": False, "error": "Non puoi rimuovere l'utente attualmente collegato"}), 400
    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.patch("/api/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = current_user()
    if user["id"] == user_id:
        return jsonify({"ok": False, "error": "Non puoi disattivare l'utente attualmente collegato"}), 400
    conn = db()
    row = conn.execute("SELECT active FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Utente non trovato"}), 404
    new_active = 0 if row["active"] else 1
    conn.execute("UPDATE users SET active=? WHERE id=?", (new_active, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "active": new_active})


@app.get("/api/section-details")
@admin_required
def section_details():
    conn = db()
    rows = conn.execute("""
        SELECT r.section, v.vote_type, v.list_name, v.name, v.votes
        FROM reports r
        JOIN votes v ON v.report_id = r.id
        ORDER BY CAST(r.section AS INTEGER), r.section, v.vote_type, v.list_name, v.name
    """).fetchall()
    conn.close()

    result = {}
    for row in rows:
        section = row["section"]
        if section not in result:
            result[section] = {
                "lists": {},
                "mayors": {},
                "preferences": {}
            }

        vote_type = row["vote_type"]
        if vote_type == "lista":
            result[section]["lists"][row["name"]] = row["votes"]
        elif vote_type == "sindaco":
            result[section]["mayors"][row["name"]] = row["votes"]
        elif vote_type == "preferenza":
            list_name = row["list_name"] or ""
            result[section]["preferences"].setdefault(list_name, {})
            result[section]["preferences"][list_name][row["name"]] = row["votes"]

    return jsonify({"ok": True, "sections": result, "data": ELECTION_DATA})

@app.get("/api/export.csv")
@admin_required
def export_csv():
    conn = db()

    # Migrazione di sicurezza nel caso il database SQLite esistente sia stato creato con una versione precedente.
    cur = conn.cursor()
    report_cols = [row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()]
    migrations = {
        "voters": "ALTER TABLE reports ADD COLUMN voters INTEGER NOT NULL DEFAULT 0",
        "blank_ballots": "ALTER TABLE reports ADD COLUMN blank_ballots INTEGER NOT NULL DEFAULT 0",
        "null_ballots": "ALTER TABLE reports ADD COLUMN null_ballots INTEGER NOT NULL DEFAULT 0",
        "contested_ballots": "ALTER TABLE reports ADD COLUMN contested_ballots INTEGER NOT NULL DEFAULT 0",
        "closed": "ALTER TABLE reports ADD COLUMN closed INTEGER NOT NULL DEFAULT 0",
        "closed_at": "ALTER TABLE reports ADD COLUMN closed_at TEXT"
    }
    for col, sql in migrations.items():
        if col not in report_cols:
            cur.execute(sql)
    conn.commit()

    rows = conn.execute("""
        SELECT
            r.section AS section,
            u.name AS representative,
            COALESCE(r.voters, 0) AS voters,
            COALESCE(r.blank_ballots, 0) AS blank_ballots,
            COALESCE(r.null_ballots, 0) AS null_ballots,
            COALESCE(r.contested_ballots, 0) AS contested_ballots,
            COALESCE(r.updated_at, '') AS updated_at,
            v.vote_type AS vote_type,
            COALESCE(v.list_name, '') AS list_name,
            v.name AS name,
            COALESCE(v.votes, 0) AS votes
        FROM reports r
        JOIN users u ON u.id = r.user_id
        JOIN votes v ON v.report_id = r.id
        ORDER BY r.section, v.vote_type, v.list_name, v.name
    """).fetchall()
    conn.close()

    output = io.StringIO()
    output.write("sep=;\n")

    writer = csv.writer(
        output,
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )

    writer.writerow([
        "Sezione",
        "Rappresentante",
        "Votanti",
        "Bianche",
        "Nulle",
        "Elettori",
        "Aggiornato",
        "Tipo",
        "Lista",
        "Nome",
        "Voti",
    ])

    for row in rows:
        writer.writerow([
            row["section"],
            row["representative"],
            row["voters"],
            row["blank_ballots"],
            row["null_ballots"],
            row["contested_ballots"],
            row["updated_at"],
            row["vote_type"],
            row["list_name"],
            row["name"],
            row["votes"],
        ])

    csv_content = "\ufeff" + output.getvalue()

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=report_comunali_barcellona.csv"},
    )

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
