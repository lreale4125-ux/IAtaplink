"""
4 task sequenziali del sistema NFC Smart Keychains.

L'approvazione, l'invio email e il salvataggio CRM sono gestiti
dal bot Telegram (bot.py), non da task CrewAI.

Flusso CrewAI:
  1. Ricerca lead B2C + B2B (L'Esploratore)
  2. Analisi produzione + listino (L'Analista)
  3. Stesura messaggi personalizzati (Il Venditore)
  4. Ricerca innovazione (L'Innovatore)
"""

from crewai import Task

from agents import l_analista, l_esploratore, l_innovatore, il_venditore

SOGLIA_B2B = 300


# ═══════════════════════════════════════════════
#  Task 1 — Ricerca Lead (B2C + B2B)
# ═══════════════════════════════════════════════

ricerca_lead = Task(
    description=(
        "Cerca potenziali clienti italiani per portachiavi NFC smart.\n\n"
        "CATEGORIA A — VENDITA SINGOLA (B2C):\n"
        "  Cerca 2 profili di potenziali clienti singoli:\n"
        "  - Professionisti/freelancer, piccoli negozi, influencer\n"
        "  Per ciascuno: nome/profilo, canale, motivazione d'acquisto.\n\n"
        "CATEGORIA B — VENDITA B2B (ordini da "
        f"{SOGLIA_B2B} pezzi in su):\n"
        "  Cerca 2 aziende B2B italiane REALI. Per ogni prospect:\n"
        "  - Nome azienda e settore\n"
        "  - Sede (città + regione)\n"
        "  - EMAIL di contatto (OBBLIGATORIA)\n"
        "  - Motivazione dettagliata\n\n"
        "IMPORTANTE: per i prospect B2B l'email è FONDAMENTALE."
    ),
    expected_output=(
        "Lista con 2 profili B2C e 2 prospect B2B. "
        "Per i B2B: nome azienda, settore, sede, EMAIL, motivazione."
    ),
    agent=l_esploratore,
)


# ═══════════════════════════════════════════════
#  Task 2 — Analisi Produzione + Pricing
# ═══════════════════════════════════════════════

analisi_produzione = Task(
    description=(
        "Leggi la configurazione usando il tool 'Leggi Configurazione Produzione'.\n"
        "Riporta nel tuo output:\n"
        "  1. Costo unitario totale\n"
        "  2. Pezzi producibili con il magazzino attuale\n"
        "  3. Tempi di produzione (Bambu Lab A1 Mini: 14 pz / 11 ore)\n"
        "  4. Listino prezzi: vendita singola e scaglioni B2B\n"
        "  5. Analisi ammortamento stampante nuova"
    ),
    expected_output=(
        "Report strutturato con: costo unitario, pezzi producibili, "
        "tempi, listino prezzi, ammortamento."
    ),
    agent=l_analista,
    context=[ricerca_lead],
)


# ═══════════════════════════════════════════════
#  Task 3 — Stesura Messaggi (B2C + B2B)
# ═══════════════════════════════════════════════

stesura_email = Task(
    description=(
        "Per OGNI prospect dell'Esploratore, scrivi un messaggio in italiano.\n\n"
        "PER PROSPECT B2C:\n"
        "  - Tono amichevole, focus uso personale/networking\n"
        "  - Prezzo al pezzo dalla fascia singola dell'Analista\n\n"
        "PER PROSPECT B2B:\n"
        "  - Tono professionale, email a freddo\n"
        "  - Prezzi a scaglioni dall'Analista\n"
        "  - Se sede in PIEMONTE → meeting a Cuneo\n"
        "  - Se fuori Piemonte → videochiamata\n\n"
        "FORMATO OUTPUT PER OGNI MESSAGGIO (segui esattamente):\n"
        "---PROSPECT---\n"
        "TIPO: B2C oppure B2B\n"
        "NOME: nome persona o azienda\n"
        "SETTORE: settore (se B2B)\n"
        "CITTA: città\n"
        "REGIONE: regione\n"
        "EMAIL: indirizzo email (se disponibile)\n"
        "MOTIVAZIONE: perché è un buon prospect\n"
        "OGGETTO_EMAIL: oggetto dell'email\n"
        "CORPO_EMAIL: testo completo del messaggio\n"
        "---FINE_PROSPECT---"
    ),
    expected_output=(
        "Per ogni prospect un blocco ---PROSPECT--- con tutti i campi compilati."
    ),
    agent=il_venditore,
    context=[ricerca_lead, analisi_produzione],
)


# ═══════════════════════════════════════════════
#  Task 4 — Ricerca Innovazione (R&D)
# ═══════════════════════════════════════════════

ricerca_innovazione = Task(
    description=(
        "Cerca sul web le ultime novità nei gadget NFC:\n"
        "  - Card NFC (biglietto da visita digitale)\n"
        "  - Espositori NFC, smart poster, badge eventi\n"
        "  - Gadget B2C (regali tech, accessori)\n\n"
        "Per ogni idea: fornitori, costi, fattibilità, target (B2C/B2B)."
    ),
    expected_output=(
        "Report R&D con 2-3 idee: descrizione, fornitori, costi, "
        "fattibilità, target di vendita."
    ),
    agent=l_innovatore,
)


tutte_le_task = [
    ricerca_lead,
    analisi_produzione,
    stesura_email,
    ricerca_innovazione,
]
