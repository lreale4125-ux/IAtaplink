"""
Tools personalizzati per il sistema multi-agente NFC Smart Keychains.

Contiene:
- TelegramApprovalTool  → invia messaggio + polling risposta
- leggi_configurazione  → legge config.yaml e calcola metriche
"""

import math
import os
import time
from typing import Type

import requests
import yaml
from crewai.tools import BaseTool, tool
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════
#  Tool 1 — Approvazione via Telegram (Human-in-the-Loop)
# ═══════════════════════════════════════════════════════════════

POLLING_INTERVAL_SEC = 5
POLLING_TIMEOUT_SEC = 3600  # 1 ora massima di attesa
TELEGRAM_MAX_MSG_LEN = 4096


class _TelegramInput(BaseModel):
    """Schema di input per il tool di approvazione Telegram."""

    messaggio: str = Field(
        ...,
        description=(
            "Messaggio completo da inviare al fondatore su Telegram. "
            "Deve contenere: destinatario dell'email, motivazione e bozza email."
        ),
    )


class TelegramApprovalTool(BaseTool):
    """
    Invia un messaggio su Telegram tramite Bot API e attende la risposta
    del fondatore (polling su getUpdates).  Il sistema si blocca finché
    il fondatore non risponde o scade il timeout di 1 ora.
    """

    name: str = "richiedi_approvazione_telegram"
    description: str = (
        "Invia un messaggio al fondatore su Telegram contenente il resoconto "
        "completo (prospect, costi, bozze email, R&D) e attende la sua risposta "
        "di approvazione o rifiuto. Il sistema resta in pausa finché il fondatore "
        "non risponde. Restituisce il testo della risposta."
    )
    args_schema: Type[BaseModel] = _TelegramInput

    def _run(self, messaggio: str) -> str:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        if not token or not chat_id:
            return "ERRORE: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati nel .env"

        base = f"https://api.telegram.org/bot{token}"

        # 1 ─ Svuota gli update pendenti per non leggere messaggi vecchi
        last_update_id = self._flush_old_updates(base)

        # 2 ─ Invia il messaggio (se troppo lungo, lo spezza)
        esito_invio = self._invia_messaggi(base, chat_id, messaggio)
        if esito_invio.startswith("ERRORE"):
            return esito_invio

        # 3 ─ Polling per la risposta del fondatore
        print("\n⏳ In attesa della risposta su Telegram...")
        scadenza = time.time() + POLLING_TIMEOUT_SEC

        while time.time() < scadenza:
            time.sleep(POLLING_INTERVAL_SEC)
            try:
                r = requests.get(
                    f"{base}/getUpdates",
                    params={"offset": last_update_id + 1, "timeout": 30},
                    timeout=60,
                )
                for update in r.json().get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    if str(msg.get("chat", {}).get("id")) == str(chat_id):
                        testo = msg.get("text", "")
                        print(f"✅ Risposta ricevuta: {testo}")
                        return f"Risposta del fondatore: {testo}"
            except requests.RequestException as e:
                print(f"⚠️ Errore polling Telegram: {e} — riprovo...")

        return "TIMEOUT: nessuna risposta ricevuta entro 1 ora."

    # ── Helpers privati ──

    @staticmethod
    def _flush_old_updates(base_url: str) -> int:
        """Scarica l'ultimo update_id per ignorare messaggi precedenti."""
        try:
            r = requests.get(
                f"{base_url}/getUpdates",
                params={"offset": -1, "limit": 1},
                timeout=30,
            )
            risultati = r.json().get("result", [])
            if risultati:
                return risultati[-1]["update_id"]
        except requests.RequestException:
            pass
        return 0

    @staticmethod
    def _invia_messaggi(base_url: str, chat_id: str, testo: str) -> str:
        """Invia il messaggio, spezzandolo in blocchi se supera il limite Telegram."""
        blocchi = []
        while testo:
            blocchi.append(testo[:TELEGRAM_MAX_MSG_LEN])
            testo = testo[TELEGRAM_MAX_MSG_LEN:]

        for i, blocco in enumerate(blocchi):
            resp = requests.post(
                f"{base_url}/sendMessage",
                json={"chat_id": chat_id, "text": blocco},
                timeout=30,
            )
            if resp.status_code != 200:
                return f"ERRORE invio Telegram (blocco {i + 1}): {resp.text}"

        return "OK"


# ═══════════════════════════════════════════════════════════════
#  Tool 2 — Lettura configurazione produzione
# ═══════════════════════════════════════════════════════════════

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


@tool("Leggi Configurazione Produzione")
def leggi_configurazione(domanda: str) -> str:
    """
    Legge il file config.yaml e restituisce tutti i dati di produzione:
    costi unitari, scorte di magazzino, capacità produttiva e analisi
    ammortamento della stampante nuova.  Usa questo tool per rispondere
    a qualsiasi domanda su costi, capacità e scorte.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        return "ERRORE: file config.yaml non trovato."

    costi = config.get("costi", {})
    mag = config.get("magazzino", {})
    prod = config.get("produzione", {})
    amm = config.get("ammortamento", {})

    # Costo unitario totale
    costo_unitario = (
        costi.get("elettricita_per_stampa_eur", 0)
        + costi.get("filamento_per_pezzo_eur", 0)
        + costi.get("costo_nfc_singolo_eur", 0)
        + costi.get("costo_anello_ferro_eur", 0)
    )

    # Pezzi producibili con il magazzino attuale
    pezzi_da_filamento = mag.get("filamento_kg", 0) * mag.get("pezzi_per_kg_filamento", 0)
    pezzi_producibili = int(min(
        mag.get("nfc_disponibili", 0),
        pezzi_da_filamento,
        mag.get("anelli_ferro", 0),
    ))

    # Tempo per produrre N pezzi
    cap = prod.get("capacita_batch_stampante", 1)
    ore_batch = prod.get("tempo_stampa_batch_ore", 1)
    batch_per_100 = math.ceil(100 / cap)
    ore_per_100 = batch_per_100 * ore_batch

    # Ammortamento stampante nuova
    costo_stamp = amm.get("costo_stampante_nuova_eur", 0)
    target = amm.get("target_vendite_ammortamento", 1)
    ammortamento_per_pezzo = round(costo_stamp / target, 4) if target else 0

    return (
        "═══ CONFIGURAZIONE PRODUZIONE ═══\n\n"

        "📦 COSTI UNITARI:\n"
        f"  Elettricità per stampa: €{costi.get('elettricita_per_stampa_eur', 0)}\n"
        f"  Filamento per pezzo:    €{costi.get('filamento_per_pezzo_eur', 0)}\n"
        f"  NFC singolo:            €{costi.get('costo_nfc_singolo_eur', 0)}\n"
        f"  Anello in ferro:        €{costi.get('costo_anello_ferro_eur', 0)}\n"
        f"  ➜ COSTO UNITARIO TOTALE: €{costo_unitario:.2f}\n\n"

        "🏭 MAGAZZINO ATTUALE:\n"
        f"  NFC disponibili:    {mag.get('nfc_disponibili', 0)}\n"
        f"  Filamento:          {mag.get('filamento_kg', 0)} kg "
        f"({int(pezzi_da_filamento)} pezzi)\n"
        f"  Anelli ferro:       {mag.get('anelli_ferro', 0)}\n"
        f"  ➜ PEZZI PRODUCIBILI ORA: {pezzi_producibili}\n\n"

        "🖨️ PRODUZIONE:\n"
        f"  Capacità batch:     {cap} pezzi\n"
        f"  Tempo per batch:    {ore_batch} ore\n"
        f"  Tempo per 100 pz:  ~{ore_per_100} ore "
        f"({batch_per_100} batch)\n\n"

        "📈 AMMORTAMENTO NUOVA STAMPANTE:\n"
        f"  Costo stampante:           €{costo_stamp}\n"
        f"  Vendite per ammortizzare:  {target} pezzi\n"
        f"  Ammortamento per pezzo:    €{ammortamento_per_pezzo}\n"
        f"  Costo unitario attuale:    €{amm.get('costo_unitario_attuale_eur', 0)}\n"
        f"  Costo unitario obiettivo:  €{amm.get('costo_unitario_obiettivo_eur', 0)}\n"
    )
