"""
CRM semplice basato su SQLite per tracciare prospect, messaggi e sessioni.

Il database viene creato automaticamente alla prima esecuzione nella
stessa cartella dello script (crm.db).
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Crea le tabelle se non esistono."""
    con = _conn()
    c = con.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS prospect (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('B2C', 'B2B')),
            settore TEXT DEFAULT '',
            sede_citta TEXT DEFAULT '',
            sede_regione TEXT DEFAULT '',
            contatto TEXT DEFAULT '',
            motivazione TEXT DEFAULT '',
            stato TEXT DEFAULT 'nuovo',
            data_creazione TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messaggio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER,
            canale TEXT DEFAULT 'email',
            destinatario TEXT DEFAULT '',
            oggetto TEXT DEFAULT '',
            corpo TEXT NOT NULL,
            stato TEXT DEFAULT 'bozza' CHECK(stato IN ('bozza','approvato','inviato','errore')),
            data_creazione TEXT NOT NULL,
            data_invio TEXT,
            errore TEXT DEFAULT '',
            FOREIGN KEY (prospect_id) REFERENCES prospect(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessione (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            prospect_b2c INTEGER DEFAULT 0,
            prospect_b2b INTEGER DEFAULT 0,
            email_inviate INTEGER DEFAULT 0,
            email_errori INTEGER DEFAULT 0,
            approvazione TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
    """)

    con.commit()
    con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def salva_prospect(
    nome: str,
    tipo: str,
    settore: str = "",
    sede_citta: str = "",
    sede_regione: str = "",
    contatto: str = "",
    motivazione: str = "",
) -> int:
    """Inserisce un prospect e restituisce il suo ID."""
    con = _conn()
    c = con.cursor()
    c.execute(
        "INSERT INTO prospect (nome, tipo, settore, sede_citta, sede_regione, "
        "contatto, motivazione, data_creazione) VALUES (?,?,?,?,?,?,?,?)",
        (nome, tipo, settore, sede_citta, sede_regione, contatto, motivazione, _now()),
    )
    pid = c.lastrowid
    con.commit()
    con.close()
    return pid


def salva_messaggio(
    corpo: str,
    prospect_id: int | None = None,
    canale: str = "email",
    destinatario: str = "",
    oggetto: str = "",
    stato: str = "bozza",
) -> int:
    """Inserisce un messaggio/email e restituisce il suo ID."""
    con = _conn()
    c = con.cursor()
    c.execute(
        "INSERT INTO messaggio (prospect_id, canale, destinatario, oggetto, "
        "corpo, stato, data_creazione) VALUES (?,?,?,?,?,?,?)",
        (prospect_id, canale, destinatario, oggetto, corpo, stato, _now()),
    )
    mid = c.lastrowid
    con.commit()
    con.close()
    return mid


def aggiorna_messaggio(messaggio_id: int, stato: str, errore: str = "") -> None:
    """Aggiorna lo stato di un messaggio (inviato / errore)."""
    con = _conn()
    c = con.cursor()
    data_invio = _now() if stato == "inviato" else None
    c.execute(
        "UPDATE messaggio SET stato=?, data_invio=?, errore=? WHERE id=?",
        (stato, data_invio, errore, messaggio_id),
    )
    con.commit()
    con.close()


def registra_sessione(
    prospect_b2c: int = 0,
    prospect_b2b: int = 0,
    email_inviate: int = 0,
    email_errori: int = 0,
    approvazione: str = "",
    note: str = "",
) -> int:
    """Registra una sessione (esecuzione della crew) e restituisce l'ID."""
    con = _conn()
    c = con.cursor()
    c.execute(
        "INSERT INTO sessione (data, prospect_b2c, prospect_b2b, email_inviate, "
        "email_errori, approvazione, note) VALUES (?,?,?,?,?,?,?)",
        (_now(), prospect_b2c, prospect_b2b, email_inviate, email_errori, approvazione, note),
    )
    sid = c.lastrowid
    con.commit()
    con.close()
    return sid


def cerca_prospect(tipo: str | None = None, stato: str | None = None) -> list[dict]:
    """Cerca prospect con filtri opzionali. Restituisce lista di dizionari."""
    con = _conn()
    con.row_factory = sqlite3.Row
    c = con.cursor()
    query = "SELECT * FROM prospect WHERE 1=1"
    params: list = []
    if tipo:
        query += " AND tipo=?"
        params.append(tipo)
    if stato:
        query += " AND stato=?"
        params.append(stato)
    query += " ORDER BY data_creazione DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    con.close()
    return rows


def statistiche() -> dict:
    """Restituisce statistiche aggregate del CRM."""
    con = _conn()
    c = con.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM prospect")
    stats["totale_prospect"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM prospect WHERE tipo='B2C'")
    stats["prospect_b2c"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM prospect WHERE tipo='B2B'")
    stats["prospect_b2b"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messaggio WHERE stato='inviato'")
    stats["email_inviate"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sessione")
    stats["sessioni_totali"] = c.fetchone()[0]
    con.close()
    return stats
