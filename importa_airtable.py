"""
Importa clienti e pratiche da Airtable CRM Pazienti → SQLite locale.
Esegui: python3 importa_airtable.py
Oppure usa il pulsante nell'app web.
"""
import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime
import database as db

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────

BASE_ID        = "appaaUPK4XYSqTDuH"
TABLE_PAZIENTI = "tblftcqGbsrR6AFI6"
TABLE_PRATICHE = "tbl1hN5zSeIitpbjB"

# Mappa stati Airtable → nostro sistema
STATO_MAP = {
    "Segnalato":  "Aperta",
    "Valutato":   "In corso",
    "Prescritto": "In corso",
    "ASL":        "In attesa",
    "Ordine":     "In corso",
    "Consegna":   "In corso",
    "Fattura":    "Completata",
    "Chiuso":     "Chiusa",
}

# Mappa ASL Airtable → nostro sistema
ASL_MAP = {
    "RM1": "ASL Roma 1",
    "RM2": "ASL Roma 2",
    "RM3": "ASL Roma 3",
    "RM4": "ASL Roma 4",
    "RM5": "ASL Roma 5",
    "RM6": "ASL Roma 6",
}

# ── HELPER ────────────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.environ.get("AIRTABLE_API_KEY", "")
    if not key:
        p = os.path.join(os.path.dirname(__file__), "config", "airtable_key.txt")
        if os.path.isfile(p):
            with open(p) as f:
                key = f.read().strip()
    return key


def _airtable_get(endpoint: str, params=None) -> dict:
    """Chiamata GET all'API Airtable v0.
    params può essere dict o lista di tuple (per chiavi duplicate come fields[]).
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("Chiave Airtable non trovata. Salvala nella pagina 'Importa da Airtable'.")

    url = f"https://api.airtable.com/v0/{BASE_ID}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Errore Airtable HTTP {e.code}: {corpo}") from e


def _get_all_records(table_id: str) -> list:
    """Scarica tutti i record di una tabella (gestisce paginazione).
    Usa returnFieldsByFieldId=true per accedere ai campi tramite ID.
    """
    records = []
    # Lista di tuple per supportare parametri multipli con lo stesso nome
    params = [("pageSize", "100"), ("returnFieldsByFieldId", "true")]

    while True:
        data = _airtable_get(table_id, params)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        # Aggiorna offset per la prossima pagina
        params = [(k, v) for k, v in params if k != "offset"]
        params.append(("offset", offset))

    return records


def _parse_indirizzo(indirizzo_raw: str) -> dict:
    """
    Estrae via, città e CAP da un indirizzo in formato libero.
    Esempi:
      "via Gian Matteo Giberti 45 Roma 00151"
      "Via dei platani 9\nRoma 00172"
    """
    if not indirizzo_raw:
        return {"indirizzo": "", "citta": "", "cap": ""}

    testo = indirizzo_raw.replace("\n", " ").strip()

    # Cerca CAP (5 cifre)
    cap_match = re.search(r'\b(\d{5})\b', testo)
    cap = cap_match.group(1) if cap_match else ""
    if cap:
        testo = testo.replace(cap, "").strip()

    # Cerca città (parola/e dopo il numero civico)
    citta = ""
    citta_match = re.search(r'\b(\d+)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s*\d{5}|$)', testo)
    if citta_match:
        citta_candidate = citta_match.group(2).strip()
        if len(citta_candidate.split()) <= 3:
            citta = citta_candidate

    if not citta:
        parole = [p for p in testo.split() if len(p) > 3 and p[0].isupper()]
        if parole:
            citta = parole[-1]

    # L'indirizzo è il testo meno la città
    indirizzo_pulito = testo
    if citta and citta in indirizzo_pulito:
        idx = indirizzo_pulito.rfind(citta)
        indirizzo_pulito = indirizzo_pulito[:idx].strip().rstrip(",")

    return {
        "indirizzo": indirizzo_pulito.strip(),
        "citta": citta.strip(),
        "cap": cap
    }


def _split_cognome_nome(cognome_nome: str) -> tuple:
    """
    "Rossi Mario"      → ("Rossi", "Mario")
    "Di Felice Tiziano" → ("Di Felice", "Tiziano")
    """
    if not cognome_nome:
        return ("", "")
    parts = cognome_nome.strip().split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    if len(parts) == 2:
        return (parts[0], parts[1])
    # 3+ parti: ultima parola = nome, le precedenti = cognome
    return (" ".join(parts[:-1]), parts[-1])


def _get_cf(field_value):
    """Estrae CF dall'aiText field di Airtable.
    L'aiText restituisce {"isValid": true/false, "value": "..."} oppure {"errorType": "..."}.
    Ritorna None se il CF non è valido (16 caratteri), così SQLite non produce conflitti UNIQUE.
    """
    if not field_value:
        return None
    if isinstance(field_value, dict):
        val = (field_value.get("value") or "").upper().strip()
    else:
        val = str(field_value).upper().strip()
    # Un CF valido ha esattamente 16 caratteri
    return val if len(val) == 16 else None


def _get_select(field_value) -> str:
    """Legge un campo singleSelect: può essere stringa o dict con 'name'."""
    if not field_value:
        return ""
    if isinstance(field_value, dict):
        return field_value.get("name", "") or ""
    return str(field_value)


def _map_asl(asl_value) -> str:
    nome = _get_select(asl_value)
    return ASL_MAP.get(nome, nome)


def _map_stato(stato_value) -> str:
    nome = _get_select(stato_value)
    return STATO_MAP.get(nome, "In corso") if nome else "Aperta"


def _map_ausilio(ausilio_value) -> str:
    """Converte lista multipleSelects in stringa."""
    if not ausilio_value:
        return ""
    if isinstance(ausilio_value, list):
        nomi = [a.get("name", "") if isinstance(a, dict) else str(a) for a in ausilio_value]
        return ", ".join(filter(None, nomi))
    return str(ausilio_value)


def _format_date(date_str) -> str:
    """Converte data ISO → YYYY-MM-DD."""
    if not date_str or not isinstance(date_str, str):
        return ""
    return date_str[:10]


def _format_importo(val) -> str:
    """Converte importo numerico Airtable in stringa."""
    if val is None:
        return ""
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return str(val)


# ── IMPORTAZIONE ──────────────────────────────────────────────────────────────

def importa_pazienti(dry_run: bool = False) -> dict:
    """
    Importa tutti i pazienti da Airtable nel database locale.
    dry_run=True → simula senza salvare.
    Ritorna statistiche + mappa airtable_record_id → cliente_id.
    """
    db.init_db()
    records = _get_all_records(TABLE_PAZIENTI)

    nuovi = 0
    aggiornati = 0
    saltati = 0
    airtable_id_map = {}  # airtable_record_id → nostro cliente_id

    for r in records:
        # Con returnFieldsByFieldId=true i valori sono in r["fields"] con chiavi = field ID
        f = r.get("fields", {})

        cognome_nome = f.get("flds1v7Enoggwo48L", "") or ""
        cognome, nome = _split_cognome_nome(cognome_nome)
        if not cognome and not nome:
            saltati += 1
            continue

        indirizzo_raw = f.get("fldDae8itcq2whMkk", "") or ""
        addr = _parse_indirizzo(indirizzo_raw)

        sesso_raw = f.get("fldYL3fzqeZAJW4Td")
        sesso = _get_select(sesso_raw)

        cliente_data = {
            "cognome":         cognome,
            "nome":            nome,
            "codice_fiscale":  _get_cf(f.get("fld19OrcEbxwu12DV")),
            "data_nascita":    _format_date(f.get("fldXJadyI5bA2rLrt", "")),
            "luogo_nascita":   f.get("fldxsOWRJjKXAD6P0", "") or "",
            "sesso":           sesso,
            "indirizzo":       addr["indirizzo"],
            "citta":           addr["citta"],
            "cap":             addr["cap"],
            "telefono":        f.get("fldry0h9YY335sxL0", "") or "",
            "email":           f.get("flduSqwEuCUI61aBU", "") or "",
            "asl_competente":  _map_asl(f.get("fldc03nsyLIlUZGL6")),
            "centro":          _get_select(f.get("fld9kQN5wQvDYidiL")),
            "note":            f.get("fldnpdzJ7jErmDBsL", "") or "",
        }

        # Aggiunge link Drive nelle note
        drive_url = f.get("fld3e7x8piBFN8FM1", "")
        if drive_url:
            note_attuali = cliente_data["note"]
            cliente_data["note"] = (note_attuali + f"\n[Drive: {drive_url}]").strip()

        if not dry_run:
            cf = cliente_data["codice_fiscale"]  # è None oppure stringa da 16 char
            esistente = None
            conn = db.get_db()

            # 1) Cerca per codice fiscale (solo se presente)
            if cf:
                row = conn.execute(
                    "SELECT id FROM clienti WHERE codice_fiscale=?", (cf,)
                ).fetchone()
                if row:
                    esistente = row[0]

            # 2) Fallback: cerca per cognome + nome esatti
            if not esistente:
                row = conn.execute(
                    "SELECT id FROM clienti WHERE cognome=? AND nome=? AND attivo=1",
                    (cognome, nome)
                ).fetchone()
                if row:
                    esistente = row[0]

            conn.close()

            if esistente:
                db.save_cliente(cliente_data, id=esistente)
                airtable_id_map[r["id"]] = esistente
                aggiornati += 1
            else:
                nuovo_id = db.save_cliente(cliente_data)
                airtable_id_map[r["id"]] = nuovo_id
                nuovi += 1
        else:
            # Dry-run: simula senza scrivere
            nuovi += 1

    return {
        "totale":          len(records),
        "nuovi":           nuovi,
        "aggiornati":      aggiornati,
        "saltati":         saltati,
        "airtable_id_map": airtable_id_map,
    }


def importa_pratiche(airtable_id_map: dict = None, dry_run: bool = False) -> dict:
    """Importa le pratiche da Airtable."""
    db.init_db()

    if airtable_id_map is None:
        airtable_id_map = {}

    records = _get_all_records(TABLE_PRATICHE)
    nuovi = 0
    saltati = 0

    for r in records:
        f = r.get("fields", {})

        # Trova il cliente collegato tramite il campo "Pazienti" (multipleRecordLinks)
        pazienti_links = f.get("fldxqkcMhj6GCKQDU", []) or []
        cliente_id = None

        for link in pazienti_links:
            # Con returnFieldsByFieldId, i link sono record ID stringa o dict
            at_id = link if isinstance(link, str) else link.get("id", "")
            if at_id in airtable_id_map:
                cliente_id = airtable_id_map[at_id]
                break

        if not cliente_id:
            saltati += 1
            continue

        pratica_data = {
            "cliente_id":          cliente_id,
            "stato":               _map_stato(f.get("fld2aBqVmZ7ny2XC9")),
            "data_apertura":       _format_date(f.get("fldSZzx5cilf3fMA4") or f.get("flddjiD2UQgCTmt3j", "")),
            "ausilio_richiesto":   _map_ausilio(f.get("fldQUgppTJCSxdqpH")),
            "importo_preventivo":  _format_importo(f.get("fldBeSOdhQEYXUawi")),
            # Timeline fasi
            "data_segnalazione":   _format_date(f.get("flddjiD2UQgCTmt3j", "")),   # Segnalata
            "data_valutazione":    _format_date(f.get("fldHg3RbAeHaBZ7GH", "")),   # Valutato
            "data_prescrizione":   _format_date(f.get("fld6dvbvmFset5xeH", "")),   # Prescritto
            "data_autorizzazione": _format_date(f.get("fldGWyqEWpweuGeGJ", "")),   # ASL
            "data_ordine":         _format_date(f.get("fldCqUm6OiTsoz1be", "")),   # Ordine
            "data_fornitura":      _format_date(f.get("fldTen6nLWWrDsCYW", "")),   # Consegna
            "note":                f.get("fld61gILT7N0YTTWx", "") or "",
        }

        if not dry_run:
            db.save_pratica(pratica_data)
            nuovi += 1
        else:
            nuovi += 1

    return {
        "totale":  len(records),
        "nuovi":   nuovi,
        "saltati": saltati,
    }


def importa_tutto(dry_run: bool = False) -> dict:
    """Importa pazienti + pratiche in sequenza."""
    print("📥 Importazione pazienti da Airtable...")
    res_p = importa_pazienti(dry_run=dry_run)
    print(f"   ✅ Trovati {res_p['totale']} | Nuovi: {res_p['nuovi']} | "
          f"Aggiornati: {res_p['aggiornati']} | Saltati: {res_p['saltati']}")

    print("📥 Importazione pratiche...")
    res_pr = importa_pratiche(
        airtable_id_map=res_p["airtable_id_map"],
        dry_run=dry_run
    )
    print(f"   ✅ Trovate {res_pr['totale']} | Importate: {res_pr['nuovi']} | "
          f"Saltate (no cliente): {res_pr['saltati']}")

    return {"pazienti": res_p, "pratiche": res_pr}


if __name__ == "__main__":
    import sys
    dry = "--dry" in sys.argv
    if dry:
        print("🔍 MODALITÀ DRY-RUN (nessuna modifica al database)\n")
    risultato = importa_tutto(dry_run=dry)
    print("\n✅ Completato.")
