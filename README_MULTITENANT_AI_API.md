# Focus360 Political Intelligence - Multitenant AI/API Edition

Questa versione supera i limiti della precedente webapp elettorale introducendo un modello SaaS multitenant reale.

## Credenziali iniziali

- SuperAdmin: `super`
- PIN: `0000`
- Admin demo: `admin`
- PIN: `1234`

## Novità principali

### 1. Multitenancy reale

Ogni organizzazione politica è un tenant autonomo. Le tabelle operative includono `tenant_id`:

- `users`
- `reports`
- `votes`
- `tenant_settings`
- `tenant_modules`
- `api_keys`
- `audit_log`

Questo impedisce a un admin di leggere o modificare dati di un altro tenant. Il SuperAdmin può invece creare tenant, admin, moduli e API key.

### 2. SuperAdmin stile Focus360AI

Il SuperAdmin può:

- creare organizzazioni/tenant;
- creare admin associati al tenant;
- assegnare moduli premium per admin;
- gestire scadenze, piano e stato del tenant;
- configurare pagamenti;
- generare API key pubbliche per il tenant.

### 3. API pubbliche versionate

Le API pubbliche sono sotto `/api/v1` e usano autenticazione Bearer.

Esempio:

```bash
curl -H "Authorization: Bearer fp_xxx" http://localhost:5000/api/v1/results
```

Endpoint disponibili:

- `GET /api/v1/tenant`
- `GET /api/v1/results`
- `GET /api/v1/ai/predictions`
- `POST /api/v1/reports` con scope `write`

Le API key si generano da SuperAdmin con:

```http
POST /api/super/api-keys
```

Body:

```json
{
  "tenant_id": 1,
  "name": "Dashboard esterna",
  "scopes": "read,write"
}
```

### 4. Moduli AI realmente implementati

Il nuovo backend introduce:

- proiezione Bayes/Laplace dei voti;
- regressione lineare sull'affluenza per sezione;
- clustering territoriale con KMeans;
- anomaly detection su invalidità/affluenza;
- indice di peso politico dei candidati;
- predizione del leader con livello di confidenza.

Endpoint principali:

- `GET /api/intelligence`
- `GET /api/ai/predictive`
- `GET /api/v1/ai/predictions`

### 5. Audit tenant-aware

Ogni azione importante viene registrata in `audit_log`. Il modulo blockchain genera una hash-chain interna tenant-aware:

```http
GET /api/blockchain
```

## Scalabilità

Per passare da demo a produzione:

1. usare PostgreSQL al posto di SQLite;
2. configurare HTTPS e reverse proxy;
3. abilitare rate limiting sulle API;
4. usare variabili d'ambiente per segreti e chiavi pagamento;
5. separare worker web e worker AI;
6. creare backup automatici per tenant.

## Deploy Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Variabili consigliate:

```env
APP_SECRET_KEY=valore-lungo-casuale
DATABASE_SQLITE_PATH=/opt/render/project/src/database.sqlite
STRIPE_PUBLIC_KEY=...
STRIPE_SECRET_KEY=...
```
