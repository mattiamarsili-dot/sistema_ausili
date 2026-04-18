"""
Registra i template PDF nel database.
Esegui una volta dopo il setup: python3 init_templates.py
"""
import os
import database as db

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "data", "pdf_templates")

TEMPLATES = [
    {
        "nome_template": "Deleghe_Rm3",
        "file_path": os.path.join(TEMPLATES_DIR, "Deleghe_Rm3.pdf"),
        "tipo_documento": "Delega + Autocertificazione",
        "asl_filter": "Roma 3",
        "descrizione": "ASL Roma 3 — Modulo 10. Autocertificazione (pag.1) + Modello di Delega (pag.2). Compilazione overlay.",
        "mappatura": ""  # Usa config/Deleghe_Rm3_mapping.json
    },
    {
        "nome_template": "Delega_RM2_Compilabile",
        "file_path": os.path.join(TEMPLATES_DIR, "Delega_RM2_Compilabile.pdf"),
        "tipo_documento": "Delega + Autocertificazione",
        "asl_filter": "Roma 2",
        "descrizione": "ASL Roma 2 — PDF compilabile (AcroForm). Delega a SAPIO LIFE (pag.1) + Allegato 5 Autocertificazione (pag.2). I nomi dei campi AcroForm vanno verificati con Python.",
        "mappatura": ""  # Usa config/Delega_RM2_Compilabile_mapping.json
    },
]

if __name__ == "__main__":
    db.init_db()
    for t in TEMPLATES:
        if not os.path.isfile(t["file_path"]):
            print(f"⚠️  File non trovato: {t['file_path']}")
            continue
        existing = [x for x in db.get_all_templates() if x["nome_template"] == t["nome_template"]]
        if existing:
            db.save_template(t, id=existing[0]["id"])
            print(f"✅ Aggiornato: {t['nome_template']}")
        else:
            db.save_template(t)
            print(f"✅ Aggiunto: {t['nome_template']}")
    print("\nTemplate registrati nel database.")
