import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")

# Crea la cartella data/ se non esiste (necessario su Railway)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_column_if_missing(conn, table, column, col_type):
    """Aggiunge una colonna alla tabella se non esiste già (migrazione sicura)."""
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cognome TEXT NOT NULL,
            codice_fiscale TEXT UNIQUE,
            data_nascita TEXT,
            luogo_nascita TEXT,
            sesso TEXT CHECK(sesso IN ('M','F','')),
            indirizzo TEXT,
            cap TEXT,
            citta TEXT,
            provincia TEXT,
            telefono TEXT,
            email TEXT,
            medico_referente TEXT,
            asl_competente TEXT,
            tipo_disabilita TEXT,
            grado_invalidita TEXT,
            tutore_nome TEXT,
            tutore_cognome TEXT,
            tutore_cognome_nome TEXT,
            tutore_telefono TEXT,
            tutore_luogo_nascita TEXT,
            tutore_data_nascita TEXT,
            tutore_provincia_nascita TEXT,
            tutore_doc_tipo TEXT,
            tutore_doc_numero TEXT,
            tutore_doc_rilascio TEXT,
            doc_tipo TEXT,
            doc_numero TEXT,
            doc_rilascio TEXT,
            note TEXT,
            data_inserimento TEXT DEFAULT (datetime('now','localtime')),
            attivo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS pratiche (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_pratica TEXT UNIQUE,
            cliente_id INTEGER NOT NULL REFERENCES clienti(id),
            tipo_pratica TEXT CHECK(tipo_pratica IN ('Valutazione','Fornitura','Assistenza','Riparazione','Collaudo')),
            stato TEXT CHECK(stato IN ('Aperta','In corso','In attesa','Completata','Chiusa')) DEFAULT 'Aperta',
            data_apertura TEXT DEFAULT (date('now','localtime')),
            data_chiusura TEXT,
            ente_pubblico TEXT,
            ufficio_protesi TEXT,
            medico_prescrittore TEXT,
            ausilio_richiesto TEXT,
            codice_ausilio TEXT,
            descrizione_ausilio TEXT,
            importo_preventivo REAL,
            importo_liquidato REAL,
            numero_autorizzazione TEXT,
            data_autorizzazione TEXT,
            data_fornitura TEXT,
            data_collaudo TEXT,
            note TEXT,
            data_inserimento TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS ausili (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice TEXT UNIQUE,
            nome TEXT NOT NULL,
            descrizione TEXT,
            categoria TEXT,
            produttore TEXT,
            modello TEXT,
            prezzo_listino REAL,
            attivo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS preventivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_preventivo TEXT UNIQUE,
            pratica_id INTEGER REFERENCES pratiche(id),
            cliente_id INTEGER NOT NULL REFERENCES clienti(id),
            data_preventivo TEXT DEFAULT (date('now','localtime')),
            validita_giorni INTEGER DEFAULT 60,
            totale REAL DEFAULT 0,
            stato TEXT CHECK(stato IN ('Bozza','Inviato','Accettato','Rifiutato')) DEFAULT 'Bozza',
            note TEXT,
            data_inserimento TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS preventivo_righe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preventivo_id INTEGER NOT NULL REFERENCES preventivi(id) ON DELETE CASCADE,
            ausilio_id INTEGER REFERENCES ausili(id),
            descrizione TEXT NOT NULL,
            quantita REAL DEFAULT 1,
            prezzo_unitario REAL DEFAULT 0,
            sconto_perc REAL DEFAULT 0,
            totale_riga REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pdf_template_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_template TEXT NOT NULL,
            file_path TEXT NOT NULL,
            tipo_documento TEXT,
            descrizione TEXT,
            asl_filter TEXT,
            mappatura TEXT,
            data_inserimento TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS documenti_generati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pratica_id INTEGER REFERENCES pratiche(id),
            cliente_id INTEGER REFERENCES clienti(id),
            preventivo_id INTEGER REFERENCES preventivi(id),
            template_id INTEGER REFERENCES pdf_template_mapping(id),
            nome_file TEXT,
            file_path TEXT,
            data_generazione TEXT DEFAULT (datetime('now','localtime')),
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS nomenclatore_voci (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice_iso TEXT,
            descrizione TEXT NOT NULL,
            prezzo_unitario REAL DEFAULT 0,
            iva_perc REAL DEFAULT 4,
            nota TEXT,
            attivo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS pratica_voci (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pratica_id INTEGER NOT NULL REFERENCES pratiche(id) ON DELETE CASCADE,
            codice_iso TEXT,
            descrizione TEXT,
            quantita REAL DEFAULT 1,
            prezzo_unitario REAL DEFAULT 0,
            prezzo_totale REAL DEFAULT 0,
            ordinamento INTEGER DEFAULT 0
        );
    """)
    conn.commit()

    # Migrazioni sicure — eseguite DOPO la creazione delle tabelle
    _add_column_if_missing(conn, "pratiche", "data_segnalazione", "TEXT")
    _add_column_if_missing(conn, "pratiche", "data_valutazione",  "TEXT")
    _add_column_if_missing(conn, "pratiche", "data_prescrizione", "TEXT")
    _add_column_if_missing(conn, "pratiche", "data_ordine",       "TEXT")
    _add_column_if_missing(conn, "clienti",  "centro",            "TEXT")
    _add_column_if_missing(conn, "clienti",  "anno_residenza",    "TEXT")
    _add_column_if_missing(conn, "pratiche", "centro",            "TEXT")

    conn.close()


# ── CLIENTI ──────────────────────────────────────────────────────────────────

def get_all_clienti(search=None, ordine="cognome"):
    ordini_validi = {"cognome", "nome", "asl_competente", "citta", "centro", "data_inserimento"}
    if ordine not in ordini_validi:
        ordine = "cognome"
    conn = get_db()
    if search:
        q = f"%{search}%"
        rows = conn.execute(
            f"SELECT * FROM clienti WHERE attivo=1 AND (nome LIKE ? OR cognome LIKE ? OR codice_fiscale LIKE ? OR citta LIKE ?) ORDER BY {ordine}, cognome",
            (q, q, q, q)
        ).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM clienti WHERE attivo=1 ORDER BY {ordine}, cognome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cliente(id):
    conn = get_db()
    row = conn.execute("SELECT * FROM clienti WHERE id=?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_cliente(data, id=None):
    conn = get_db()
    fields = ["nome","cognome","codice_fiscale","data_nascita","luogo_nascita","sesso",
              "indirizzo","cap","citta","provincia","anno_residenza","telefono","email",
              "medico_referente","asl_competente","tipo_disabilita","centro",
              "doc_tipo","doc_numero","doc_rilascio",
              "tutore_nome","tutore_cognome","tutore_cognome_nome","tutore_telefono",
              "tutore_luogo_nascita","tutore_data_nascita","tutore_provincia_nascita",
              "tutore_doc_tipo","tutore_doc_numero","tutore_doc_rilascio","note"]

    def _val(f):
        v = data.get(f, "")
        # Il codice fiscale vuoto va salvato come NULL (non "")
        # così il vincolo UNIQUE non collide tra più clienti senza CF
        if f == "codice_fiscale" and not v:
            return None
        return v if v is not None else ""

    values = [_val(f) for f in fields]
    if id:
        set_clause = ", ".join(f"{f}=?" for f in fields)
        conn.execute(f"UPDATE clienti SET {set_clause} WHERE id=?", values + [id])
    else:
        placeholders = ", ".join("?" * len(fields))
        conn.execute(f"INSERT INTO clienti ({','.join(fields)}) VALUES ({placeholders})", values)
        id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return id


def delete_cliente(id):
    conn = get_db()
    conn.execute("UPDATE clienti SET attivo=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ── PRATICHE ─────────────────────────────────────────────────────────────────

def get_all_pratiche(cliente_id=None, stato=None, search=None, centro=None, ausilio=None, ordine="data_apertura"):
    conn = get_db()
    query = """
        SELECT p.*, c.nome, c.cognome, c.codice_fiscale, c.telefono
        FROM pratiche p JOIN clienti c ON p.cliente_id = c.id
        WHERE 1=1
    """
    params = []
    if cliente_id:
        query += " AND p.cliente_id=?"; params.append(cliente_id)
    if stato:
        query += " AND p.stato=?"; params.append(stato)
    if centro:
        query += " AND p.centro=?"; params.append(centro)
    if ausilio:
        query += " AND p.ausilio_richiesto=?"; params.append(ausilio)
    if search:
        q = f"%{search}%"
        query += " AND (p.numero_pratica LIKE ? OR c.cognome LIKE ? OR p.ausilio_richiesto LIKE ?)"
        params += [q, q, q]
    # Ordinamento sicuro
    ordini_validi = {"data_apertura", "stato", "centro", "ausilio_richiesto", "c.cognome"}
    if ordine not in ordini_validi:
        ordine = "data_apertura"
    query += f" ORDER BY {ordine} DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pratica(id):
    conn = get_db()
    row = conn.execute(
        "SELECT p.*, c.nome, c.cognome, c.codice_fiscale FROM pratiche p JOIN clienti c ON p.cliente_id=c.id WHERE p.id=?",
        (id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_pratica(data, id=None):
    conn = get_db()
    fields = ["cliente_id","stato","data_apertura","data_chiusura",
              "ente_pubblico","centro","medico_prescrittore","ausilio_richiesto",
              "descrizione_ausilio","importo_preventivo","importo_liquidato",
              "data_autorizzazione","data_fornitura",
              "data_segnalazione","data_valutazione","data_prescrizione","data_ordine",
              "note","significato_terapeutico"]
    values = [data.get(f, "") or None for f in fields]
    if id:
        set_clause = ", ".join(f"{f}=?" for f in fields)
        conn.execute(f"UPDATE pratiche SET {set_clause} WHERE id=?", values + [id])
    else:
        # Genera numero pratica automatico univoco
        year = datetime.now().year
        # Cerca il massimo progressivo già usato nell'anno (funziona anche durante import batch)
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(numero_pratica, 8) AS INTEGER)) FROM pratiche "
            "WHERE numero_pratica LIKE ?", (f"PR{year}-%",)
        ).fetchone()
        last = row[0] if row[0] else 0
        numero = f"PR{year}-{last+1:04d}"
        conn.execute(f"INSERT INTO pratiche (numero_pratica, {','.join(fields)}) VALUES (?, {','.join('?'*len(fields))})",
                     [numero] + values)
        id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return id


# ── AUSILI ───────────────────────────────────────────────────────────────────

def get_all_ausili(search=None):
    conn = get_db()
    if search:
        q = f"%{search}%"
        rows = conn.execute("SELECT * FROM ausili WHERE attivo=1 AND (nome LIKE ? OR codice LIKE ? OR categoria LIKE ?)",
                            (q, q, q)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ausili WHERE attivo=1 ORDER BY categoria, nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_ausilio(data, id=None):
    conn = get_db()
    fields = ["codice","nome","descrizione","categoria","produttore","modello","prezzo_listino"]
    values = [data.get(f, "") for f in fields]
    if id:
        set_clause = ", ".join(f"{f}=?" for f in fields)
        conn.execute(f"UPDATE ausili SET {set_clause} WHERE id=?", values + [id])
    else:
        conn.execute(f"INSERT INTO ausili ({','.join(fields)}) VALUES ({','.join('?'*len(fields))})", values)
        id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return id


# ── PDF TEMPLATES ─────────────────────────────────────────────────────────────

def get_all_templates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM pdf_template_mapping ORDER BY tipo_documento, nome_template").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_template(id):
    conn = get_db()
    row = conn.execute("SELECT * FROM pdf_template_mapping WHERE id=?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_templates_per_asl(asl: str) -> list:
    """Restituisce i template compatibili con l'ASL del cliente.
    Se asl_filter è vuoto, il template è universale (mostrato sempre).
    Se asl_filter è impostato, viene mostrato solo se l'ASL del cliente lo contiene."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM pdf_template_mapping ORDER BY tipo_documento, nome_template").fetchall()
    conn.close()
    result = []
    for r in [dict(x) for x in rows]:
        filtro = (r.get("asl_filter") or "").strip()
        if not filtro:
            result.append(r)
        elif filtro.lower() in (asl or "").lower():
            result.append(r)
    return result


def save_template(data, id=None):
    conn = get_db()
    fields = ["nome_template","file_path","tipo_documento","descrizione","asl_filter","mappatura"]
    values = [data.get(f, "") for f in fields]
    if id:
        set_clause = ", ".join(f"{f}=?" for f in fields)
        conn.execute(f"UPDATE pdf_template_mapping SET {set_clause} WHERE id=?", values + [id])
    else:
        conn.execute(f"INSERT INTO pdf_template_mapping ({','.join(fields)}) VALUES ({','.join('?'*len(fields))})", values)
        id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return id


def elimina_template(id):
    conn = get_db()
    conn.execute("DELETE FROM pdf_template_mapping WHERE id=?", (id,))
    conn.commit()
    conn.close()


def log_documento(data):
    conn = get_db()
    fields = ["pratica_id","cliente_id","preventivo_id","template_id","nome_file","file_path","note"]
    values = [data.get(f) for f in fields]
    conn.execute(f"INSERT INTO documenti_generati ({','.join(fields)}) VALUES ({','.join('?'*len(fields))})", values)
    conn.commit()
    conn.close()


# ── NOMENCLATORE ──────────────────────────────────────────────────────────────

def get_all_nomenclatore(search=None):
    conn = get_db()
    if search:
        q = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM nomenclatore_voci WHERE attivo=1 AND (codice_iso LIKE ? OR descrizione LIKE ?)",
            (q, q)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM nomenclatore_voci WHERE attivo=1 ORDER BY codice_iso, descrizione").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_nomenclatore_voce(data, id=None):
    conn = get_db()
    fields = ["codice_iso", "descrizione", "prezzo_unitario", "iva_perc", "nota"]
    values = [data.get(f, "") or None for f in fields]
    if id:
        set_clause = ", ".join(f"{f}=?" for f in fields)
        conn.execute(f"UPDATE nomenclatore_voci SET {set_clause} WHERE id=?", values + [id])
    else:
        conn.execute(f"INSERT INTO nomenclatore_voci ({','.join(fields)}) VALUES ({','.join('?'*len(fields))})", values)
        id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return id


def delete_nomenclatore_voce(id):
    conn = get_db()
    conn.execute("UPDATE nomenclatore_voci SET attivo=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()


def get_pratica_voci(pratica_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM pratica_voci WHERE pratica_id=? ORDER BY ordinamento, id",
        (pratica_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_pratica_voci(pratica_id, voci_list):
    """Sostituisce tutte le voci della pratica con la lista fornita.
    Aggiorna anche pratiche.importo_preventivo con il subtotale (netto)."""
    conn = get_db()
    conn.execute("DELETE FROM pratica_voci WHERE pratica_id=?", (pratica_id,))
    subtotale = 0.0
    for i, v in enumerate(voci_list):
        qty = float(v.get("quantita", 1) or 1)
        prezzo_u = float(v.get("prezzo_unitario", 0) or 0)
        prezzo_t = round(qty * prezzo_u, 2)
        subtotale += prezzo_t
        conn.execute(
            "INSERT INTO pratica_voci (pratica_id, codice_iso, descrizione, quantita, prezzo_unitario, prezzo_totale, ordinamento) VALUES (?,?,?,?,?,?,?)",
            (pratica_id, v.get("codice_iso",""), v.get("descrizione",""), qty, prezzo_u, prezzo_t, i)
        )
    # Aggiorna importo_preventivo nella pratica con il totale netto
    conn.execute(
        "UPDATE pratiche SET importo_preventivo=? WHERE id=?",
        (round(subtotale, 2), pratica_id)
    )
    conn.commit()
    conn.close()


# ── STATISTICHE ───────────────────────────────────────────────────────────────

def get_statistiche():
    conn = get_db()
    stats = {}
    stats["totale_clienti"] = conn.execute("SELECT COUNT(*) FROM clienti WHERE attivo=1").fetchone()[0]
    stats["pratiche_aperte"] = conn.execute("SELECT COUNT(*) FROM pratiche WHERE stato IN ('Aperta','In corso')").fetchone()[0]
    stats["pratiche_totali"] = conn.execute("SELECT COUNT(*) FROM pratiche").fetchone()[0]
    stats["pratiche_per_stato"] = [dict(r) for r in conn.execute(
        "SELECT stato, COUNT(*) as n FROM pratiche GROUP BY stato").fetchall()]
    stats["pratiche_per_tipo"] = [dict(r) for r in conn.execute(
        "SELECT tipo_pratica, COUNT(*) as n FROM pratiche GROUP BY tipo_pratica").fetchall()]
    stats["ultimi_clienti"] = [dict(r) for r in conn.execute(
        "SELECT id, nome, cognome, data_inserimento FROM clienti WHERE attivo=1 ORDER BY data_inserimento DESC LIMIT 5").fetchall()]
    stats["ultime_pratiche"] = [dict(r) for r in conn.execute(
        """SELECT p.id, p.numero_pratica, p.stato, p.tipo_pratica, c.nome, c.cognome
           FROM pratiche p JOIN clienti c ON p.cliente_id=c.id
           ORDER BY p.data_inserimento DESC LIMIT 5""").fetchall()]
    conn.close()
    return stats
