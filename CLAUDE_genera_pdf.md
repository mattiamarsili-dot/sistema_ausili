# Contesto: Generazione PDF dalla Pratica

Sessione focalizzata sul flusso di generazione PDF: dalla UI della pagina pratica
alla route Flask, fino alla compilazione e download del file.

---

## Flusso completo attuale

```
pratica_form.html
  └── card template → click "Genera PDF"
        ├── tipo Prescrizione → apriModalVariante() → modal selezione testo
        │     └── compilaGeneraPDF() → GET /compila/{template_id}/{pratica_id}?significato_custom=...
        └── altri tipi → GET /compila/{template_id}/{pratica_id} diretto
                              │
                              ▼
                    app.py — def compila_pdf()
                      ├── db.get_pratica(pratica_id)
                      ├── db.get_cliente(...)
                      ├── db.get_template(template_id)
                      ├── db.get_pratica_voci(pratica_id)
                      ├── pdf_mod.compila_pdf(tmpl, dati)
                      ├── db.log_documento(...)
                      └── send_file(output_path, as_attachment=True)
```

---

## Route Flask — app.py

```python
@app.route("/compila/<int:template_id>/<int:pratica_id>", methods=["GET", "POST"])
def compila_pdf(template_id, pratica_id):
    pratica  = db.get_pratica(pratica_id)
    cliente  = db.get_cliente(pratica["cliente_id"])
    tmpl     = db.get_template(template_id)
    voci     = db.get_pratica_voci(pratica_id)

    dati = {
        "cliente":            cliente,
        "pratica":            pratica,
        "voci":               voci,
        "data_oggi":          today.strftime("%d/%m/%Y"),
        "variante_testo":     request.args.getlist("variante"),
        "significato_custom": request.form.get("significato_custom", "")
                              or request.args.get("significato_custom", ""),
    }

    output_path = pdf_mod.compila_pdf(tmpl, dati)  # → pdf_compiler.py
    db.log_documento({...})
    return send_file(output_path, as_attachment=True, ...)
```

**File**: `app.py` righe 413–445

**Nota**: `significato_custom` arriva sia da GET (query param) che da POST (form hidden).
Attualmente viene usato quasi sempre via GET → URL potenzialmente lunghissimo.

---

## UI in pratica_form.html

### Sezione "Genera documento PDF" (solo in modalità modifica)
- Mostrata solo se `pratica.id` esiste e ci sono template disponibili
- Template filtrati per ASL del cliente via `get_templates_per_asl(asl)` in `database.py`
- Una card per ogni template con: nome, tipo, descrizione, pulsante "Genera PDF"

### Logica pulsante per tipo template
```javascript
// Template tipo "Prescrizione" → apre modal per selezione testo
apriModalVariante(templateId, ausilio, praticaId)

// Template altri tipi → navigazione diretta
window.location.href = `/compila/${templateId}/${praticaId}`
```

**Problema attuale**: il codice HTML usa una condizione hardcoded (controlla `t.tipo_documento`)
che andrebbe resa più robusta.

### Modal selezione variante testo (per Prescrizione)
```
1. Apertura modal
2. fetch GET /api/testi-prescrizione/varianti?ausilio={ausilio_richiesto}
3. Mostra checkbox varianti disponibili
4. Al check: fetch GET /api/testi-prescrizione/anteprima?ausilio=...&variante=...
             → popola textarea "significatoCustom"
5. Click "Genera PDF": GET /compila/{id}/{id}?significato_custom={testo}
   oppure: GET /compila/{id}/{id}?variante=X&variante=Y
```

**File**: `templates/pratica_form.html` righe 229–313 (HTML) + 517–603 (JS)

---

## Campo significato_terapeutico in pratiche

La tabella `pratiche` ha il campo `significato_terapeutico TEXT` (aggiunto di recente).
Il form pratica_form.html ha una textarea che lo salva con il resto della pratica.

In `pdf_compiler.py → _arricchisci_dati()`:
```python
sig = (dati.get("pratica") or {}).get("significato_terapeutico", "") or ""
sig = sig.strip() or dati.get("significato_custom", "").strip()
if sig:
    _espandi_testo(dati, "significato_riga", sig, 6, 118)
    return dati
# fallback → testi_prescrizione.json per ausilio_richiesto
```

Priorità risoluzione testo: `significato_terapeutico` (salvato) → `significato_custom` (URL) → `testi_prescrizione.json`

---

## API di supporto

```python
GET /api/testi-prescrizione/varianti?ausilio={nome}
# → lista nomi varianti disponibili per quell'ausilio

GET /api/testi-prescrizione/anteprima?ausilio={nome}&variante={v1}&variante={v2}
# → {"testo": "testo unito delle varianti selezionate"}
```

---

## Log documenti generati

Ogni PDF compilato viene loggato in `documenti_generati`:
```sql
INSERT INTO documenti_generati
  (pratica_id, cliente_id, template_id, nome_file, file_path)
VALUES (?, ?, ?, ?, ?)
```
**Attualmente**: il log c'è ma i documenti generati **non sono mostrati da nessuna parte nell'UI**.

---

## Problemi noti / aree da migliorare

### UX
- [ ] **Nessun loading state**: il click "Genera PDF" non mostra nessun feedback
      mentre il server compila — l'utente non sa se sta succedendo qualcosa
- [ ] **significato_custom in GET**: testo lungo in URL → può causare errori su testi molto lunghi.
      Meglio passare via POST (form hidden già esiste: `formCompilaCustom`)
- [ ] **Nessuna lista storico PDF**: i documenti generati sono loggati nel DB ma mai mostrati.
      Utile mostrare sotto la sezione template: "Documenti generati per questa pratica"
- [ ] **Modal solo per Prescrizione**: la logica che apre il modal vs naviga diretto
      è hardcoded su `tipo_documento == 'Prescrizione'` — andrebbe basata su un flag nel template

### Funzionalità
- [ ] **Anteprima inline** prima del download: mostrare il PDF nel browser invece di scaricarlo
- [ ] **Rigenerazione documento**: link rapido per rigenerare l'ultimo PDF prodotto per una pratica
- [ ] **Selezione multipla template**: genera più documenti in una volta (preventivo + prescrizione)

---

## File da modificare in questa sessione

| File | Sezione |
|---|---|
| `app.py` righe 413–445 | Route `compila_pdf` |
| `templates/pratica_form.html` righe 229–313 | Card template + modal |
| `templates/pratica_form.html` righe 517–603 | JS compilazione |
| `database.py` | Eventuale nuova funzione `get_documenti_pratica(id)` |

---

## Come testare

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# http://localhost:5000/pratiche/<id>   (pratica con voci e template configurati)
```

Verifica log documenti generati:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
rows = conn.execute('''
    SELECT dg.id, dg.nome_file, dg.data_generazione,
           t.nome_template, c.cognome, p.numero_pratica
    FROM documenti_generati dg
    LEFT JOIN pdf_template_mapping t ON dg.template_id = t.id
    LEFT JOIN clienti c ON dg.cliente_id = c.id
    LEFT JOIN pratiche p ON dg.pratica_id = p.id
    ORDER BY dg.id DESC LIMIT 10
''').fetchall()
for r in rows: print(r)
conn.close()
"
```
