# Contesto: Moduli Prescrizione Altra Mobilità

Sessione focalizzata sui **due template prescrizione per Altra Mobilità**.
Progetto: Flask + SQLite in `/Cloude code Lavoro/sistema_ausili/`

---

## I due template

### 1. PRESCCRIZIONE.pdf (prescrizione generica)
- **File PDF**: `templates/PRESCCRIZIONE.pdf`
- **Mapping**: `config/PRESCCRIZIONE_mapping.json`
- **DB id**: 11 — nome: "Prescrizione Altra Mobilità"
- **Pagine**: 2
- **Struttura**:
  - Pag.1: dati paziente + tabella 15 righe voci (codice ISO, descrizione LEA, quantità)
  - Pag.2: 6 righe Significato Terapeutico (`Signf. Terapeutico.0.0` … `.5.0`)

**Campi dati paziente:**
| Campo PDF | Dato |
|---|---|
| `Cognome` | `cliente.cognome` |
| `Nome` | `cliente.nome` |
| `C.F` | `cliente.codice_fiscale` |
| `Data Nascita` | `cliente.data_nascita` |
| `Luogo Nasc` | `cliente.luogo_nascita` |
| `Telefono` | `cliente.telefono` |
| `Resid. via` | `cliente.indirizzo` |
| `Comune Res` | `cliente.citta` |
| `Provinc` | `cliente.provincia` |
| `Patologia` | `cliente.tipo_disabilita` |

**Campi voci (15 righe, 0–14):**
- Riga 0: `Cod. ISO.0.0.0.0`, `Descrizione LEA.0.0`, `Q.tà.0.0`
- Righe 1–13: `Cod. ISO.N.0`, `Descrizione LEA.N.0`, `Q.tà.N.0`
- Riga 14: `Cod. ISO.0.0.1.0`, `Descrizione LEA.14.0`, `Q.tà.14.0`

---

### 2. PrescrizioneSanta lucia.pdf (Santa Lucia)
- **File PDF**: `templates/PrescrizioneSanta lucia.pdf`
- **Mapping**: `config/PrescrizioneSantaLucia_mapping.json`
- **DB id**: 10 — nome: "Prescrizione Altra Mobilità — Santa Lucia"
- **Pagine**: 2
- **Struttura**:
  - Pag.1: dati paziente + tabella 15 righe voci (codici ISO, descrizione, quantità)
  - Pag.2: campo `Diagnosi` + 5 righe Significato Terapeutico (`Sign. Terap.0.0` … `.4.0`)

**Campi dati paziente:**
| Campo PDF | Dato |
|---|---|
| `Cognome` | `cliente.cognome` |
| `Nome` | `cliente.nome` |
| `CF` | `cliente.codice_fiscale` |
| `Data Nascita` | `cliente.data_nascita` |
| `Luogo Nascita` | `cliente.luogo_nascita` |
| `Telef` | `cliente.telefono` |
| `Via res` | `cliente.indirizzo` |
| `Comun` | `cliente.citta` |
| `Prov` | `cliente.provincia` |
| `Diagnosi` | `cliente.tipo_disabilita` |

**Campi voci (15 righe, 0–14):**
- Tutte le righe consistenti: `Codici ISO.N.0`, `Descrizione. ISO.N.0`, `Q.tà.N.0`

---

## Motore di compilazione — pdf_compiler.py

**Entry point**: `compila_pdf(template_record, dati)` in `pdf_compiler.py`

**Funzione usata**: `compila_form_pdf(pdf_path, mappatura, dati, output_path)`
- Tipo mapping: `"_tipo": "form"`
- Prima di compilare chiama `_imposta_font_campi(writer, "/Helv 10 Tf 0 g")` → Helvetica 10pt su tutti i campi
- Poi `update_page_form_field_values(page, field_values, auto_regenerate=True)` su tutte le pagine

**Campi disponibili da `_arricchisci_dati()`** (chiamata automaticamente):
- `cliente.cognome`, `cliente.nome`, `cliente.codice_fiscale`, `cliente.data_nascita` (→ gg/mm/aaaa)
- `cliente.luogo_nascita`, `cliente.indirizzo`, `cliente.citta`, `cliente.provincia`, `cliente.telefono`
- `cliente.tipo_disabilita`, `cliente.asl_competente`, `cliente.centro`
- `voci_N_codice`, `voci_N_descrizione`, `voci_N_quantita` (N = 0–15)
- `significato_riga_N` (N = 0–5) — testi da `config/testi_prescrizione.json` se configurati
- `data_oggi` (gg/mm/aaaa)

---

## Come testare localmente

```python
import pdf_compiler as pdf_mod, json

dati = {
    'cliente': {
        'nome': 'Mario', 'cognome': 'Rossi',
        'codice_fiscale': 'RSSMRA80A01H501Z',
        'data_nascita': '1980-01-01', 'luogo_nascita': 'Roma',
        'indirizzo': 'Via Roma 1', 'citta': 'Milano', 'provincia': 'MI',
        'telefono': '3391234567', 'tipo_disabilita': 'Esiti frattura',
    },
    'pratica': {'ausilio_richiesto': 'Deambulatore'},
    'voci': [
        {'codice_iso': '12.06.03.036', 'descrizione': 'Deambulatore 4 ruote', 'quantita': 1,
         'prezzo_unitario': 250.0, 'prezzo_totale': 250.0},
    ]
}

dati = pdf_mod._arricchisci_dati(dati)
# Aggiunta manuale significato (normalmente da testi_prescrizione.json)
dati['significato_riga_0'] = 'Il dispositivo supporta la deambulazione in sicurezza.'

# Test PRESCCRIZIONE
with open('config/PRESCCRIZIONE_mapping.json', encoding='utf-8') as f:
    campi = json.load(f)['campi']
pdf_mod.compila_form_pdf('templates/PRESCCRIZIONE.pdf', campi, dati, '/tmp/test_prescr.pdf')

# Test Santa Lucia
with open('config/PrescrizioneSantaLucia_mapping.json', encoding='utf-8') as f:
    campi = json.load(f)['campi']
pdf_mod.compila_form_pdf('templates/PrescrizioneSanta lucia.pdf', campi, dati, '/tmp/test_sl.pdf')
```

---

## Stato attuale e problemi noti

- ✅ Mapping completo per entrambi i template
- ✅ Font Helvetica 10pt forzato su tutti i campi
- ⚠️ I testi `significato_riga_N` si compilano automaticamente solo se la categoria ausilio è in `config/testi_prescrizione.json` — per "Altra Mobilità" non è ancora configurata
- ⚠️ Il campo `Patologia` / `Diagnosi` usa `cliente.tipo_disabilita` — verificare che sia popolato nelle pratiche

## File da modificare in questa sessione
- `config/PRESCCRIZIONE_mapping.json`
- `config/PrescrizioneSantaLucia_mapping.json`
- `config/testi_prescrizione.json` (se si aggiungono testi predefiniti)
- `pdf_compiler.py` (solo se serve modificare la logica di compilazione)
