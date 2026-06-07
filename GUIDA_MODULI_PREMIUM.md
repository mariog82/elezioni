# Guida operativa ai moduli premium della Political Intelligence Platform

## 1. Prerequisito obbligatorio: anagrafica elettorale

La piattaforma parte volutamente senza sindaci, liste, coalizioni e consiglieri. Questo evita che grafici, dashboard e simulazioni vengano alimentati da dati dimostrativi.

Ordine di caricamento consigliato:

1. **Importazione prioritaria sindaci**  
   CSV con separatore `;`:

   ```csv
   Numero Sindaco;Candidato Sindaco
   1;NOME CANDIDATO SINDACO
   2;ALTRO CANDIDATO SINDACO
   ```

2. **Importazione prioritaria liste/coalizioni/consiglieri**  
   CSV con separatore `;`:

   ```csv
   Numero Lista;Nome Lista;Coalizione;Numero Candidato;Nome Candidato
   1;LISTA CIVICA UNO;NOME CANDIDATO SINDACO;1;NOME CANDIDATO CONSIGLIERE
   1;LISTA CIVICA UNO;NOME CANDIDATO SINDACO;2;ALTRO CANDIDATO CONSIGLIERE
   ```

3. Solo dopo caricare o inserire:
   - voti sindaci;
   - voti liste;
   - preferenze consiglieri;
   - voti per sezione;
   - schede bianche/nulle;
   - voto disgiunto.

Senza anagrafica completa l'app blocca l'inserimento voti e avvisa l'utente.

---

## 2. Blockchain Electoral Audit

### Cosa fa

Il modulo trasforma ogni report/sezione in un payload JSON ordinato, calcola un hash SHA-256 e collega ogni blocco al precedente. Il risultato è una catena dimostrativa interna con:

- sezione;
- data di aggiornamento;
- rappresentante;
- hash del dato;
- hash del blocco precedente;
- hash del blocco corrente.

Serve a dimostrare che un verbale non è stato alterato dopo la certificazione.

### Come si usa nell'app

1. L'admin attiva il modulo da **Gestione moduli**.
2. Va in **Blockchain Electoral Audit**.
3. Clicca **Aggiorna audit**.
4. Controlla la catena generata.
5. In una versione production-ready, l'ultimo hash o gli hash per sezione vengono ancorati su blockchain.

### Implementazione in produzione su Polygon, Base, Arbitrum o Ethereum

Architettura consigliata:

1. Backend Flask genera `audit_hash`:
   - JSON canonico ordinato;
   - SHA-256;
   - salvataggio su tabella `audit_anchors`.
2. Smart contract Solidity minimale:
   - funzione `anchor(bytes32 hash, string metadataURI)`;
   - evento `AuditAnchored(hash, metadataURI, timestamp)`;
   - mapping hash → timestamp/ente.
3. Upload del verbale completo su IPFS/Arweave/S3 immutabile.
4. Scrittura on-chain solo dell'hash e dell'URI.
5. Frontend mostra:
   - hash locale;
   - transaction hash;
   - link explorer;
   - stato verificato/non verificato.

Reti consigliate:

- **Polygon**: costi bassi, ecosistema maturo.
- **Base**: adatta a UX Web3 moderna e costi contenuti.
- **Arbitrum**: buona per scalabilità Ethereum L2.
- **Ethereum mainnet**: massima sicurezza, costi più alti.

Dipendenze Python possibili:

```txt
web3
python-dotenv
eth-account
```

Variabili ambiente:

```env
CHAIN_RPC_URL=https://...
ANCHOR_CONTRACT_ADDRESS=0x...
ANCHOR_PRIVATE_KEY=...
CHAIN_EXPLORER_URL=https://...
```

### Implementazione con Hyperledger

Hyperledger è preferibile se il progetto è usato da enti, partiti, osservatori o associazioni con permessi controllati.

Architettura:

- rete permissioned;
- canali per consultazione/elezione;
- chaincode per salvare hash verbali;
- identità rilasciate da una CA;
- accesso solo a nodi autorizzati.

Differenza principale: Polygon/Base/Arbitrum/Ethereum sono pubbliche; Hyperledger è una blockchain privata/consortile.

---

## 3. DAO civica

### Cosa fa

La DAO civica permette di trasformare la piattaforma in un sistema di governance partecipativa:

- proposte civiche;
- priorità di quartiere;
- bilancio partecipativo;
- consultazioni interne;
- monitoraggio del programma amministrativo.

### Implementazione consigliata

Fase 1, senza blockchain:

- tabella `dao_proposals`;
- tabella `dao_votes`;
- ruoli: cittadino verificato, osservatore, moderatore, admin;
- votazione semplice o ponderata.

Fase 2, con blockchain:

- token reputazionale non speculativo;
- voto firmato da wallet;
- snapshot degli aventi diritto;
- hash della proposta e dei risultati ancorato on-chain.

Il token deve essere presentato come reputazionale/civico, non come strumento finanziario.

---

## 4. Gamification NFT elettorali

### Cosa fa

Genera badge digitali per milestone:

- sezione certificata;
- osservatore civico;
- 100% sezioni acquisite;
- partecipazione DAO;
- contributore verificato.

### Implementazione production

1. Creare metadati JSON del badge.
2. Salvare immagine e metadati su IPFS.
3. Mint NFT su smart contract ERC-721 o ERC-1155.
4. Collegare wallet utente o wallet istituzionale.
5. Mostrare badge in dashboard pubblica.

Per ridurre complessità, si può partire da badge off-chain e passare agli NFT solo nella versione enterprise.

---

## 5. Modulo investigativo / OSINT politico

### Cosa fa

Il modulo OSINT non deve sostituire indagini ufficiali. Serve a leggere segnali pubblici e aggregati:

- concentrazioni anomale di preferenze;
- sezioni con voto disgiunto elevato;
- reti candidato-sezione-lista;
- reputazione pubblica;
- trend social;
- rassegna stampa;
- open data elettorali.

### Implementazione funzionale

Fonti integrabili:

- albo pretorio;
- delibere e determine;
- open data comunali/regionali;
- risultati elettorali storici;
- articoli di stampa;
- pagine social pubbliche tramite API ufficiali;
- comunicati e programmi pubblici.

Pipeline:

1. Raccolta fonti lecite.
2. Normalizzazione nomi candidati/liste.
3. Estrazione entità: persone, luoghi, organizzazioni.
4. Sentiment e topic analysis.
5. Creazione grafo relazionale.
6. Alert con livello: basso, attenzione, alto.
7. Scheda candidato/lista.

Tecnologie consigliate:

- Python `pandas`, `networkx`, `spacy`;
- PostgreSQL + pgvector per ricerca semantica;
- Neo4j per grafi relazionali;
- Celery per job periodici;
- API social ufficiali, non scraping invasivo.

Vincoli:

- usare solo dati leciti;
- evitare profilazione illegittima;
- documentare la fonte;
- mantenere audit log delle analisi.

---

## 6. Modulo Social & Viral

### Cosa fa

Trasforma dati aggregati in contenuti condivisibili:

- dashboard pubblica;
- card candidato/lista;
- Political Score;
- ranking territoriali;
- link pubblici;
- QR code;
- embed per sito o giornale locale.

### Implementazione

1. API pubblica `/api/public-dashboard` con dati aggregati.
2. Pagine pubbliche senza dati personali degli operatori.
3. Generazione card HTML/immagine.
4. QR code verso dashboard pubblica.
5. Export PNG/PDF delle card.
6. Condivisione WhatsApp/Telegram/Facebook/X.

Political Score suggerito:

- voti assoluti;
- crescita rispetto a sezioni già acquisite;
- efficienza preferenze;
- peso nella lista;
- presenza territoriale;
- capacità di traino.

---

## 7. Political Intelligence Platform

### Cosa fa

È il cuore premium della piattaforma. Usa i dati caricati per produrre analisi avanzate:

- heatmap territoriale consenso;
- analisi reti clientelari/body politico;
- predizione elettorale AI-like;
- peso politico reale.

### Come farlo funzionare

Prerequisiti:

1. anagrafica sindaci/liste/coalizioni/consiglieri caricata;
2. sezioni o report inseriti;
3. voti sindaco/lista/preferenze disponibili;
4. voto disgiunto opzionale ma consigliato;
5. numero elettori/votanti aggiornato nella quadratura.

### Evoluzione AI reale

L'attuale versione produce indicatori euristici. Per una vera AI:

1. raccogliere storico elettorale per sezione;
2. creare dataset con affluenza, lista, candidato, quartiere, storico, trend;
3. addestrare modelli:
   - Random Forest / XGBoost per previsione voti;
   - regressione per turnout;
   - clustering per aree omogenee;
   - graph analytics per reti territoriali.
4. salvare modello con `joblib`;
5. servire previsioni tramite endpoint Flask;
6. mostrare confidenza e margine di errore.

Metriche utili:

- voto candidato / voto lista;
- preferenze candidato / preferenze totali lista;
- dominanza per sezione;
- concentrazione territoriale;
- scostamento rispetto alla media;
- indice di traino;
- indice di dipendenza dalla lista;
- rischio voto disperso.

---

## 8. Moduli indipendenti e vendita SaaS

Ogni modulo può essere attivato/disattivato dall'admin in **Gestione moduli**. Questo permette offerte commerciali modulari:

- Base: inserimento voti + import CSV;
- Pro: grafici + Political Score;
- Premium: Intelligence + simulatore;
- Trust: Blockchain Electoral Audit;
- Enterprise: OSINT + DAO + NFT + API pubbliche.
