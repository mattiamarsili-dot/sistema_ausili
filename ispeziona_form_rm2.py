"""
Stampa i nomi esatti dei campi AcroForm del PDF compilabile RM2.
Esegui dopo aver installato Python:
  python3 ispeziona_form_rm2.py

L'output aggiorna il file config/Delega_RM2_Compilabile_mapping.json
"""
import json, os
from pypdf import PdfReader

PDF = os.path.join(os.path.dirname(__file__),
                   "data", "pdf_templates", "Delega_RM2_Compilabile.pdf")

CONFIG = os.path.join(os.path.dirname(__file__),
                      "config", "Delega_RM2_Compilabile_mapping.json")

MAPPA_SUGGERITA = {
    "nome":            "cliente.cognome_nome",
    "cognome":         "cliente.cognome_nome",
    "sottoscritto":    "cliente.cognome_nome",
    "nato_a":          "cliente.luogo_nascita",
    "luogo_nascita":   "cliente.luogo_nascita",
    "data_nascita":    "cliente.data_nascita",
    "il":              "cliente.data_nascita",
    "nato_il":         "cliente.data_nascita",
    "via":             "cliente.indirizzo",
    "indirizzo":       "cliente.indirizzo",
    "citta":           "cliente.citta",
    "città":           "cliente.citta",
    "ausilio":         "pratica.ausilio_richiesto",
    "ausili":          "pratica.ausilio_richiesto",
    "data":            "data_oggi",
    "roma":            "data_oggi",
    "doc_tipo":        "cliente.doc_tipo",
    "tipo_doc":        "cliente.doc_tipo",
    "n":               "cliente.doc_numero",
    "numero":          "cliente.doc_numero",
    "rilasciato_a":    "cliente.citta",
    "doc_data":        "cliente.doc_rilascio",
    "cod_fiscale":     "cliente.codice_fiscale",
    "cf":              "cliente.codice_fiscale",
    "codice_fiscale":  "cliente.codice_fiscale",
    "telefono":        "cliente.telefono",
    "medico":          "pratica.medico_prescrittore",
    "struttura":       "pratica.medico_prescrittore",
    "prescrizione":    "pratica.data_autorizzazione",
    "luogo_data":      "data_oggi",
}

reader = PdfReader(PDF)
fields = reader.get_fields() or {}

print(f"\n{'='*60}")
print(f"PDF: {os.path.basename(PDF)}")
print(f"Campi trovati: {len(fields)}")
print(f"{'='*60}\n")

nuova_mappatura = {}
for name, field in fields.items():
    valore = field.value or ""
    tipo   = field.field_type or ""
    chiave_suggerita = ""
    for keyword, chiave in MAPPA_SUGGERITA.items():
        if keyword.lower() in name.lower():
            chiave_suggerita = chiave
            break

    print(f"  Campo: '{name}'")
    print(f"    Tipo:    {tipo}")
    print(f"    Valore:  {repr(valore)}")
    print(f"    Suggerito → {chiave_suggerita or '???'}")
    print()
    nuova_mappatura[name] = chiave_suggerita or "???"

# Aggiorna il config con i nomi reali
with open(CONFIG, encoding="utf-8") as f:
    config = json.load(f)

config["campi"] = nuova_mappatura
config["_note"] = config.get("_note","") + " [nomi campi verificati con ispeziona_form_rm2.py]"

with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print(f"✅ Mappatura aggiornata in: {CONFIG}")
print("\nI campi con '???' vanno mappati manualmente.")
print("Riaprilo e sostituisci '???' con la chiave dati corretta.")
