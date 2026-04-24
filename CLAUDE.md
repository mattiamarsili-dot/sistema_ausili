# Sistema Ausili — Contesto progetto

App Flask + SQLite deployata su Railway (https://web-production-d6861.up.railway.app).
GitHub: mattiamarsili-dot/sistema_ausili

## Stack
- `app.py` — Flask, 40+ route
- `database.py` — SQLite con WAL mode abilitato (`PRAGMA journal_mode = WAL`)
- `pdf_compiler.py` — compilazione PDF (pypdf + reportlab)
- `config/` — mapping JSON per ogni template PDF
- `data/pdf_templates/` — template PDF gestiti dall'app
- `templates/` — HTML Flask + alcuni PDF prescrizione (non cancellare i PDF qui)

---

## Modulo PDF — pdf_compiler.py

### Funzioni principali

**`compila_pdf(template_record, dati)`** — entry point chiamato da app.py  
**`_arricchisci_dati(dati)`** — aggiunge campi derivati prima della compilazione  
**`compila_form_pdf(pdf_path, mappatura, dati, output_path)`** — compila AcroForm  
**`compila_overlay_pdf(...)`** — overlay ReportLab su PDF statico  
**`compila_preventivo_pdf(...)`** — preventivo con tabella dinamica ReportLab  
**`_imposta_font_campi(writer, da_string)`** — forza font su tutti i campi AcroForm  

### Campi derivati da `_arricchisci_dati()`
| Chiave | Valore |
|---|---|
| `cliente.cognome_nome` | "Cognome Nome" |
| `cliente.citta_cap` | "Città CAP" |
| `cliente.data_nascita` | formattata gg/mm/aaaa |
| `asl_competente` | top-level copia di cliente.asl_competente |
| `data_oggi` | gg/mm/aaaa |
| `data_oggi_ddmm` | ddmm (es. "2304") |
| `voci_N_codice` | codice ISO riga N (0-15) |
| `voci_N_descrizione` | descrizione riga N |
| `voci_N_quantita` | quantità formattata |
| `voci_N_prezzo_unitario` | "€ X.XXX,XX" |
| `voci_N_prezzo_totale` | "€ X.XXX,XX" |
| `subtotale` | somma prezzi totali |
| `iva_importo` | 4% del subtotale |
| `totale_finale` | subtotale + IVA |
| `significato_riga_N` | testo prescrizione riga N (da testi_prescrizione.json) |

### Strategie di compilazione (campo `_tipo` nel mapping JSON)
- `"form"` — AcroForm con campi nominati (usa `compila_form_pdf`)
- `"overlay"` — coordinate x/y su PDF statico (usa `compila_overlay_pdf`)
- `"preventivo_tabella"` — tabella dinamica ReportLab (usa `compila_preventivo_pdf`)

### Font AcroForm
`_imposta_font_campi(writer, "/Helv 10 Tf 0 g")` — forza Helvetica 10pt (≈ Arial) su tutti i campi prima della compilazione. Modificare il numero per cambiare dimensione.

---

## Template PDF registrati nel DB (pdf_template_mapping)

| ID | Nome | Tipo | File |
|---|---|---|---|
| 3 | Delega_Sapio | Delega | data/pdf_templates/Delega_Sapio.pdf |
| 8 | **Preventivo Altra Mobilità** | Preventivo | data/pdf_templates/AM.pdf |
| 10 | **Prescrizione Altra Mobilità — Santa Lucia** | Prescrizione | templates/PrescrizioneSanta lucia.pdf |
| 11 | **Prescrizione Altra Mobilità** | Prescrizione | templates/PRESCCRIZIONE.pdf |

### Config mapping JSON (in `config/`)
- `AM_mapping.json` — preventivo AcroForm 16 righe voci (AM.pdf)
- `PRESCCRIZIONE_mapping.json` — prescrizione 15 righe (PRESCCRIZIONE.pdf)
- `PrescrizioneSantaLucia_mapping.json` — prescrizione Santa Lucia 15 righe
- `Delega_Sapio_mapping.json` — delega 2 pagine AcroForm
- `Prescrizione_Cloude_mapping.json` — prescrizione generica (template rimosso dal DB)

### Struttura mapping JSON
```json
{
  "_tipo": "form",
  "_note": "commento descrittivo",
  "campi": {
    "NomeCampoPDF": "chiave.in.dati"
  }
}
```

### Campi speciali AM.pdf (Preventivo Altra Mobilità)
- `Text1` → cognome_nome, `Text2` → luogo_nascita, `Text3` → citta_cap
- `Text4` → indirizzo, `Text5` → data_nascita, `Text6` → centro, `Text7` → telefono
- Prima riga descrizione voci: `Descr. ISO.0.0.1.0` (non `Descr. ISO.0.0.0.0`)
- Righe 4-14 descrizione: `Descr. ISO.4.0.X.0` (X = 0..10)
- Riga 15 descrizione: `Descr. ISO.0.0.0.0`

---

## DB — tabelle chiave
- `clienti` — include: centro, asl_competente, tipo_disabilita, medico_referente
- `pratiche` — include: ausilio_richiesto, medico_prescrittore, centro
- `pratica_voci` — codice_iso, descrizione, quantita, prezzo_unitario, prezzo_totale
- `pdf_template_mapping` — nome_template, file_path, tipo_documento, mappatura (JSON)
- `documenti_generati` — log PDF generati, template_id nullable

## Eliminazione template
La route `/templates/<id>/elimina` cancella il file fisico **solo** se è in `data/pdf_templates/`. Template in `templates/` perdono solo il record DB.

## Deploy
Push su GitHub → Railway deploya automaticamente.
Credenziali GitHub non configurate nel terminale: usare GitHub Desktop → Push origin.
