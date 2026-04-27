# Sistema Ausili — README per sessioni Claude

> Documento di riferimento per avviare sessioni Claude focalizzate su aree specifiche del progetto.
> Leggi questa pagina per capire lo stato attuale, poi apri il file `CLAUDE_*.md` relativo all'area su cui vuoi lavorare.

---

## Cos'è questo progetto

Web app gestionale per **Sapio Life SRL**, tecnici di ausili sanitari.  
Permette di gestire **clienti con disabilità grave**, le relative **pratiche ASL** e generare automaticamente i **documenti PDF** richiesti (preventivi, prescrizioni, deleghe).

**Deploy live**: https://web-production-d6861.up.railway.app  
**GitHub**: mattiamarsili-dot/sistema_ausili  
**Locale**: `/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili/`

---

## Stack tecnico

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python 3, Flask ≥ 3.0 |
| Database | SQLite (WAL mode, busy_timeout 5s) |
| PDF | pypdf ≥ 4.0 (AcroForm) + ReportLab ≥ 4.0 (overlay) |
| Frontend | Bootstrap 5.3.2 + Bootstrap Icons (CDN) — nessun CSS/JS custom |
| Deploy | Railway (Procfile + gunicorn) |
| Sync GitHub | GitHub Desktop (credenziali HTTPS non configurate nel terminale) |

---

## Mappa file

```
sistema_ausili/
├── app.py                  # Flask — 772 righe, 40+ route
├── database.py             # SQLite CRUD — 505 righe
├── pdf_compiler.py         # Compilazione PDF — 557 righe
│
├── config/                 # Mapping JSON per ogni template PDF
│   ├── AM_mapping.json                     # Preventivo Altra Mobilità
│   ├── PRESCCRIZIONE_mapping.json          # Prescrizione Altra Mobilità
│   ├── PrescrizioneSantaLucia_mapping.json # Prescrizione Santa Lucia
│   ├── Delega_Sapio_mapping.json
│   ├── Deleghe_Rm3_mapping.json
│   ├── Delega_RM2_Compilabile_mapping.json
│   ├── testi_prescrizione.json             # Testi standard per tipo ausilio
│   └── nomenclatore_gruppi.json            # Preset voci per categoria ausilio
│
├── data/
│   ├── database.db                         # SQLite — dati produzione
│   ├── pdf_templates/                      # PDF template gestiti dall'app
│   │   ├── AM.pdf                          # Preventivo Altra Mobilità
│   │   ├── Delega_Sapio.pdf
│   │   ├── Delega_RM2_Compilabile.pdf
│   │   └── Deleghe_Rm3.pdf
│   └── output/                             # PDF generati (temporanei)
│
├── templates/              # HTML Flask + alcuni PDF prescrizione
│   ├── base.html           # Layout base Bootstrap
│   ├── index.html          # Dashboard (152 righe)
│   ├── clienti.html        # Lista clienti (166 righe)
│   ├── cliente_form.html   # Form cliente (273 righe)
│   ├── pratiche.html       # Lista pratiche (172 righe)
│   ├── pratica_form.html   # Form pratica (635 righe) ← più complessa
│   ├── templates.html      # Gestione template PDF
│   ├── nomenclatore.html   # Catalogo ausili
│   ├── drive.html          # File manager locale
│   ├── importa.html        # Import dati da file
│   ├── importa_airtable.html
│   ├── testi_prescrizione.html
│   ├── PRESCCRIZIONE.pdf   # Template PDF prescrizione (non cancellare!)
│   └── PrescrizioneSanta lucia.pdf  # (non cancellare!)
│
├── static/                 # Asset statici
│
# --- File di contesto Claude ---
├── README_CLAUDE.md        # ← questo file — panoramica generale
├── CLAUDE.md               # Contesto generale progetto
├── CLAUDE_pdf_compiler.md  # Sessioni su pdf_compiler.py
├── CLAUDE_genera_pdf.md    # Sessioni sulla route /compila e UI generazione PDF
├── CLAUDE_prescrizioni.md  # Sessioni sui template prescrizione (mapping JSON)
├── CLAUDE_ui_design.md     # Sessioni su interfaccia / Bootstrap
├── CLAUDE_pratiche_clienti.md  # Sessioni su DB, query, visualizzazioni dati
└── CLAUDE_dashboard_pages.md   # Sessioni su dashboard, lista/form clienti e pratiche
```

---

## Stato attuale del DB

```
clienti               78 record (attivo=1)
pratiche              70 record
pratica_voci          28 righe voci
pdf_template_mapping   6 template registrati
documenti_generati     log PDF (non mostrati in UI)
nomenclatore_voci      catalogo ausili ISO
```

### Template PDF attivi

| ID | Nome | Tipo | File |
|----|------|------|------|
| 1 | Deleghe_Rm3 | Richiesta ausilio | `data/pdf_templates/Deleghe_Rm3.pdf` |
| 2 | Delega_RM2_Compilabile | Richiesta ausilio | `data/pdf_templates/Delega_RM2_Compilabile.pdf` |
| 3 | Delega_Sapio | Delega | `data/pdf_templates/Delega_Sapio.pdf` |
| 8 | Preventivo Altra Mobilità | Preventivo | `data/pdf_templates/AM.pdf` |
| 10 | Prescrizione Altra Mobilità — Santa Lucia | Prescrizione | `templates/PrescrizioneSanta lucia.pdf` |
| 11 | Prescrizione Altra Mobilità | Prescrizione | `templates/PRESCCRIZIONE.pdf` |

---

## Mappa route principali (`app.py`)

| Route | Funzione | Template |
|-------|----------|----------|
| `GET /` | `index()` | `index.html` |
| `GET/POST /clienti` | `clienti()` | `clienti.html` |
| `GET/POST /clienti/<id>` | `modifica_cliente()` | `cliente_form.html` |
| `GET/POST /pratiche` | `pratiche()` | `pratiche.html` |
| `GET/POST /pratiche/<id>` | `modifica_pratica()` | `pratica_form.html` |
| `GET /templates` | `templates()` | `templates.html` |
| `GET /nomenclatore` | `nomenclatore()` | `nomenclatore.html` |
| `GET/POST /compila/<tid>/<pid>` | `compila_pdf()` | — (download file) |
| `GET /drive` | `drive()` | `drive.html` |
| `GET /importa` | `importa()` | `importa.html` |
| `GET /api/pratica/<id>/voci` | `api_get_voci()` | JSON |
| `POST /api/pratica/<id>/voci` | `api_save_voci()` | JSON |
| `GET /api/nomenclatore/gruppi` | `api_nomenclatore_gruppi()` | JSON |
| `GET /api/testi-prescrizione/varianti` | `api_varianti_testo()` | JSON |
| `GET /api/testi-prescrizione/anteprima` | `api_anteprima_testo()` | JSON |
| `GET /api/inspect/<tid>` | `api_inspect()` | JSON |
| `GET /api/clienti` | `api_clienti()` | JSON |

---

## Flusso generazione PDF

```
pratica_form.html → click "Genera PDF"
  ├── tipo Prescrizione → modal selezione variante testo
  │     └── GET /compila/<tid>/<pid>?significato_custom=...
  └── altri tipi → GET /compila/<tid>/<pid>
                         │
                         ▼
              app.py def compila_pdf()
                ├── db.get_pratica / get_cliente / get_template / get_pratica_voci
                ├── pdf_compiler.compila_pdf(tmpl, dati)
                │     ├── _arricchisci_dati(dati)   # aggiunge campi derivati
                │     ├── _carica_mappatura()        # config/*.json o DB
                │     └── compila_form_pdf() / compila_overlay_pdf()
                ├── db.log_documento(...)
                └── send_file(output, as_attachment=True)
```

---

## File di contesto Claude — quando usarli

| File | Usa quando vuoi lavorare su… |
|------|------------------------------|
| `CLAUDE_pdf_compiler.md` | Logica compilazione PDF, nuovi mapping JSON, font, chiavi derivate |
| `CLAUDE_genera_pdf.md` | Route `/compila`, modal UI prescrizione, API testi, UX download |
| `CLAUDE_prescrizioni.md` | Mapping specifici PRESCCRIZIONE.pdf e PrescrizioneSantaLucia.pdf |
| `CLAUDE_ui_design.md` | Layout Bootstrap, navbar, componenti UI, stile visivo |
| `CLAUDE_pratiche_clienti.md` | Query DB, JOIN, statistiche, visualizzazioni dati |
| `CLAUDE_dashboard_pages.md` | Dashboard KPI, lista clienti/pratiche, filtri, form dettaglio |

**Come usarli**: apri una nuova sessione Claude → allega il file MD → descrivi cosa vuoi fare.

---

## Aree di miglioramento pianificate

### Priorità alta
- [ ] **Paginazione** su lista clienti e lista pratiche (attualmente carica tutto)
- [ ] **Storico documenti generati** visibile nell'UI (tabella `documenti_generati` già loggata ma mai mostrata)
- [ ] **Loading state** sul pulsante "Genera PDF" (nessun feedback visivo durante compilazione)
- [ ] **significato_custom via POST** invece di GET (URL troppo lungo per testi lunghi)

### Priorità media
- [ ] **Grafici dashboard** con Chart.js — `pratiche_per_stato` e `pratiche_per_tipo` già disponibili
- [ ] **Timeline workflow visuale** in pratica_form (6 step: segnalazione→collaudo)
- [ ] **Filtri persistenti** in localStorage per lista pratiche/clienti
- [ ] **Export CSV** lista clienti e pratiche
- [ ] **KPI importi** in dashboard (sum importo_preventivo, importo_liquidato)

### Priorità bassa
- [ ] **Vista Kanban** pratiche per stato
- [ ] **Anteprima PDF inline** (mostrare nel browser invece di scaricare)
- [ ] **Paginazione voci nomenclatore** (se il catalogo cresce molto)
- [ ] **Validazione CF** lato client in cliente_form.html
- [ ] **Auto-fill data_chiusura** quando stato = 'Completata'

---

## Convenzioni di codice

- **Nessun file CSS/JS custom** — tutto via Bootstrap 5.3.2 CDN + Bootstrap Icons CDN
- **Database**: sempre `conn.row_factory = sqlite3.Row` + WAL mode + busy_timeout 5000ms
- **Mapping PDF**: file JSON in `config/` hanno priorità sul campo `mappatura` nel DB
- **Font AcroForm**: default `/Helv 10 Tf 0 g` (Helvetica 10pt ≈ Arial) tramite `_imposta_font_campi()`
- **Output PDF**: sempre in `data/output/{nome_template}_{CF}_{timestamp}.pdf`
- **Template PDF gestiti**: solo quelli in `data/pdf_templates/` vengono cancellati fisicamente; quelli in `templates/` perdono solo il record DB

---

## Come avviare in locale

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# → http://localhost:5000
```

## Come fare deploy

1. Modifiche salvate localmente
2. **GitHub Desktop** → Stage changes → Commit → Push origin
3. Railway deploya automaticamente dal branch main
4. Verifica su https://web-production-d6861.up.railway.app

> ⚠️ Non usare `git push` da terminale — credenziali HTTPS non configurate. Usare GitHub Desktop.

---

## Verifica rapida DB da terminale

```bash
sqlite3 "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili/data/database.db" "
SELECT 'clienti', COUNT(*) FROM clienti WHERE attivo=1
UNION ALL SELECT 'pratiche', COUNT(*) FROM pratiche
UNION ALL SELECT 'voci', COUNT(*) FROM pratica_voci
UNION ALL SELECT 'template', COUNT(*) FROM pdf_template_mapping;
"
```
