# Contesto: Modulo pdf_compiler.py

Sessione focalizzata sul modulo di compilazione PDF del progetto Sistema Ausili (Flask+SQLite su Railway).

---

## File di riferimento

| File | Scopo |
|------|-------|
| `pdf_compiler.py` | Modulo principale (558 righe) |
| `config/*_mapping.json` | Mapping campi per ogni template |
| `app.py` righe 413–445 | Route `/compila/<template_id>/<pratica_id>` |
| `data/pdf_templates/` | Template PDF gestiti dall'app |
| `templates/` | Contiene anche alcuni PDF prescrizione |

---

## Architettura — 3 strategie di compilazione

### 1. `form` — AcroForm (pypdf)
Per PDF con campi modulo nominati. Entry: `compila_form_pdf()`.
- Legge il mapping `"campi": {"NomeCampoPDF": "chiave.dati"}`
- Forza font su tutti i campi con `_imposta_font_campi()`
- Chiama `update_page_form_field_values(..., auto_regenerate=True)`

### 2. `overlay` — Testo su PDF statico (ReportLab)
Per PDF senza campi modulo. Entry: `compila_overlay_pdf()`.
- Il mapping `"campi"` è una lista di dict `{pagina, x, y, chiave_dati, font, font_size}`
- Crea un canvas ReportLab per ogni pagina, vi disegna il testo, lo fonde col PDF originale

### 3. `preventivo_tabella` — Tabella dinamica legacy (ReportLab)
Per il vecchio `MODELLO_PREVENTIVI_2026`. Entry: `compila_preventivo_pdf()`.
- Coordinate hardcoded nel codice (righe 401–463)
- **Attualmente inutilizzato** — tutti i preventivi usano ora `form` o `overlay`

---

## Funzioni — mappa completa

### `_fmt_euro(val)` — riga 31
```python
_fmt_euro(1234.5) → "€ 1.234,50"
```

### `_arricchisci_dati(dati)` — riga 35
Aggiunge campi derivati al dict `dati` prima della compilazione.
Input: dict con chiavi `cliente`, `pratica`, `voci`, `variante_testo`, `significato_custom`.
Output: stesso dict con chiavi aggiuntive (vedi sezione **Chiavi derivate** sotto).

### `_espandi_testo(dati, prefisso, testo, max_righe, max_chars)` — riga 185
Split testo lungo in righe. Rispetta `\n` espliciti, poi spezza per lunghezza.
```python
_espandi_testo(dati, "significato_riga", "testo lungo...", 6, 135)
# → dati["significato_riga_0"] = "prima riga"
#    dati["significato_riga_1"] = "seconda riga"
#    dati["significato_riga_2..5"] = ""
```

### `_get_field_value(field_key, dati)` — riga 208
Resolver dot-notation su dict annidato.
```python
_get_field_value("cliente.cognome", dati)  # → "Rossi"
_get_field_value("pratica.data_apertura", dati)  # → "15/04/2026" (ISO → gg/mm/aaaa)
```
Auto-formatta stringhe ISO date `YYYY-MM-DD` → `dd/MM/YYYY`.

### `get_pdf_form_fields(pdf_path)` — riga 232
Restituisce lista dict `{nome_campo, tipo, valore_default}`.
Usata per ispezionare un PDF prima di scrivere il mapping.

### `_imposta_font_campi(writer, da_string, overrides)` — riga 253
Imposta il Default Appearance (`/DA`) su **tutti** i campi AcroForm ricorsivamente.
```python
_imposta_font_campi(writer, "/Helv 10 Tf 0 g", overrides={"Sign. Terap": "/Helv 8 Tf 0 g"})
```
- `da_string` default: `/Helv 10 Tf 0 g` (Helvetica ≈ Arial, 10pt)
- `overrides`: dict `{sottostringa_nome_campo: da_string}` per campi con font diverso
- Match per **substring** del nome campo (case-sensitive)

### `compila_form_pdf(pdf_path, mappatura, dati, output_path, font_overrides)` — riga 285
Strategia AcroForm. Sequenza:
1. `PdfReader` + `PdfWriter`
2. `_imposta_font_campi(writer, overrides=font_overrides)`
3. Costruisce `field_values` dal mapping (salta chiavi che iniziano con `_`)
4. `update_page_form_field_values` su ogni pagina con `auto_regenerate=True`
5. Scrive file in `data/output/`

### `compila_overlay_pdf(pdf_path, overlay_config, dati, output_path)` — riga 321
Strategia overlay ReportLab. Per ogni pagina crea canvas, disegna stringhe alle coordinate, fonde con `page.merge_page()`.

### `compila_preventivo_pdf(pdf_path, dati, output_path)` — riga 371
Strategia legacy con coordinate hardcoded (usata per MODELLO_PREVENTIVI_2026 — ora non più in produzione).

### `_carica_mappatura(template_record)` — riga 477
Risolve la mappatura in ordine di priorità:
1. `config/{nome_template}_mapping.json` (priorità — file on disk)
2. Campo `mappatura` (JSON) nel record DB

### `compila_pdf(template_record, dati)` — riga 495 (**entry point**)
Chiamato da `app.py`. Sequenza:
1. `_arricchisci_dati(dati)`
2. `_carica_mappatura(template_record)` → legge `_tipo`
3. Costruisce nome output: `{nome_template}_{CF}_{timestamp}.pdf`
4. Dispatch al metodo corretto per `_tipo`
5. Se mapping ha `_overlay` → applica overlay aggiuntivo ReportLab sul PDF già compilato

### `inspect_pdf(pdf_path)` — riga 536
```python
inspect_pdf("data/pdf_templates/AM.pdf")
# → {"tipo": "form", "pagine": 2, "campi_modulo": [{nome_campo, tipo, valore_default}, ...]}
```

---

## Chiavi derivate da `_arricchisci_dati()`

```
# Cliente
cliente.cognome_nome        — "Cognome Nome"
cliente.citta_cap           — "Città CAP"
cliente.nascita_gg          — "15"
cliente.nascita_mm          — "04"
cliente.nascita_aaaa        — "2026"
cliente.doc_tipo_numero     — "Carta d'identità   AB1234567"
cliente.tutore_doc_tipo_numero
cliente.doc_rilascio        — gg/mm/aaaa (formattata da ISO)
cliente.tutore_doc_rilascio — gg/mm/aaaa
cliente.tutore_data_nascita — gg/mm/aaaa

# Azienda
nome_azienda                — "SAPIO LIFE SRL"

# Pratica
pratica.medico_prescrittore — auto-fill da cliente.medico_referente se vuoto
pratica.codice_am           — "AM" + data_autorizzazione in ddmm.aa
asl_competente              — copia top-level di cliente.asl_competente

# Date
data_oggi                   — gg/mm/aaaa
data_oggi_ddmm              — ddmm (es. "2304")

# Voci nomenclatore (N = 0..15)
voci_N_codice
voci_N_descrizione
voci_N_quantita             — senza decimali inutili ("1" non "1.0")
voci_N_prezzo_unitario      — "€ X.XXX,XX" (vuoto se 0)
voci_N_prezzo_totale        — "€ X.XXX,XX" (vuoto se 0)

# Totali
subtotale                   — somma prezzi_totale voci
iva_importo                 — subtotale × 4%
totale_finale               — subtotale + iva_importo

# Significato terapeutico (split in righe)
significato_riga_N          — N=0..5

# Testi prescrizione da testi_prescrizione.json
modi_riga_N                 — N=0..5
controindicazioni_riga_N    — N=0..1
```

**Priorità testo significato** (in `_arricchisci_dati`):
1. `pratica.significato_terapeutico` (campo salvato nel DB)
2. `significato_custom` (query param dal GET o form POST)
3. `testi_prescrizione.json` per `ausilio_richiesto` + `variante_testo`

---

## Formato mapping JSON

```json
{
  "_tipo": "form",
  "_note": "descrizione umana (ignorato dal codice)",
  "_font_overrides": {
    "sottostringa_nome_campo": "/Helv 8 Tf 0 g"
  },
  "_overlay": [],
  "campi": {
    "NomeCampoPDF": "chiave.dati"
  }
}
```

**Chiavi speciali** (ignorate dal compilatore):
- Qualsiasi chiave che inizia con `_` in `campi` viene saltata
- Valore `"_"` viene saltato

**Risoluzione mappatura** (`_carica_mappatura`):
1. `config/{nome_template}_mapping.json` se esiste
2. Campo `mappatura` JSON nel record DB (`pdf_template_mapping.mappatura`)

---

## Template attivi in produzione

| Nome DB | File | Tipo | Mapping |
|---------|------|------|---------|
| Preventivo Altra Mobilità | `data/pdf_templates/AM.pdf` | `form` | `config/AM_mapping.json` |
| Prescrizione Altra Mobilità | `templates/PRESCCRIZIONE.pdf` | `form` | `config/PRESCCRIZIONE_mapping.json` |
| Prescrizione Altra Mobilità — Santa Lucia | `templates/PrescrizioneSanta lucia.pdf` | `form` | `config/PrescrizioneSantaLucia_mapping.json` |
| Delega_Sapio | `data/pdf_templates/Delega_Sapio.pdf` | `form` | `config/Delega_Sapio_mapping.json` |

---

## Font system — dettaglio

Il Default Appearance (`/DA`) di un campo AcroForm controlla il font usato quando il PDF reader renderizza il testo compilato.

```
/Helv 10 Tf 0 g
  │     │   │ └── colore testo (0 = nero)
  │     │   └──── operatore color
  │     └──────── dimensione in punti
  └────────────── font name (Helv = Helvetica/Arial)
```

`_imposta_font_campi()` sovrascrive il `/DA` di ogni campo prima di riempirlo.  
Senza questo, `auto_regenerate=True` userebbe il font originale del PDF (spesso troppo piccolo o errato).

**Override per campo**:
```json
"_font_overrides": {
  "Signf. Terapeutico": "/Helv 8 Tf 0 g",
  "Sign. Terap":        "/Helv 8 Tf 0 g"
}
```
Match per **substring** del nome campo — basta che la sottostringa compaia nel nome completo del campo PDF.

---

## Note sui campi AcroForm con nomi complessi

pypdf usa dot-notation gerarchica per i campi con parent/kids. Esempio da AM.pdf:
```
Descr. ISO.0.0.1.0   ← prima riga (attenzione: non .0.0.0.0!)
Descr. ISO.1.0       ← righe 1-3
Descr. ISO.2.0
Descr. ISO.3.0
Descr. ISO.4.0.0.0   ← righe 4-14 (con quarto livello)
...
Descr. ISO.4.0.10.0
Descr. ISO.0.0.0.0   ← ultima riga (riga 15)
```
Quando si ispezione un nuovo PDF e i nomi sembrano incoerenti, è normale — deriva dalla struttura AcroForm padre/figlio del PDF originale.

---

## Come testare

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# http://localhost:5000/pratiche/<id> → click "Genera PDF"
# Verifica il file generato in data/output/
```

Ispezione campi di un nuovo PDF:
```python
from pdf_compiler import inspect_pdf
import json
result = inspect_pdf("data/pdf_templates/NUOVO.pdf")
for campo in result["campi_modulo"]:
    print(campo["nome_campo"], "—", campo["tipo"])
```

Compilazione di test senza avviare Flask:
```python
import sqlite3, json
from pdf_compiler import compila_pdf

conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row
tmpl = dict(conn.execute("SELECT * FROM pdf_template_mapping WHERE id=8").fetchone())
pratica = dict(conn.execute("SELECT * FROM pratiche WHERE id=1").fetchone())
cliente = dict(conn.execute("SELECT * FROM clienti WHERE id=?", (pratica["cliente_id"],)).fetchone())
voci = [dict(r) for r in conn.execute("SELECT * FROM pratica_voci WHERE pratica_id=1").fetchall()]
conn.close()

dati = {"cliente": cliente, "pratica": pratica, "voci": voci}
out = compila_pdf(tmpl, dati)
print("Generato:", out)
```
