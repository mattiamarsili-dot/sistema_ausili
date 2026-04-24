# Contesto: Visualizzazioni Pratiche & Clienti

Sessione focalizzata su nuove viste, filtri avanzati e interconnessione dati
nelle pagine `/pratiche` e `/clienti` del progetto Flask+SQLite.

---

## Stato attuale

### Pagina `/pratiche`
**Filtri esistenti:** ricerca testo (numero_pratica, cognome, ausilio), stato, centro, ausilio, ordinamento
**Dati mostrati in tabella:** numero_pratica, cliente, stato, centro, ausilio, ASL, data_apertura
**Dati mostrati in card mobile:** + telefono

**Dati disponibili ma NON mostrati:**
- `importo_preventivo`, `importo_liquidato` — economia pratica
- `tipo_pratica` — Valutazione/Fornitura/Assistenza/Riparazione/Collaudo
- `medico_prescrittore`, `numero_autorizzazione`
- `data_chiusura`, `data_autorizzazione`, `data_fornitura`, `data_collaudo`
- `data_segnalazione`, `data_valutazione`, `data_prescrizione`, `data_ordine`
- `codice_fiscale` cliente (già in JOIN ma non mostrato)

### Pagina `/clienti`
**Filtri esistenti:** ricerca testo (nome, cognome, cf, città), ordinamento
**Dati mostrati:** cognome+nome, codice_fiscale, città+provincia, telefono, ASL, centro

**Dati disponibili ma NON mostrati:**
- `tipo_disabilita`, `grado_invalidita`, `medico_referente`
- `data_nascita`, `sesso`, `luogo_nascita`
- `data_inserimento` (data di aggiunta al sistema)
- N° pratiche collegate (da JOIN) — **non calcolato né mostrato**
- Stato pratiche collegate — **nessun collegamento visivo**

---

## Schema DB — tabelle principali

### clienti
```
id, nome, cognome, codice_fiscale, data_nascita, luogo_nascita, sesso
indirizzo, cap, citta, provincia, anno_residenza
telefono, email, medico_referente, asl_competente, centro
tipo_disabilita, grado_invalidita
tutore_cognome, tutore_nome, tutore_cognome_nome, tutore_telefono
tutore_luogo_nascita, tutore_data_nascita, tutore_provincia_nascita
tutore_doc_tipo, tutore_doc_numero, tutore_doc_rilascio
doc_tipo, doc_numero, doc_rilascio
note, data_inserimento, attivo (0/1)
```

### pratiche
```
id, numero_pratica, cliente_id (FK→clienti), tipo_pratica, stato
data_apertura, data_chiusura
ente_pubblico (=ASL), ufficio_protesi, medico_prescrittore
ausilio_richiesto, codice_ausilio, descrizione_ausilio
importo_preventivo (REAL), importo_liquidato (REAL)
numero_autorizzazione, data_autorizzazione
data_fornitura, data_collaudo
data_segnalazione, data_valutazione, data_prescrizione, data_ordine
centro, note, data_inserimento
```

### pratica_voci
```
id, pratica_id (FK→pratiche CASCADE), codice_iso
descrizione, quantita, prezzo_unitario, prezzo_totale, ordinamento
```

### nomenclatore_voci
```
id, codice_iso, descrizione, prezzo_unitario, iva_perc, nota, attivo
```

### documenti_generati
```
id, pratica_id (FK→pratiche), cliente_id, preventivo_id, template_id
nome_file, file_path, data_generazione, note
```

---

## JOIN disponibili

| Join | SQL | Utilità |
|---|---|---|
| pratiche → clienti | `p.cliente_id = c.id` | già in uso — dati cliente in lista pratiche |
| pratiche → pratica_voci | `pv.pratica_id = p.id` | voci/importi per pratica |
| pratica_voci → nomenclatore_voci | `pv.codice_iso = nv.codice_iso` | arricchire voci con metadati nomenclatore |
| clienti → pratiche (COUNT) | `COUNT(p.id) GROUP BY c.id` | numero pratiche per cliente |
| pratiche → documenti_generati | `dg.pratica_id = p.id` | PDF generati per pratica |

---

## Funzioni DB da modificare/estendere

**`database.py`:**

```python
# Esistenti
get_all_clienti(search=None, ordine="cognome")       # nessun JOIN pratiche
get_all_pratiche(cliente_id, stato, search, centro, ausilio, ordine)
get_pratica(id)          # JOIN clienti
get_pratica_voci(id)     # solo pratica_voci

# Da aggiungere / estendere
get_all_clienti(...)     # + COUNT pratiche per cliente, + stato ultima pratica
get_all_pratiche(...)    # + filtro data_apertura range, + filtro tipo_pratica
                         # + importo_preventivo, + somma voci
get_stats_dashboard()    # aggregati per grafici e KPI
```

---

## Route da modificare/aggiungere

**`app.py`:**

```python
# Esistenti
GET /clienti              # passa: clienti, search, vista, ordine
GET /pratiche             # passa: pratiche, search, stato, centro, ausilio, ordine, vista

# Da estendere
GET /clienti              # + filtro ASL, + filtro centro, + filtro ha_pratiche
GET /pratiche             # + filtro tipo_pratica, + filtro data_da/data_a
                          # + filtro importo_min/importo_max

# Nuove API JSON per grafici/dati aggregati
GET /api/stats/pratiche   # conteggi per stato, ausilio, centro, mese
GET /api/stats/clienti    # distribuzione ASL, centro, tipo_disabilita
```

---

## Costanti hardcoded (usarle nei select e filtri)

```python
# app.py
CENTRI_LIST = [
    "ASL","CPA","CTO","Campus","Capo Darco","Gemelli","HBG",
    "Nemo","PTV","PUPrimo","Sabelli","Santa Lucia","Sant'Andrea","VillaFulvia","Wildm"
]
AUSILII_LIST = [
    "Accessori","B. esterni","Bascula su Misura","Basculante Posturale","Bici",
    "Deambulatore","Elettronica","Leggera","Materasso","Montascale","Moveon",
    "Passeggino posturale","Postura Pediatrica","Postura Tronco","Propulsore",
    "Sectional Body","Sedia WX","Statica","Super leggera"
]
STATI_PRATICA = ["Aperta","In corso","In attesa","Completata","Chiusa"]
TIPI_PRATICA  = ["Valutazione","Fornitura","Assistenza","Riparazione","Collaudo"]
ASL_LIST = ["RM1","RM2","RM3","RM4","RM5","RM6","FR","VT","Altro"]
```

---

## Visualizzazioni da implementare

### Pagina `/pratiche`

**Filtri aggiuntivi:**
- Filtro `tipo_pratica` (Valutazione/Fornitura/ecc.)
- Filtro data apertura: `data_da` e `data_a` (input date range)
- Filtro presenza importo (con/senza preventivo)

**Colonne aggiuntive (toggle):**
- `importo_preventivo` / `importo_liquidato` (con € e colore se liquidato > 0)
- `tipo_pratica` (badge)
- Timeline avanzamento (barra progressiva sulle 6 fasi)

**Vista Kanban (per stato):**
- 5 colonne: Aperta | In corso | In attesa | Completata | Chiusa
- Card draggabili per cambiare stato (fetch PATCH)
- Contatore pratiche per colonna

**Vista Timeline:**
- Ordinata per data_apertura
- Mostra la fase attiva di ciascuna pratica (quale data è compilata per ultima)

**KPI sopra la lista:**
- N° pratiche aperte, totale importi preventivati, totale liquidati, pratiche senza data fornitura

### Pagina `/clienti`

**Filtri aggiuntivi:**
- Filtro `asl_competente` (select)
- Filtro `centro` (select)
- Filtro `ha_pratiche` (sì/no)
- Filtro `tipo_disabilita` (testo)

**Colonne aggiuntive:**
- N° pratiche per cliente (COUNT via JOIN)
- Stato ultima pratica (badge)
- Data ultima apertura pratica

**Vista espansa (accordion/dettaglio inline):**
- Click su riga → espande dati clinici, tutore, pratiche collegate
- Evita il doppio click per aprire il form completo

**KPI sopra la lista:**
- N° clienti attivi, distribuzione per ASL, distribuzione per centro

---

## Interconnessione tra pagine

**Navigazione incrociata da implementare:**
- Da lista clienti → click cliente → lista pratiche filtrata per quel cliente (già esiste tramite `/pratiche?cliente_id=X` ma non esposto in UI)
- Da lista pratiche → click cliente → scheda cliente
- Da pratica → link diretto a tutti i PDF generati per quella pratica
- Da cliente → totale importi preventivati + liquidati su tutte le pratiche

**Widget "pratiche attive" nella scheda cliente:**
- Attualmente le pratiche collegate al cliente sono mostrate in `cliente_form.html` come tabella semplice
- Da arricchire con: stato (badge), importo_preventivo, link diretto alla pratica

---

## Come testare localmente

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# http://localhost:5000/pratiche
# http://localhost:5000/clienti
```

Query di test diretto sul DB:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
# Esempio: clienti con conteggio pratiche
rows = conn.execute('''
    SELECT c.cognome, c.nome, c.asl_competente,
           COUNT(p.id) as n_pratiche,
           MAX(p.stato) as ultimo_stato
    FROM clienti c
    LEFT JOIN pratiche p ON p.cliente_id = c.id
    WHERE c.attivo = 1
    GROUP BY c.id
    ORDER BY n_pratiche DESC LIMIT 10
''').fetchall()
for r in rows: print(r)
conn.close()
"
```

---

## Priorità suggerite per questa sessione

1. **Filtri aggiuntivi** pratiche (tipo_pratica, date range) — modifica `database.py` + route + HTML
2. **Colonna N° pratiche** in lista clienti — JOIN COUNT in `get_all_clienti()`
3. **KPI pratiche** sopra la lista (aperte, importi totali) — query aggregata in route
4. **Vista Kanban** pratiche per stato — nuova vista HTML + JS drag & drop
5. **Accordion clienti** con dettaglio inline — JS toggle + fetch dati pratiche
