"""
Modulo per la compilazione automatica di PDF.
Supporta:
  - PDF con campi modulo AcroForm (pypdf)
  - PDF statici con overlay di testo (reportlab + pypdf)
"""
import os
import json
import io
from datetime import datetime

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, create_string_object
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "output")


def _fmt_euro(val: float) -> str:
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _arricchisci_dati(dati: dict) -> dict:
    """
    Aggiunge chiavi derivate utili per i template:
      cliente.cognome_nome, cliente.nascita_gg/mm/aaaa, ecc.
    """
    c = dati.get("cliente", {})
    if c:
        # Cognome Nome come campo unico
        if not c.get("cognome_nome"):
            c["cognome_nome"] = f"{c.get('cognome','').strip()} {c.get('nome','').strip()}".strip()
        # Parti della data di nascita
        dn = c.get("data_nascita", "")
        if dn and len(dn) == 10:
            try:
                d = datetime.strptime(dn, "%Y-%m-%d")
                c["nascita_gg"]   = d.strftime("%d")
                c["nascita_mm"]   = d.strftime("%m")
                c["nascita_aaaa"] = d.strftime("%Y")
            except Exception:
                pass
        # Tipo documento + numero combinati (es. "Carta d'identità   AB1234567")
        doc_tipo = c.get("doc_tipo", "").strip()
        doc_num  = c.get("doc_numero", "").strip()
        if doc_tipo or doc_num:
            c["doc_tipo_numero"] = f"{doc_tipo}   {doc_num}".strip() if (doc_tipo and doc_num) else (doc_tipo or doc_num)
        # Stessa cosa per il tutore/delegato
        t_tipo = c.get("tutore_doc_tipo", "").strip()
        t_num  = c.get("tutore_doc_numero", "").strip()
        if t_tipo or t_num:
            c["tutore_doc_tipo_numero"] = f"{t_tipo}   {t_num}".strip() if (t_tipo and t_num) else (t_tipo or t_num)
        # Formatta doc_rilascio se presente
        for campo in ("doc_rilascio", "tutore_doc_rilascio", "tutore_data_nascita"):
            v = c.get(campo, "")
            if v and len(v) == 10 and v[4] == "-":
                try:
                    c[campo] = datetime.strptime(v, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    pass
        dati["cliente"] = c

    # Chiavi fisse azienda
    dati["nome_azienda"] = "SAPIO LIFE SRL"

    # Medico prescrittore con fallback: pratica → medico_referente del cliente
    p = dati.get("pratica", {})
    if not p.get("medico_prescrittore") and c.get("medico_referente"):
        if isinstance(p, dict):
            p["medico_prescrittore"] = c.get("medico_referente", "")
            dati["pratica"] = p

    # ASL come testo leggibile (per compilare il campo ASL fisso nel modulo)
    asl_val = c.get("asl_competente", "")
    dati["asl_competente"] = asl_val  # top-level per comodità nel mapping

    # Codice AM per Delega Sapio: "AM" + data_autorizzazione in formato ddmm.aa
    p = dati.get("pratica", {})
    if isinstance(p, dict):
        data_auth = p.get("data_autorizzazione", "")
        if data_auth and len(data_auth) >= 10:
            try:
                d = datetime.strptime(data_auth[:10], "%Y-%m-%d")
                p["codice_am"] = "AM" + d.strftime("%d%m.%y")
            except Exception:
                pass
        dati["pratica"] = p

    # Data di oggi formattata
    dati["data_oggi"] = datetime.now().strftime("%d/%m/%Y")

    # Data oggi in formato ddmm (per campo N. Preven in AM.pdf)
    dati["data_oggi_ddmm"] = datetime.now().strftime("%d%m")

    # Città + CAP combinati
    c["citta_cap"] = f"{c.get('citta','').strip()} {c.get('cap','').strip()}".strip()
    dati["cliente"] = c

    # Espandi voci nomenclatore in chiavi flat per i template AcroForm
    # voci_0_codice, voci_0_descrizione, voci_0_quantita, ... (fino a 16 righe)
    voci = dati.get("voci", [])
    subtotale_voci = 0.0
    for i, v in enumerate(voci[:16]):
        qty = v.get("quantita", 1)
        # Formatta quantità: rimuove decimali inutili (1.0 → "1", 2.5 → "2,5")
        if isinstance(qty, float) and qty == int(qty):
            qty_str = str(int(qty))
        else:
            qty_str = str(qty).replace(".", ",")
        p_u = float(v.get("prezzo_unitario", 0) or 0)
        p_t = float(v.get("prezzo_totale", 0) or 0)
        subtotale_voci += p_t
        dati[f"voci_{i}_codice"]           = str(v.get("codice_iso", "") or "")
        dati[f"voci_{i}_descrizione"]      = str(v.get("descrizione", "") or "")
        dati[f"voci_{i}_quantita"]         = qty_str
        dati[f"voci_{i}_prezzo_unitario"]  = _fmt_euro(p_u) if p_u else ""
        dati[f"voci_{i}_prezzo_totale"]    = _fmt_euro(p_t) if p_t else ""
    # Pulisci le righe extra (se ci sono meno voci del max del template)
    for i in range(len(voci), 16):
        dati[f"voci_{i}_codice"]          = ""
        dati[f"voci_{i}_descrizione"]     = ""
        dati[f"voci_{i}_quantita"]        = ""
        dati[f"voci_{i}_prezzo_unitario"] = ""
        dati[f"voci_{i}_prezzo_totale"]   = ""
    # Totali calcolati dalle voci
    iva_voci = round(subtotale_voci * 0.04, 2)
    dati["subtotale"]    = _fmt_euro(subtotale_voci)
    dati["iva_importo"]  = _fmt_euro(iva_voci)
    dati["totale_finale"] = _fmt_euro(round(subtotale_voci + iva_voci, 2))

    # Testo significato personalizzato dall'utente (ha priorità sul JSON)
    if dati.get("significato_custom", "").strip():
        _espandi_testo(dati, "significato_riga", dati["significato_custom"].strip(), 6, 118)
        return dati

    # Testi predefiniti per Prescrizione, associati al tipo di ausilio
    testi_path = os.path.join(os.path.dirname(__file__), "config", "testi_prescrizione.json")
    if os.path.isfile(testi_path):
        try:
            with open(testi_path, encoding="utf-8") as f:
                testi_map = json.load(f)
            ausilio = dati.get("pratica", {}).get("ausilio_richiesto", "") or ""
            varianti_richieste = dati.get("variante_testo") or []
            if isinstance(varianti_richieste, str):
                varianti_richieste = [varianti_richieste] if varianti_richieste else []
            entry = testi_map.get(ausilio)
            selezionate = []
            if isinstance(entry, list) and entry:
                if varianti_richieste:
                    # Mantieni l'ordine scelto dall'utente
                    selezionate = [v for nome in varianti_richieste
                                   for v in entry if v.get("nome") == nome]
                else:
                    selezionate = [entry[0]]    # default: prima variante
            elif isinstance(entry, dict):       # vecchio formato singola variante
                selezionate = [entry]
            if selezionate:
                # Unisci i testi di tutte le varianti selezionate con riga vuota tra una e l'altra
                def _unisci(campo):
                    parti = [v.get(campo, "").strip() for v in selezionate if v.get(campo, "").strip()]
                    return "\n\n".join(parti)
                _espandi_testo(dati, "significato_riga", _unisci("significato"), 6, 118)
                _espandi_testo(dati, "modi_riga",        _unisci("modi_impiego"), 6, 118)
                _espandi_testo(dati, "controindicazioni_riga", _unisci("controindicazioni"), 2, 118)
        except Exception:
            pass

    return dati


def _espandi_testo(dati: dict, prefisso: str, testo: str, max_righe: int, max_chars: int):
    """Suddivide un testo in righe di max_chars caratteri e le inserisce in dati come prefisso_0, prefisso_1..."""
    righe = []
    if testo:
        # Rispetta i ritorni a capo espliciti, poi spezza per lunghezza
        for paragrafo in testo.split("\n"):
            paragrafo = paragrafo.strip()
            if not paragrafo:
                if righe:  # riga vuota di separazione
                    righe.append("")
                continue
            while len(paragrafo) > max_chars:
                # Cerca spazio per andare a capo
                idx = paragrafo.rfind(" ", 0, max_chars)
                if idx == -1:
                    idx = max_chars
                righe.append(paragrafo[:idx])
                paragrafo = paragrafo[idx:].lstrip()
            righe.append(paragrafo)
    for i in range(max_righe):
        dati[f"{prefisso}_{i}"] = righe[i] if i < len(righe) else ""


def _get_field_value(field_key: str, dati: dict) -> str:
    """Risolve un campo dalla mappa dati. Supporta dot-notation: 'cliente.nome'"""
    # Chiavi speciali con trattino basso: ignora campi _desc, _note, ecc.
    if field_key.startswith("_test_"):
        return dati.get(field_key, "")
    parts = field_key.split(".")
    val = dati
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p, "")
        else:
            return ""
    if val is None:
        return ""
    # Formattazione date ISO → gg/mm/aaaa
    if isinstance(val, str) and len(val) == 10 and val[4] == "-":
        try:
            d = datetime.strptime(val, "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
        except Exception:
            pass
    return str(val)


def get_pdf_form_fields(pdf_path: str) -> list[dict]:
    """Restituisce la lista dei campi modulo presenti nel PDF."""
    if not HAS_PYPDF:
        return []
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        if not fields:
            return []
        result = []
        for name, field in fields.items():
            result.append({
                "nome_campo": name,
                "tipo": field.field_type,
                "valore_default": field.value or ""
            })
        return result
    except Exception as e:
        return [{"errore": str(e)}]


def _imposta_font_campi(writer: "PdfWriter", da_string: str = "/Helv 10 Tf 0 g") -> None:
    """Imposta il Default Appearance (font e dimensione) su tutti i campi AcroForm."""
    from pypdf.generic import NameObject, create_string_object

    def _processa(field_ref):
        try:
            field = field_ref.get_object()
            field[NameObject("/DA")] = create_string_object(da_string)
            if "/Kids" in field:
                for kid in field["/Kids"]:
                    _processa(kid)
        except Exception:
            pass

    root = writer._root_object
    if "/AcroForm" in root:
        acroform = root["/AcroForm"].get_object()
        if "/Fields" in acroform:
            for field_ref in acroform["/Fields"]:
                _processa(field_ref)


def compila_form_pdf(pdf_path: str, mappatura: dict, dati: dict, output_path: str) -> str:
    """
    Compila un PDF con campi AcroForm.
    mappatura: {nome_campo_pdf: chiave_in_dati}
    dati: dizionario con i dati (supporta nesting: {'cliente': {...}, 'pratica': {...}})
    """
    if not HAS_PYPDF:
        raise RuntimeError("pypdf non installato. Esegui: pip install pypdf")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    # Forza Helvetica 10pt (equivalente Arial) su tutti i campi
    _imposta_font_campi(writer, "/Helv 10 Tf 0 g")

    field_values = {}
    for campo_pdf, chiave_dati in mappatura.items():
        # Salta chiavi-commento (iniziano con _)
        if campo_pdf.startswith("_"):
            continue
        # Salta valori placeholder
        if chiave_dati == "_":
            continue
        field_values[campo_pdf] = _get_field_value(chiave_dati, dati)

    # Applica a TUTTE le pagine
    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=True)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def compila_overlay_pdf(pdf_path: str, overlay_config: list, dati: dict, output_path: str) -> str:
    """
    Compila un PDF statico sovrapponendo testo alle coordinate specificate.
    overlay_config: lista di dict con:
        {pagina, x, y, chiave_dati, font, font_size, colore}
    """
    if not HAS_PYPDF or not HAS_REPORTLAB:
        raise RuntimeError("pypdf e reportlab richiesti. Esegui: pip install pypdf reportlab")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_num, page in enumerate(reader.pages):
        # Crea overlay per questa pagina
        packet = io.BytesIO()
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        for item in overlay_config:
            if item.get("pagina", 0) != page_num:
                continue
            testo = _get_field_value(item["chiave_dati"], dati)
            if not testo:
                continue
            font = item.get("font", "Helvetica")
            size = item.get("font_size", 10)
            colore = item.get("colore", (0, 0, 0))
            c.setFont(font, size)
            c.setFillColorRGB(*colore)
            c.drawString(item["x"], item["y"], testo)

        c.save()
        packet.seek(0)

        overlay_reader = PdfReader(packet)
        if overlay_reader.pages:
            page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def compila_preventivo_pdf(pdf_path: str, dati: dict, output_path: str) -> str:
    """
    Compila MODELLO_PREVENTIVI_2026 (PDF statico) con overlay testo + tabella voci.
    Le coordinate sono in punti PDF (y dal basso).
    """
    if not HAS_PYPDF or not HAS_REPORTLAB:
        raise RuntimeError("pypdf e reportlab richiesti")

    voci = dati.get("voci", [])
    cliente = dati.get("cliente", {})
    pratica = dati.get("pratica", {})

    # Calcola totali
    subtotale = sum(float(v.get("prezzo_totale", 0) or 0) for v in voci)
    iva = round(subtotale * 0.04, 2)
    totale_lordo = round(subtotale + iva, 2)

    fmt_euro = _fmt_euro

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    page = reader.pages[0]
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0, 0, 0)

    # ── Dati paziente ──────────────────────────────────────────────
    cognome_nome = f"{cliente.get('cognome','').strip()} {cliente.get('nome','').strip()}".strip()
    c.drawString(130, 648.7, cognome_nome)

    luogo_nascita = cliente.get("luogo_nascita", "")
    c.drawString(393, 648.7, luogo_nascita)

    indirizzo = f"{cliente.get('indirizzo','')} {cliente.get('citta','')}".strip()
    c.drawString(145, 625.9, indirizzo)

    # Data nascita formattata
    dn = cliente.get("data_nascita", "")
    if dn and len(dn) >= 10:
        try:
            d = datetime.strptime(dn[:10], "%Y-%m-%d")
            dn_fmt = d.strftime("%d/%m/%Y")
        except Exception:
            dn_fmt = dn
    else:
        dn_fmt = dn
    c.drawString(335, 625.9, dn_fmt)

    telefono = cliente.get("telefono", "")
    c.drawString(120, 603.2, telefono)

    centro = pratica.get("centro", "")
    c.drawString(395, 603.2, centro)

    # Numero pratica come riferimento
    num_pratica = pratica.get("numero_pratica", "")
    codice_am = pratica.get("codice_am", "")
    rif = codice_am if codice_am else num_pratica
    c.drawString(135, 678.2, rif)

    # ── Tabella voci ───────────────────────────────────────────────
    c.setFont("Helvetica", 9)
    y_start = 362.0
    row_h = 17.0
    max_righe = 12  # sicurezza: non andare oltre i totali

    for i, v in enumerate(voci[:max_righe]):
        y = y_start - i * row_h
        codice = str(v.get("codice_iso", "") or "")
        desc = str(v.get("descrizione", "") or "")
        qty = v.get("quantita", 1)
        p_u = float(v.get("prezzo_unitario", 0) or 0)
        p_t = float(v.get("prezzo_totale", 0) or 0)

        c.drawString(16, y, codice[:14])
        # Tronca descrizione se troppo lunga (~50 chars per adattarsi alla colonna)
        if len(desc) > 52:
            desc = desc[:50] + "…"
        c.drawString(99, y, desc)
        c.drawRightString(375, y, str(qty).rstrip("0").rstrip(".") if "." in str(qty) else str(qty))
        c.drawRightString(453, y, fmt_euro(p_u) if p_u else "")
        c.drawRightString(512, y, fmt_euro(p_t) if p_t else "")

    # ── Totali ─────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(512, 110.2, fmt_euro(subtotale))
    c.drawRightString(512, 94.2, fmt_euro(iva))
    c.drawRightString(512, 78.1, fmt_euro(totale_lordo))

    c.save()
    packet.seek(0)

    overlay_reader = PdfReader(packet)
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def _carica_mappatura(template_record: dict) -> dict:
    """
    Cerca la mappatura in ordine:
    1. File config/<nome_template>_mapping.json
    2. Campo mappatura nel database
    """
    nome = template_record.get("nome_template", "")
    config_path = os.path.join(CONFIG_DIR, f"{nome}_mapping.json")
    if os.path.isfile(config_path):
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    mappatura_json = template_record.get("mappatura", "{}")
    try:
        return json.loads(mappatura_json) if mappatura_json else {}
    except Exception:
        return {}


def compila_pdf(template_record: dict, dati: dict) -> str:
    """
    Punto di ingresso principale.
    template_record: record dalla tabella pdf_template_mapping
    dati: dizionario con chiavi 'cliente', 'pratica', 'preventivo', ecc.
    Ritorna il percorso del file generato.
    """
    pdf_path = template_record["file_path"]
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"Template non trovato: {pdf_path}")

    dati = _arricchisci_dati(dati)
    dati["data_oggi"] = datetime.now().strftime("%d/%m/%Y")

    mappatura = _carica_mappatura(template_record)
    tipo = mappatura.get("_tipo", "form")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cliente_cf = dati.get("cliente", {}).get("codice_fiscale", "SCONOSCIUTO")
    nome_out = f"{template_record['nome_template']}_{cliente_cf}_{timestamp}.pdf"
    output_path = os.path.join(OUTPUT_DIR, nome_out)

    if tipo == "preventivo_tabella":
        return compila_preventivo_pdf(pdf_path, dati, output_path)

    if tipo == "overlay":
        # Filtra solo i campi reali (ignora chiavi con _ come _desc, _note)
        overlay_config = [c for c in mappatura.get("campi", []) if not c.get("chiave_dati", "").startswith("_")]
        return compila_overlay_pdf(pdf_path, overlay_config, dati, output_path)
    else:
        campi = mappatura.get("campi", {})
        return compila_form_pdf(pdf_path, campi, dati, output_path)


def inspect_pdf(pdf_path: str) -> dict:
    """
    Ispeziona un PDF e restituisce info sui campi modulo presenti.
    Utile per configurare la mappatura.
    """
    info = {
        "tipo": "statico",
        "pagine": 0,
        "campi_modulo": []
    }
    if not HAS_PYPDF:
        return info
    try:
        reader = PdfReader(pdf_path)
        info["pagine"] = len(reader.pages)
        fields = get_pdf_form_fields(pdf_path)
        if fields:
            info["tipo"] = "form"
            info["campi_modulo"] = fields
    except Exception as e:
        info["errore"] = str(e)
    return info
