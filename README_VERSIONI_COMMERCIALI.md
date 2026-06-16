# Versioni commerciali SuperAdmin

La piattaforma contiene una nuova sezione SuperAdmin dedicata alla vendita SaaS dell'applicazione.

## Versioni previste

### 1. Political Intelligence Platform START
- Prezzo stimato: 149 €/mese, 1.490 €/anno, setup 490 €.
- Target: liste civiche, piccoli comitati, singoli candidati.
- Moduli: dashboard social/base e funzioni operative di rilevazione.
- Valore: sostituisce WhatsApp, Excel e telefonate durante lo scrutinio.

### 2. Political Intelligence Platform PRO
- Prezzo stimato: 399 €/mese, 3.990 €/anno, setup 990 €.
- Target: coalizioni, candidati sindaco strutturati, comitati con più liste.
- Moduli: Political Intelligence AI, Dashboard Social, Electoral Audit, Simulatore predittivo, API pubbliche.
- Valore: trasforma la raccolta dei voti in analisi strategica e supporto decisionale.

### 3. Political Intelligence Platform ENTERPRISE
- Prezzo stimato: 990 €/mese, 9.900 €/anno, setup 2.500 €.
- Target: partiti, federazioni provinciali/regionali, grandi organizzazioni politiche.
- Moduli: tutti i moduli, incluso OSINT politico.
- Valore: consente di gestire molti territori, molte campagne e grandi volumi di dati/API.

## Comportamento implementato

- Il SuperAdmin visualizza le tre versioni commerciali.
- Durante la creazione di un Admin è possibile scegliere il piano commerciale.
- La creazione dell'Admin crea automaticamente anche il tenant/cliente.
- L'applicazione abilita automaticamente i moduli previsti dal piano.
- Il SuperAdmin può cambiare piano a un tenant già esistente.
- Il cambio piano aggiorna scadenza e moduli tenant.
- Gli Admin vedono solo i moduli previsti dal piano e assegnati al loro profilo.

## Endpoint aggiunti

- `GET /api/super/sales-versions`
- `POST /api/super/sales-versions/<plan_key>`
- `POST /api/super/tenants/<tenant_id>/plan`

