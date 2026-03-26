"""
Tool CrewAI per la lettura della configurazione di produzione.
"""

import math
import os

import yaml
from crewai.tools import tool

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


@tool("Leggi Configurazione Produzione")
def leggi_configurazione(domanda: str) -> str:
    """
    Legge il file config.yaml e restituisce tutti i dati di produzione:
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

    scaglioni_txt = ""
    for s in vendita.get("scaglioni_b2b", []):
        sconto = s.get("sconto_percentuale", 0) / 100
        prezzo = round(prezzo_singolo * (1 - sconto), 2)
        da, a = s.get("da", 0), s.get("a", 0)
        a_label = f"{a}" if a < 99999 else "+"
        scaglioni_txt += f"  {da}-{a_label} pz: €{prezzo}/pz (-{int(sconto*100)}%)\n"

    fil_txt = ""
    for f in filamento.get("refill_senza_bobina", []):
        fil_txt += f"  {f['rotoli']} rotoli: €{f['prezzo_eur']} ({f['sconto']})\n"

    return (
        f"═══ CONFIGURAZIONE PRODUZIONE ({prod.get('stampante','N/A')}) ═══\n\n"
        "📦 COSTI UNITARI:\n"
        f"  Elettricità:   €{costi.get('elettricita_per_stampa_eur', 0)}\n"
        f"  Filamento:     €{costi.get('filamento_per_pezzo_eur', 0)}\n"
        f"  NFC singolo:   €{costi.get('costo_nfc_singolo_eur', 0)} (100pz = €7.00)\n"
        f"  Anello ferro:  €{costi.get('costo_anello_ferro_eur', 0)} (100pz = €2.67)\n"
        f"  ➜ COSTO UNITARIO TOTALE: €{costo_unitario:.3f}\n\n"
        "🏭 MAGAZZINO ATTUALE:\n"
        f"  NFC disponibili:    {mag.get('nfc_disponibili', 0)}\n"
        f"  Filamento:          {mag.get('filamento_kg', 0)} kg "
        f"({int(pezzi_da_filamento)} pezzi)\n"
        f"  Anelli ferro:       {mag.get('anelli_ferro', 0)}\n"
        f"  ➜ PEZZI PRODUCIBILI ORA: {pezzi_producibili}\n\n"
        "🖨️ PRODUZIONE:\n"
        f"  Stampante:          {prod.get('stampante', 'N/A')}\n"
        f"  Capacità batch:     {cap} pezzi\n"
        f"  Tempo per batch:    {ore_batch} ore\n"
        f"  Tempo per 100 pz:  ~{ore_per_100} ore ({batch_per_100} batch)\n\n"
        "🧵 LISTINO FILAMENTO (refill senza bobina):\n"
        f"{fil_txt}\n"
        "📈 AMMORTAMENTO NUOVA STAMPANTE:\n"
        f"  Costo stampante:           €{costo_stamp}\n"
        f"  Vendite per ammortizzare:  {target} pezzi\n"
        f"  Ammortamento per pezzo:    €{ammortamento_per_pezzo}\n\n"
        f"💰 LISTINO PREZZI (soglia B2B: {soglia} pz):\n"
        f"  VENDITA SINGOLA (1-{soglia-1} pz): €{prezzo_singolo}/pz "
        f"(margine {int(margine_singolo*100)}%)\n"
        f"  SCAGLIONI B2B (≥{soglia} pz):\n"
        f"{scaglioni_txt}"
    )
