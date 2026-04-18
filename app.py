import os
import json
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import database as db
import pdf_compiler as pdf_mod
import lettore_documenti as lettore

app = Flask(__name__)
app.secret_key = "ausili_secret_2024"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "data", "pdf_templates")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── INIT ─────────────────────────────────────────────────────────────────────

@app.before_request
def setup():
    db.init_db()


# ── HOME / DASHBOARD ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    stats = db.get_statistiche()
    return render_template("index.html", stats=stats)


# ── CLIENTI ──────────────────────────────────────────────────────────────────

@app.route("/clienti")
def clienti():
    search = request.args.get("q", "")
    lista = db.get_all_clienti(search=search or None)
    return render_template("clienti.html", clienti=lista, search=search)


@app.route("/clienti/nuovo", methods=["GET", "POST"])
def nuovo_cliente():
    if request.method == "POST":
        db.save_cliente(request.form.to_dict())
        flash("Cliente salvato con successo.", "success")
        return redirect(url_for("clienti"))
    return render_template("cliente_form.html", cliente={}, title="Nuovo Cliente")


@app.route("/clienti/<int:id>", methods=["GET", "POST"])
def modifica_cliente(id):
    cliente = db.get_cliente(id)
    if not cliente:
        flash("Cliente non trovato.", "danger")
        return redirect(url_for("clienti"))
    if request.method == "POST":
        db.save_cliente(request.form.to_dict(), id=id)
        flash("Cliente aggiornato.", "success")
        return redirect(url_for("clienti"))
    pratiche = db.get_all_pratiche(cliente_id=id)
    return render_template("cliente_form.html", cliente=cliente, pratiche=pratiche, title="Modifica Cliente")


@app.route("/clienti/<int:id>/elimina", methods=["POST"])
def elimina_cliente(id):
    db.delete_cliente(id)
    flash("Cliente rimosso.", "warning")
    return redirect(url_for("clienti"))


# ── PRATICHE ─────────────────────────────────────────────────────────────────

@app.route("/pratiche")
def pratiche():
    search = request.args.get("q", "")
    stato = request.args.get("stato", "")
    lista = db.get_all_pratiche(stato=stato or None, search=search or None)
    return render_template("pratiche.html", pratiche=lista, search=search, stato_filtro=stato)


@app.route("/pratiche/nuova", methods=["GET", "POST"])
def nuova_pratica():
    if request.method == "POST":
        id = db.save_pratica(request.form.to_dict())
        flash("Pratica creata.", "success")
        return redirect(url_for("modifica_pratica", id=id))
    clienti_list = db.get_all_clienti()
    cliente_id = request.args.get("cliente_id")
    return render_template("pratica_form.html", pratica={}, clienti=clienti_list,
                           selected_cliente=cliente_id, title="Nuova Pratica")


@app.route("/pratiche/<int:id>", methods=["GET", "POST"])
def modifica_pratica(id):
    pratica = db.get_pratica(id)
    if not pratica:
        flash("Pratica non trovata.", "danger")
        return redirect(url_for("pratiche"))
    if request.method == "POST":
        db.save_pratica(request.form.to_dict(), id=id)
        flash("Pratica aggiornata.", "success")
        return redirect(url_for("modifica_pratica", id=id))
    clienti_list = db.get_all_clienti()
    cliente = db.get_cliente(pratica["cliente_id"])
    asl = (cliente or {}).get("asl_competente", "")
    templates = db.get_templates_per_asl(asl)
    # Pre-compila medico_prescrittore dal cliente se la pratica non ce l'ha
    pratica = dict(pratica)
    if not pratica.get("medico_prescrittore") and cliente:
        pratica["medico_prescrittore"] = cliente.get("medico_referente", "")
    return render_template("pratica_form.html", pratica=pratica, clienti=clienti_list,
                           templates=templates, asl_cliente=asl, title="Dettaglio Pratica")


# ── PDF TEMPLATES ─────────────────────────────────────────────────────────────

@app.route("/templates")
def templates():
    lista = db.get_all_templates()
    return render_template("templates.html", templates=lista)


@app.route("/templates/nuovo", methods=["GET", "POST"])
def nuovo_template():
    if request.method == "POST":
        f = request.files.get("file_pdf")
        if f and f.filename.endswith(".pdf"):
            filename = f.filename.replace(" ", "_")
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(save_path)
            data = request.form.to_dict()
            data["file_path"] = save_path
            tid = db.save_template(data)
            flash("Template caricato.", "success")
            return redirect(url_for("modifica_template", id=tid))
        else:
            flash("Carica un file PDF valido.", "danger")
    return render_template("template_form.html", template={}, campi=[], title="Nuovo Template")


@app.route("/templates/<int:id>", methods=["GET", "POST"])
def modifica_template(id):
    tmpl = db.get_template(id)
    if not tmpl:
        flash("Template non trovato.", "danger")
        return redirect(url_for("templates"))
    if request.method == "POST":
        data = request.form.to_dict()
        data["file_path"] = tmpl["file_path"]
        db.save_template(data, id=id)
        flash("Template aggiornato.", "success")
        return redirect(url_for("templates"))
    campi = pdf_mod.inspect_pdf(tmpl["file_path"])
    return render_template("template_form.html", template=tmpl, campi=campi, title="Configura Template")


# ── COMPILAZIONE PDF ─────────────────────────────────────────────────────────

@app.route("/compila/<int:template_id>/<int:pratica_id>")
def compila_pdf(template_id, pratica_id):
    pratica = db.get_pratica(pratica_id)
    if not pratica:
        return jsonify({"errore": "Pratica non trovata"}), 404
    cliente = db.get_cliente(pratica["cliente_id"])
    tmpl = db.get_template(template_id)
    if not tmpl:
        return jsonify({"errore": "Template non trovato"}), 404

    dati = {
        "cliente": cliente,
        "pratica": pratica,
        "data_oggi": __import__("datetime").date.today().strftime("%d/%m/%Y")
    }

    try:
        output_path = pdf_mod.compila_pdf(tmpl, dati)
        db.log_documento({
            "pratica_id": pratica_id,
            "cliente_id": cliente["id"],
            "template_id": template_id,
            "nome_file": os.path.basename(output_path),
            "file_path": output_path
        })
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))
    except Exception as e:
        flash(f"Errore nella compilazione: {e}", "danger")
        return redirect(url_for("modifica_pratica", id=pratica_id))


@app.route("/api/inspect/<int:template_id>")
def api_inspect(template_id):
    tmpl = db.get_template(template_id)
    if not tmpl:
        return jsonify({"errore": "Template non trovato"}), 404
    info = pdf_mod.inspect_pdf(tmpl["file_path"])
    return jsonify(info)


# ── IMPORTA DA DRIVE ─────────────────────────────────────────────────────────

@app.route("/importa")
def importa():
    path = request.args.get("path", "")
    contenuto = lettore.sfoglia_cartella(path or None)
    return render_template("importa.html", contenuto=contenuto)


@app.route("/api/analizza", methods=["POST"])
def api_analizza():
    """Analizza uno o più PDF con Claude e restituisce i dati estratti."""
    data = request.get_json()
    paths = data.get("paths", [])
    if not paths:
        return jsonify({"errore": "Nessun file specificato"}), 400
    risultati = []
    for p in paths:
        if not os.path.isfile(p):
            risultati.append({"_file": os.path.basename(p), "errore": "File non trovato"})
        else:
            risultati.append(lettore.analizza_documento(p))
    return jsonify(risultati)


@app.route("/api/analizza-cartella", methods=["POST"])
def api_analizza_cartella():
    data = request.get_json()
    cartella = data.get("path", "")
    if not os.path.isdir(cartella):
        return jsonify({"errore": "Cartella non trovata"}), 400
    risultati = lettore.analizza_cartella_pratica(cartella)
    return jsonify(risultati)


@app.route("/importa/salva", methods=["POST"])
def importa_salva():
    """Salva i dati estratti (revisionati dall'utente) come nuovo cliente + pratica."""
    form = request.form.to_dict()

    # Salva o aggiorna cliente
    cliente_id = form.get("cliente_id") or None
    if cliente_id:
        db.save_cliente(form, id=int(cliente_id))
    else:
        cliente_id = db.save_cliente(form)

    # Crea pratica se ci sono dati
    if form.get("ausilio_richiesto") or form.get("medico_prescrittore"):
        form["cliente_id"] = cliente_id
        db.save_pratica(form)
        flash("Cliente e pratica importati con successo.", "success")
    else:
        flash("Cliente importato. Aggiungi la pratica manualmente.", "success")

    return redirect(url_for("modifica_cliente", id=cliente_id))


@app.route("/api/clienti")
def api_clienti():
    q = request.args.get("q", "")
    lista = db.get_all_clienti(search=q or None)
    return jsonify(lista)


@app.route("/api/clienti/<int:id>")
def api_cliente_detail(id):
    c = db.get_cliente(id)
    if not c:
        return jsonify({}), 404
    return jsonify(c)


# ── IMPORTA DA AIRTABLE ───────────────────────────────────────────────────────

# Stato globale dell'importazione (semplice per uso locale/single-user)
_importazione_stato = {"running": False, "risultato": None, "errore": None}


@app.route("/importa-airtable")
def importa_airtable_page():
    """Pagina per importare clienti e pratiche da Airtable."""
    # Controlla se la chiave API è configurata
    key_path = os.path.join(os.path.dirname(__file__), "config", "airtable_key.txt")
    key_ok = False
    if os.path.isfile(key_path):
        with open(key_path) as f:
            val = f.read().strip()
            key_ok = bool(val) and not val.startswith("INSERISCI")

    stats = db.get_statistiche()
    return render_template("importa_airtable.html",
                           key_ok=key_ok,
                           stats=stats,
                           stato=_importazione_stato)


@app.route("/api/airtable/importa", methods=["POST"])
def api_airtable_importa():
    """Avvia l'importazione da Airtable (dry_run o reale)."""
    global _importazione_stato
    if _importazione_stato["running"]:
        return jsonify({"errore": "Importazione già in corso"}), 409

    data = request.get_json() or {}
    dry_run = data.get("dry_run", False)

    _importazione_stato = {"running": True, "risultato": None, "errore": None}

    def esegui():
        global _importazione_stato
        try:
            import importa_airtable as ia
            risultato = ia.importa_tutto(dry_run=dry_run)
            _importazione_stato["risultato"] = risultato
        except Exception as e:
            _importazione_stato["errore"] = str(e)
        finally:
            _importazione_stato["running"] = False

    t = threading.Thread(target=esegui, daemon=True)
    t.start()
    return jsonify({"avviato": True, "dry_run": dry_run})


@app.route("/api/airtable/stato")
def api_airtable_stato():
    """Restituisce lo stato corrente dell'importazione."""
    return jsonify(_importazione_stato)


@app.route("/api/airtable/salva-chiave", methods=["POST"])
def api_airtable_salva_chiave():
    """Salva la chiave API Airtable."""
    data = request.get_json() or {}
    chiave = (data.get("chiave") or "").strip()
    if not chiave:
        return jsonify({"errore": "Chiave vuota"}), 400
    key_path = os.path.join(os.path.dirname(__file__), "config", "airtable_key.txt")
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "w") as f:
        f.write(chiave)
    return jsonify({"ok": True})


# ── DRIVE BROWSER ────────────────────────────────────────────────────────────

DRIVE_BASE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-altramobilita@gmail.com/Il mio Drive"
)
IS_CLOUD = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

# Cartelle preferite mostrate sulla homepage Drive (percorsi relativi a DRIVE_BASE)
DRIVE_PREFERITI = [
    {"nome": "📁 2026",         "path": "2026"},
    {"nome": "Pratiche",        "path": "2026/Pratiche"},
    {"nome": "Moduli",          "path": "2026/MODULI"},
    {"nome": "Deleghe",         "path": "2026/MODULI/DELEGA"},
    {"nome": "MoveOn",          "path": "2026/Pratiche/MoveOn"},
    {"nome": "Domiciliari",     "path": "2026/Pratiche/Domiciliari"},
    {"nome": "CPA",             "path": "2026/Pratiche/CPA"},
    {"nome": "Nemo",            "path": "2026/Pratiche/Nemo"},
]

ICONE_EXT = {
    ".pdf":  ("bi-file-earmark-pdf-fill", "text-danger"),
    ".jpg":  ("bi-file-earmark-image",    "text-warning"),
    ".jpeg": ("bi-file-earmark-image",    "text-warning"),
    ".png":  ("bi-file-earmark-image",    "text-warning"),
    ".docx": ("bi-file-earmark-word",     "text-primary"),
    ".xlsx": ("bi-file-earmark-excel",    "text-success"),
    ".txt":  ("bi-file-earmark-text",     "text-secondary"),
}


def _drive_path_safe(rel_path: str) -> str | None:
    """Restituisce il percorso assoluto solo se è dentro DRIVE_BASE."""
    abs_path = os.path.normpath(os.path.join(DRIVE_BASE, rel_path))
    if abs_path.startswith(os.path.normpath(DRIVE_BASE)):
        return abs_path
    return None


@app.route("/drive")
def drive():
    if IS_CLOUD:
        return render_template("drive.html", cloud=True,
                               cartelle=None, files=None,
                               breadcrumb=[], path_corrente="",
                               preferiti=DRIVE_PREFERITI)
    rel = request.args.get("path", "")
    # Se c'è un percorso, sfoglia quella cartella
    if rel:
        abs_path = _drive_path_safe(rel)
        if not abs_path or not os.path.isdir(abs_path):
            flash("Cartella non trovata.", "warning")
            return redirect(url_for("drive"))

        # Cartelle e file
        try:
            entries = os.listdir(abs_path)
        except PermissionError:
            flash("Accesso negato.", "danger")
            return redirect(url_for("drive"))

        cartelle = []
        files = []
        for name in sorted(entries, key=lambda x: x.lower()):
            if name.startswith("."):
                continue
            full = os.path.join(abs_path, name)
            rel_child = os.path.join(rel, name)
            if os.path.isdir(full):
                cartelle.append({"nome": name, "path": rel_child})
            else:
                ext = os.path.splitext(name)[1].lower()
                icona, colore = ICONE_EXT.get(ext, ("bi-file-earmark", "text-secondary"))
                files.append({
                    "nome": name,
                    "path": rel_child,
                    "ext": ext,
                    "icona": icona,
                    "colore": colore,
                    "size": os.path.getsize(full),
                })

        # Breadcrumb
        parti = rel.split(os.sep)
        breadcrumb = []
        for i, p in enumerate(parti):
            breadcrumb.append({"nome": p, "path": os.path.join(*parti[:i+1])})

        return render_template("drive.html",
                               cartelle=cartelle,
                               files=files,
                               breadcrumb=breadcrumb,
                               path_corrente=rel,
                               preferiti=DRIVE_PREFERITI)

    # Homepage Drive: mostra solo i preferiti
    return render_template("drive.html",
                           cartelle=None,
                           files=None,
                           breadcrumb=[],
                           path_corrente="",
                           preferiti=DRIVE_PREFERITI)


@app.route("/drive/file")
def drive_file():
    """Serve un file dalla cartella Drive."""
    rel = request.args.get("path", "")
    abs_path = _drive_path_safe(rel)
    if not abs_path or not os.path.isfile(abs_path):
        return "File non trovato", 404
    # Apertura inline per i PDF, download per gli altri
    ext = os.path.splitext(abs_path)[1].lower()
    inline = ext in (".pdf", ".jpg", ".jpeg", ".png")
    return send_file(abs_path, as_attachment=not inline)


if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("RAILWAY_ENVIRONMENT") is None  # debug solo in locale
    app.run(debug=debug, host="0.0.0.0", port=port)
