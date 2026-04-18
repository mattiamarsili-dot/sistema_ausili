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

    return dati


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

    field_values = {}
    for campo_pdf, chiave_dati in mappatura.items():
        field_values[campo_pdf] = _get_field_value(chiave_dati, dati)

    writer.update_page_form_field_values(writer.pages[0], field_values)

    # Applica a tutte le pagine se necessario
    if len(writer.pages) > 1:
        for page in writer.pages[1:]:
            writer.update_page_form_field_values(page, field_values)

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
