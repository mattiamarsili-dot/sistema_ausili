"""
Registra i template PDF nel database.
Esegui una volta dopo il setup: python3 init_templates.py
"""
import os
import database as db

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "data", "pdf_templates")

TEMPLATES = [
    {
        "nome_template": "Prescrizione_Cloude",
        "file_path": os.path.join(TEMPLATES_DIR, "Prescrizione_Cloude.pdf"),
        "tipo_documento": "Prescrizione",
        "asl_filter": "",
        "descrizione": "Prescrizione DM 332/1999 — universale per tutte le ASL. AcroForm.",
        "mappatura": ""
    },
    {
        "nome_template": "Delega_Sapio",
        "file_path": os.path.join(TEMPLATES_DIR, "Delega_Sapio.pdf"),
        "tipo_documento": "Delega",
        "asl_filter": "",
        "descrizione": "Delega SAPIO LIFE — valida per tutte le ASL. AcroForm 2 pagine.",
        "mappatura": ""
    },
    {
        "nome_template": "MODELLO_PREVENTIVI_2026",
        "file_path": os.path.join(TEMPLATES_DIR, "MODELLO_PREVENTIVI_2026.pdf"),
        "tipo_documento": "Preventivo",
        "asl_filter": "",
        "descrizione": "Modello preventivo 2026 — universale. Overlay tabella voci.",
        "mappatura": ""
    },
    {
        "nome_template": "Delega_RM2_Compilabile",
        "file_path": os.path.join(TEMPLATES_DIR, "Delega_RM2_Compilabile.pdf"),
        "tipo_documento": "Delega + Autocertificazione",
        "asl_filter": "RM2",
        "descrizione": "ASL RM2 — PDF compilabile (AcroForm). Delega SAPIO LIFE (pag.1) + Allegato 5 Autocertificazione (pag.2).",
        "mappatura": ""
    },
    {
        "nome_template": "Deleghe_Rm3",
        "file_path": os.path.join(TEMPLATES_DIR, "Deleghe_Rm3.pdf"),
        "tipo_documento": "Delega + Autocertificazione",
        "asl_filter": "RM3",
        "descrizione": "ASL RM3 — Modulo 10. Autocertificazione (pag.1) + Modello di Delega (pag.2). Overlay.",
        "mappatura": ""
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
    print("\nDone — template registrati nel database.")
