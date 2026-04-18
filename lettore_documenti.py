"""
Modulo per leggere documenti da Google Drive e estrarne dati strutturati
usando Claude AI (Anthropic API).

Supporta:
- PDF con testo estraibile (prescrizioni, deleghe compilate)
- PDF scansionati (immagini) → Claude vision
- Navigazione cartelle Drive montate localmente
"""
import os
import json
import base64
from pathlib import Path

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Percorso base Google Drive
DRIVE_BASE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-altramobilita@gmail.com/Il mio Drive"
)

PROMPT_ESTRAZIONE = """Sei un assistente specializzato nell'estrazione di dati anagrafici e clinici da documenti italiani per la gestione di ausili per persone con disabilità.

Analizza il documento e estrai i seguenti dati in formato JSON. Se un campo non è presente, usa null.

{
  "cliente": {
    "nome": null,
    "cognome": null,
    "codice_fiscale": null,
    "data_nascita": null,
    "luogo_nascita": null,
    "sesso": null,
    "indirizzo": null,
    "citta": null,
    "provincia": null,
    "cap": null,
    "telefono": null,
    "asl_competente": null,
    "medico_referente": null,
    "tipo_disabilita": null,
    "grado_invalidita": null
  },
  "pratica": {
    "tipo_pratica": null,
    "ausilio_richiesto": null,
    "codice_ausilio": null,
    "medico_prescrittore": null,
    "ente_pubblico": null,
    "ufficio_protesi": null,
    "data_autorizzazione": null,
    "numero_autorizzazione": null
  },
  "tipo_documento": null,
  "note_aggiuntive": null
}

Regole:
- Le date devono essere in formato YYYY-MM-DD
- Il codice fiscale deve essere in maiuscolo, 16 caratteri
- tipo_pratica deve essere uno tra: Valutazione, Fornitura, Assistenza, Riparazione, Collaudo
- tipo_documento deve descrivere brevemente il documento (es. "Prescrizione medica", "Delega ASL Roma 2", "Autocertificazione")
- Rispondi SOLO con il JSON, nessun testo aggiuntivo
"""


def _get_api_key() -> str:
    """Legge la chiave API da variabile ambiente o file config."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        config_path = os.path.join(os.path.dirname(__file__), "config", "api_key.txt")
        if os.path.isfile(config_path):
            with open(config_path) as f:
                key = f.read().strip()
    return key


def estrai_testo_pdf(pdf_path: str) -> tuple[str, bool]:
    """
    Estrae il testo da un PDF.
    Ritorna (testo, è_scansionato).
    Se è scansionato (nessun testo), ritorna ("", True).
    """
    if not HAS_PYPDF:
        return "", False
    try:
        reader = PdfReader(pdf_path)
        testo = ""
        for page in reader.pages:
            testo += page.extract_text() or ""
        testo = testo.strip()
        is_scanned = len(testo) < 50
        return testo, is_scanned
    except Exception as e:
        return f"Errore lettura: {e}", False


def _pdf_to_base64_images(pdf_path: str) -> list[str]:
    """Converte le pagine di un PDF in immagini base64 per Claude vision."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=200, fmt="jpeg")
        result = []
        import io
        for img in images[:4]:  # Max 4 pagine
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            result.append(base64.standard_b64encode(buf.getvalue()).decode())
        return result
    except Exception:
        return []


def analizza_documento(pdf_path: str) -> dict:
    """
    Analizza un PDF con Claude e restituisce i dati estratti.
    """
    if not HAS_ANTHROPIC:
        return {"errore": "Libreria anthropic non installata"}

    api_key = _get_api_key()
    if not api_key:
        return {"errore": "API key Anthropic non configurata. Vedi config/api_key.txt"}

    client = anthropic.Anthropic(api_key=api_key)
    testo, is_scanned = estrai_testo_pdf(pdf_path)

    try:
        if is_scanned:
            # PDF scansionato → usa vision
            immagini = _pdf_to_base64_images(pdf_path)
            if not immagini:
                return {"errore": "PDF scansionato ma pdf2image non disponibile. Installa: pip install pdf2image"}

            content = [{"type": "text", "text": PROMPT_ESTRAZIONE}]
            for img_b64 in immagini:
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                })

            risposta = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": content}]
            )
        else:
            # PDF con testo
            risposta = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": f"{PROMPT_ESTRAZIONE}\n\n--- DOCUMENTO ---\n{testo[:8000]}"
                }]
            )

        testo_risposta = risposta.content[0].text.strip()
        # Rimuovi eventuali blocchi markdown
        if testo_risposta.startswith("```"):
            testo_risposta = testo_risposta.split("```")[1]
            if testo_risposta.startswith("json"):
                testo_risposta = testo_risposta[4:]

        dati = json.loads(testo_risposta)
        dati["_file"] = os.path.basename(pdf_path)
        dati["_path"] = pdf_path
        dati["_scansionato"] = is_scanned
        return dati

    except json.JSONDecodeError as e:
        return {"errore": f"Risposta AI non valida: {e}", "_raw": testo_risposta}
    except Exception as e:
        return {"errore": str(e)}


def sfoglia_cartella(path: str = None) -> dict:
    """
    Elenca il contenuto di una cartella Drive.
    Ritorna: {cartelle: [...], pdf: [...], altri: [...]}
    """
    base = path or DRIVE_BASE
    if not os.path.isdir(base):
        return {"errore": f"Cartella non trovata: {base}", "cartelle": [], "pdf": [], "altri": []}

    cartelle, pdfs, altri = [], [], []
    try:
        for item in sorted(os.scandir(base), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith("."):
                continue
            info = {"nome": item.name, "path": item.path}
            if item.is_dir():
                cartelle.append(info)
            elif item.name.lower().endswith(".pdf"):
                info["size_kb"] = round(item.stat().st_size / 1024, 1)
                pdfs.append(info)
            else:
                altri.append(info)
    except PermissionError:
        pass

    return {
        "path_corrente": base,
        "path_padre": str(Path(base).parent) if base != DRIVE_BASE else None,
        "cartelle": cartelle,
        "pdf": pdfs,
        "altri": altri
    }


def analizza_cartella_pratica(cartella_path: str) -> list[dict]:
    """
    Analizza tutti i PDF in una cartella di pratica.
    Ritorna lista di risultati per ogni documento.
    """
    risultati = []
    if not os.path.isdir(cartella_path):
        return [{"errore": "Cartella non trovata"}]

    for item in os.scandir(cartella_path):
        if item.name.lower().endswith(".pdf") and not item.name.startswith("."):
            r = analizza_documento(item.path)
            r["_file"] = item.name
            risultati.append(r)

    return risultati
