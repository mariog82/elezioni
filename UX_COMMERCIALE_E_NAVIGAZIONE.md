# Political Intelligence Platform - Layout UX consigliato per la vendita

## Obiettivo
Rendere l'applicazione percepita come uno strumento indispensabile per campagne elettorali, liste civiche, partiti e organizzazioni politiche: rapida, semplice, controllabile e immediatamente utile.

## Layout consigliato

### 1. Navigazione orizzontale persistente
Una horizontal bar in alto deve rimanere visibile nelle aree principali. Il SuperAdmin vede: Versioni, Tenant, Moduli, Nuovo admin, Admin, Pagamenti, Aggiorna, Esci. L'Admin vede: Dashboard, Import, Utenti, Grafici, Dashboard pubblica, Rilevazione.

### 2. Dashboard con priorità operative
La prima schermata deve mostrare solo ciò che serve subito:
- stato scrutinio;
- sezioni ricevute;
- quadratura;
- alert errori;
- moduli premium disponibili;
- scadenza piano.

### 3. Vendibilità dei piani
I piani devono motivare l'upgrade:
- START: raccolta dati e dashboard essenziale;
- PRO: intelligence, simulatori, social dashboard e analisi avanzate;
- ENTERPRISE: API, audit, OSINT, blockchain audit, multi-territorio, supporto e personalizzazioni.

### 4. Pagamenti
Sono stati aggiunti: Carta di Credito, Stripe, PayPal, Nexi, Satispay, PagoPA, Apple Pay, Google Pay, SEPA, Bonifico e Link di pagamento. Per la vendita reale si consiglia Stripe/Nexi per carta e abbonamenti, PayPal per clienti piccoli, bonifico/SEPA per contratti enterprise.

### 5. UX funzionale
- Pochi pulsanti principali per schermata.
- Messaggi chiari: “Errore quadratura”, “Dati salvati”, “Piano scaduto”.
- Colori: rosso scuro/bordeaux per identità politica istituzionale, bianco per leggibilità, grigio per neutralità dati.
- Card commerciali con prezzo, benefici e moduli inclusi.
- Tabelle leggibili con ricerca e filtri nelle versioni successive.

## Evoluzione consigliata
- Wizard onboarding tenant in 4 step: piano, dati organizzazione, admin, pagamento.
- Checkout integrato con carta di credito.
- CRM leggero nel SuperAdmin: lead, preventivi, contratti, scadenze.
- Trial di 14 giorni con upgrade guidato.
- Tour iniziale dell'Admin dopo il primo accesso.
