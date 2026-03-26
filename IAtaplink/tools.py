"""
Tool CrewAI per la lettura della configurazione di produzione.
Output in formato TOON (Token-Oriented Object Notation) per massima efficienza token.
"""

import math
import os

import yaml
from crewai.tools import tool
from toon_format import encode as toon_encode

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


@tool("Leggi Configurazione Produzione")
def leggi_configurazione(domanda: str) -> str:
    """
    Legge il file config.yaml e restituisce tutti i dati di produzione
    in formato TOON (Token-Oriented Object Notation):
    costi unitari, scorte di magazzino, capacità produttiva (Bambu Lab A1 Mini),
    analisi ammortamento e listino prezzi (vendita singola + scaglioni B2B).
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
    vendita = config.get("vendita", {})
    filamento = config.get("filamento", {})

    costo_unitario = (
        costi.get("elettricita_per_stampa_eur", 0)
        + costi.get("filamento_per_pezzo_eur", 0)
        + costi.get("costo_nfc_singolo_eur", 0)
        + costi.get("costo_anello_ferro_eur", 0)
    )

    pezzi_da_filamento = mag.get("filamento_kg", 0) * mag.get("pezzi_per_kg_filamento", 0)
    pezzi_producibili = int(min(
        mag.get("nfc_disponibili", 0),
        pezzi_da_filamento,
        mag.get("anelli_ferro", 0),
    ))

    cap = prod.get("capacita_batch_stampante", 1)
    ore_batch = prod.get("tempo_stampa_batch_ore", 1)
    batch_per_100 = math.ceil(100 / cap)
    ore_per_100 = batch_per_100 * ore_batch

    costo_stamp = amm.get("costo_stampante_nuova_eur", 0)
    target = amm.get("target_vendite_ammortamento", 1)
    ammortamento_per_pezzo = round(costo_stamp / target, 4) if target else 0

    margine_singolo = vendita.get("margine_singolo_percentuale", 70) / 100
    soglia = vendita.get("soglia_b2b", 300)
    prezzo_singolo = round(costo_unitario / (1 - margine_singolo), 2)

    scaglioni = []
    for s in vendita.get("scaglioni_b2b", []):
        sconto = s.get("sconto_percentuale", 0) / 100
        prezzo = round(prezzo_singolo * (1 - sconto), 2)
        scaglioni.append({
            "da": s.get("da", 0),
            "a": s.get("a", 0),
            "sconto_pct": int(sconto * 100),
            "prezzo_eur": prezzo,
        })

    fil_listino = []
    for f in filamento.get("refill_senza_bobina", []):
        fil_listino.append({
            "rotoli": f["rotoli"],
            "prezzo_eur": f["prezzo_eur"],
            "sconto": f["sconto"],
        })

    dati = {
        "stampante": prod.get("stampante", "N/A"),
        "costi_unitari_eur": {
            "elettricita": costi.get("elettricita_per_stampa_eur", 0),
            "filamento": costi.get("filamento_per_pezzo_eur", 0),
            "nfc": costi.get("costo_nfc_singolo_eur", 0),
            "anello_ferro": costi.get("costo_anello_ferro_eur", 0),
            "totale": round(costo_unitario, 3),
        },
        "magazzino": {
            "nfc_disponibili": mag.get("nfc_disponibili", 0),
            "filamento_kg": mag.get("filamento_kg", 0),
            "pezzi_da_filamento": int(pezzi_da_filamento),
            "anelli_ferro": mag.get("anelli_ferro", 0),
            "pezzi_producibili": pezzi_producibili,
        },
        "produzione": {
            "capacita_batch": cap,
            "ore_per_batch": ore_batch,
            "batch_per_100pz": batch_per_100,
            "ore_per_100pz": ore_per_100,
        },
        "filamento_listino": fil_listino,
        "ammortamento": {
            "costo_stampante_eur": costo_stamp,
            "target_vendite": target,
            "costo_per_pezzo_eur": ammortamento_per_pezzo,
        },
        "listino_prezzi": {
            "soglia_b2b": soglia,
            "singolo_prezzo_eur": prezzo_singolo,
            "singolo_margine_pct": int(margine_singolo * 100),
            "scaglioni_b2b": scaglioni,
        },
    }

    return "DATI PRODUZIONE (formato TOON):\n\n" + toon_encode(dati)
