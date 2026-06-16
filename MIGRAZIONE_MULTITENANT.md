# Migrazione dalla versione monotenente alla versione multitenant

La vecchia applicazione usava dati globali: utenti, anagrafiche, voti e configurazioni erano condivisi.

La nuova versione crea automaticamente un tenant demo chiamato `platform-demo` e associa a esso i vecchi record privi di `tenant_id`.

## Cosa cambia

| Prima | Dopo |
|---|---|
| Database globale | Database logicamente separato per tenant |
| Admin non isolati | Ogni admin appartiene a un tenant |
| Impostazioni globali | `tenant_settings` per organizzazione |
| Moduli globali | `tenant_modules` + `admin_module_permissions` |
| Dashboard unica | Dashboard filtrata per tenant |
| Nessuna API pubblica | API `/api/v1` con Bearer token |
| AI dimostrativa | AI con regressione, clustering, proiezione e anomalie |

## Verifiche dopo il deploy

1. Login come SuperAdmin: `super / 0000`.
2. Creare un nuovo tenant oppure un nuovo admin: se manca il tenant viene creato automaticamente.
3. Accedere come admin e caricare anagrafiche elettorali.
4. Inserire dati di sezione.
5. Aprire `Political Intelligence AI`.
6. Generare una API key e testare `/api/v1/results`.

## Nota sui dati

La separazione è applicativa e database-level tramite `tenant_id`. In produzione enterprise si può evolvere verso:

- schema PostgreSQL per tenant;
- database separato per tenant;
- crittografia per tenant;
- retention policy separata.
