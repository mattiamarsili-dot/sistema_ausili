# Contesto: Dashboard, Pagina Clienti, Pagina Pratiche

Sessione focalizzata sul miglioramento e la pulizia delle pagine principali del Sistema Ausili.

---

## File di riferimento

| File | Righe | Scopo |
|------|-------|-------|
| `app.py` righe 37–139 | ~100 | Route dashboard + clienti + pratiche |
| `database.py` righe 189–320 | ~130 | Funzioni DB per queste pagine |
| `templates/index.html` | 152 | Dashboard |
| `templates/clienti.html` | 166 | Lista clienti |
| `templates/cliente_form.html` | 273 | Dettaglio/modifica cliente |
| `templates/pratiche.html` | 172 | Lista pratiche |
| `templates/pratica_form.html` | 635 | Dettaglio/modifica pratica |

Stack: Flask + Bootstrap 5.3.2 + Bootstrap Icons. Nessun file CSS/JS custom separato.

---

## Dashboard (`/`)

**Route**: `app.py` riga 37–40  
**Template**: `templates/index.html`

```python
def index():
    stats = db.get_statistiche()
    return render_template("index.html", stats=stats)
```

### `db.get_statistiche()` — `database.py` riga 488–505

Ritorna dict con:

| Chiave | Query |
|--------|-------|
| `totale_clienti` | `COUNT(*) FROM clienti WHERE attivo=1` |
| `pratiche_aperte` | `COUNT(*) WHERE stato IN ('Aperta','In corso')` |
| `pratiche_totali` | `COUNT(*) FROM pratiche` |
| `pratiche_per_stato` | `GROUP BY stato → [{stato, n}, ...]` |
| `pratiche_per_tipo` | `GROUP BY tipo_pratica → [{tipo_pratica, n}, ...]` |
| `ultimi_clienti` | `ORDER BY data_inserimento DESC LIMIT 5` |
| `ultime_pratiche` | join clienti, `ORDER BY data_inserimento DESC LIMIT 5` |

### Contenuto attuale `index.html`
- 4 card statistiche (totale clienti, pratiche aperte, pratiche totali, un altro KPI)
- Lista ultimi 5 clienti inseriti
- Lista ultime 5 pratiche con link diretto

### Aree di miglioramento dashboard

- **Grafici aggregati**: `pratiche_per_stato` e `pratiche_per_tipo` già disponibili nel dict — aggiungere Chart.js (CDN) per donut/bar chart
- **KPI importo**: aggiungere `SUM(importo_liquidato)` e `SUM(importo_preventivo)` in `get_statistiche()`
- **Pratiche per ASL**: `GROUP BY asl_competente` join con clienti
- **Pratiche in ritardo**: pratiche con `stato='In corso'` e `data_apertura` > N giorni fa
- **Workflow step mancanti**: pratiche senza `data_prescrizione` o `data_collaudo` valorizzate

---

## Pagina Lista Clienti (`/clienti`)

**Route**: `app.py` riga 45–52  
**Template**: `templates/clienti.html`

```python
def clienti():
    search = request.args.get("q", "").strip()
    vista  = request.args.get("vista", "tabella")
    ordine = request.args.get("ordine", "cognome")
    clienti_list = db.get_all_clienti(search=search or None, ordine=ordine)
    return render_template("clienti.html", clienti=clienti_list,
                           search=search, vista=vista, ordine=ordine)
```

### `db.get_all_clienti(search, ordine)` — `database.py` riga 189–203

- Search LIKE su: `nome`, `cognome`, `codice_fiscale`, `citta`
- Ordini disponibili: `cognome`, `nome`, `asl_competente`, `citta`, `centro`, `data_inserimento`
- Filtra automaticamente `attivo=1`

### Funzionalità attuali `clienti.html`
- Barra ricerca testuale
- Dropdown ordine (6 opzioni)
- Toggle vista tabella / card grid
- Link a modifica e nuova pratica per ogni cliente

### Aree di miglioramento

- **Paginazione**: nessuna — tutti i record vengono caricati. Aggiungere `LIMIT/OFFSET` in DB + controlli pagina nell'HTML
- **Filtri aggiuntivi**: filtrare per ASL, centro, presenza/assenza pratiche
- **Export CSV**: button che scarica la lista corrente filtrata
- **Salvataggio filtri**: `localStorage` per ricordare l'ultimo ordine/vista scelto dall'utente
- **Contatore risultati**: mostrare "N clienti trovati" sotto la barra di ricerca

---

## Pagina Dettaglio Cliente (`/clienti/<id>`)

**Route**: `app.py` riga 64–75  
**Template**: `templates/cliente_form.html` (273 righe, 7 sezioni card)

```python
def modifica_cliente(id):
    cliente = db.get_cliente(id)
    pratiche = db.get_all_pratiche(cliente_id=id)
    return render_template("cliente_form.html", cliente=cliente,
                           pratiche=pratiche, title="Modifica Cliente")
```

### Campi cliente (tabella `clienti`)

**Anagrafica**: `nome`, `cognome`, `codice_fiscale`, `data_nascita`, `luogo_nascita`, `sesso`  
**Residenza**: `indirizzo`, `cap`, `citta`, `provincia`, `anno_residenza`, `telefono`, `email`  
**Clinico/ASL**: `asl_competente`, `centro`, `medico_referente`, `tipo_disabilita`, `grado_invalidita`  
**Documenti**: `doc_tipo`, `doc_numero`, `doc_rilascio`  
**Tutore/Delegato**: `tutore_nome`, `tutore_cognome`, `tutore_telefono`, `tutore_luogo_nascita`, `tutore_data_nascita`, `tutore_provincia_nascita`, `tutore_doc_tipo`, `tutore_doc_numero`, `tutore_doc_rilascio`  
**Altro**: `note`

### Aree di miglioramento

- **Pratiche collegate**: la lista delle pratiche del cliente è già passata ma può essere arricchita con stato badge e link diretto
- **Navigazione rapida**: ancore interne tra le 7 sezioni card (anagrafica, residenza, …)
- **Validazione CF**: validazione codice fiscale lato client prima del submit
- **Auto-fill data_nascita**: da codice fiscale se il CF è valido

---

## Pagina Lista Pratiche (`/pratiche`)

**Route**: `app.py` riga 87–103  
**Template**: `templates/pratiche.html` (172 righe)

```python
def pratiche():
    search = request.args.get("q", "")
    stato  = request.args.get("stato", "")
    centro = request.args.get("centro", "")
    ausilio = request.args.get("ausilio", "")
    ordine = request.args.get("ordine", "data_apertura")
    vista  = request.args.get("vista", "tabella")
    pratiche_list = db.get_all_pratiche(stato=stato or None, search=search or None,
                                        centro=centro or None, ausilio=ausilio or None,
                                        ordine=ordine)
    return render_template("pratiche.html", pratiche=pratiche_list,
                           CENTRI=CENTRI, AUSILII=AUSILII, ...)
```

### `db.get_all_pratiche(...)` — `database.py` riga 253–280

- Join con `clienti` per `nome`, `cognome`, `codice_fiscale`, `telefono`
- Search LIKE su: `numero_pratica`, `cognome` (join), `ausilio_richiesto`
- Filtri exact match: `stato`, `centro`, `ausilio`
- Ordini: `data_apertura DESC` (default), `stato`, `centro`, `ausilio_richiesto`, `c.cognome`

### Liste hardcoded in `app.py` (righe 15–25)

```python
CENTRI  = ["ASL", "CPA", "CTO", "Campus", "Capo Darco", ...]
AUSILII = ["Accessori", "B. esterni", "Bascula su Misura", ...]
```

### Funzionalità attuali `pratiche.html`
- Ricerca testuale
- 4 dropdown filtro: stato, centro, ausilio (+ ordine)
- Toggle tabella / card grid
- Badge colorato per stato pratica

### Aree di miglioramento

- **Paginazione**: stessa situazione dei clienti — nessuna attualmente
- **Vista Kanban**: colonne per stato (Aperta | In corso | In attesa | Completata | Chiusa)
- **Export CSV** della lista filtrata
- **Filtri attivi**: badge visibili che mostrano i filtri applicati con × per rimuoverli
- **Salvataggio filtri in localStorage**: l'utente deve selezionare ogni volta da capo
- **Colonna importi**: mostrare `importo_preventivo` e `importo_liquidato` nella tabella
- **Link al cliente**: nella riga pratica, click sul nome del cliente apre la scheda cliente

---

## Pagina Dettaglio Pratica (`/pratiche/<id>`)

**Route**: `app.py` riga 119–139  
**Template**: `templates/pratica_form.html` (635 righe — la più complessa)

```python
def modifica_pratica(id):
    pratica  = db.get_pratica(id)
    clienti  = db.get_all_clienti()
    cliente  = db.get_cliente(pratica["cliente_id"])
    asl      = cliente["asl_competente"]
    templates = db.get_templates_per_asl(asl)
    # pre-fill medico_prescrittore da cliente.medico_referente se vuoto
    if not pratica.get("medico_prescrittore"):
        pratica["medico_prescrittore"] = cliente.get("medico_referente", "")
    return render_template("pratica_form.html", pratica=pratica,
                           clienti=clienti, templates=templates, ...)
```

### Campi pratica (tabella `pratiche`)

**Core**: `cliente_id`, `stato`, `data_apertura`, `data_chiusura`, `numero_pratica`  
**Provider**: `ente_pubblico`, `centro`, `medico_prescrittore`  
**Ausilio**: `ausilio_richiesto`, `descrizione_ausilio`, `importo_preventivo`, `importo_liquidato`  
**Autorizzazione**: `numero_autorizzazione`, `data_autorizzazione`  
**Workflow (6 step)**: `data_segnalazione`, `data_valutazione`, `data_prescrizione`, `data_ordine`, `data_fornitura`, `data_collaudo`  
**Testo**: `note`, `significato_terapeutico`

### Sezione voci nomenclatore (JS-driven)

Le voci sono in tabella separata `pratica_voci`.  
Il form le gestisce interamente via JavaScript (fetch API):
- `GET /api/voci/<pratica_id>` → lista voci
- `POST /api/voci` → aggiunge voce
- `DELETE /api/voci/<id>` → rimuove voce
- `PUT /api/voci/<id>` → modifica quantità/prezzi

Ogni modifica voci aggiorna automaticamente `pratiche.importo_preventivo` (somma subtotale).

### Sezione template PDF

Mostra card per ogni template disponibile filtrato per ASL del cliente.  
Per tipo `Prescrizione`: apre modal per selezione testo (varianti da `testi_prescrizione.json`).  
Per altri tipi: navigazione diretta a `/compila/<template_id>/<pratica_id>`.

### `db.save_pratica(form_dict, id)` — `database.py` riga 293–320

Genera `numero_pratica` automatico `PR{anno}-{counter:04d}` per le nuove pratiche.

### Aree di miglioramento

- **Timeline visuale dei 6 step**: progress bar orizzontale con i 6 step del workflow; step completati (con data) = verde, mancanti = grigi
- **Auto-save / dirty flag**: avvisare l'utente prima di uscire dalla pagina se ci sono modifiche non salvate (`beforeunload` + dirty tracking)
- **Storico documenti generati**: sotto la sezione PDF, mostrare i PDF già generati per questa pratica (da tabella `documenti_generati`) con link download e data
- **Calcolo durata pratica**: giorni da `data_apertura` a `data_chiusura` (o a oggi se aperta)
- **Completamento automatico campo**: quando viene impostato `stato = 'Completata'`, auto-fill `data_chiusura = oggi`

---

## Schema DB — tabelle coinvolte

```sql
clienti (
  id, nome, cognome, codice_fiscale, data_nascita, luogo_nascita, sesso,
  indirizzo, cap, citta, provincia, telefono, email,
  asl_competente, centro, medico_referente, tipo_disabilita, grado_invalidita,
  doc_tipo, doc_numero, doc_rilascio,
  tutore_nome, tutore_cognome, tutore_telefono, ... (vari campi tutore),
  note, data_inserimento, attivo
)

pratiche (
  id, cliente_id, numero_pratica, stato, tipo_pratica,
  data_apertura, data_chiusura, centro, ente_pubblico, medico_prescrittore,
  ausilio_richiesto, descrizione_ausilio, importo_preventivo, importo_liquidato,
  numero_autorizzazione, data_autorizzazione,
  data_segnalazione, data_valutazione, data_prescrizione,
  data_ordine, data_fornitura, data_collaudo,
  note, significato_terapeutico, data_inserimento
)

pratica_voci (
  id, pratica_id, codice_iso, descrizione, quantita, prezzo_unitario, prezzo_totale
)

documenti_generati (
  id, pratica_id, cliente_id, template_id (nullable FK),
  nome_file, file_path, data_generazione
)
```

---

## Come testare

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# http://localhost:5000/          → dashboard
# http://localhost:5000/clienti   → lista clienti
# http://localhost:5000/pratiche  → lista pratiche
# http://localhost:5000/pratiche/<id>  → dettaglio pratica
```

Verifica dati dashboard da CLI:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
print('Clienti attivi:', conn.execute('SELECT COUNT(*) FROM clienti WHERE attivo=1').fetchone()[0])
print('Pratiche aperte:', conn.execute(\"SELECT COUNT(*) FROM pratiche WHERE stato IN ('Aperta','In corso')\").fetchone()[0])
print('Per stato:')
for r in conn.execute('SELECT stato, COUNT(*) n FROM pratiche GROUP BY stato'): print(' ', dict(r))
conn.close()
"
```
