"""
Task sequenziali del sistema NFC Smart Keychains.

Flusso:
  1. Ricerca lead (L'Esploratore)
  2. Analisi produzione (L'Analista)
  3. Stesura email (Il Venditore)       ← usa contesto di 1 + 2
  4. Ricerca innovazione (L'Innovatore)
  5. Approvazione finale (Il Capo)      ← raccoglie tutto, invia su Telegram, attende OK
"""

from crewai import Task

from agents import il_capo, l_analista, l_esploratore, l_innovatore, il_venditore


# ═══════════════════════════════════════════════
#  Task 1 — Ricerca Lead
# ═══════════════════════════════════════════════

ricerca_lead = Task(
    description=(
        "Cerca 3 aziende B2B italiane che potrebbero acquistare portachiavi NFC "
        "smart personalizzabili. Per ogni prospect fornisci:\n"
        "  - Nome azienda e settore\n"
        "  - Sede (città e regione — IMPORTANTISSIMO specificare la regione)\n"
        "  - Contatto (email o profilo LinkedIn di un referente)\n"
        "  - Motivazione: perché questa azienda è un buon target\n\n"
        "Concentrati su: aziende che partecipano a fiere, organizzano eventi corporate, "
        "fanno onboarding di nuovi dipendenti, o cercano gadget tech promozionali."
    ),
    expected_output=(
        "Lista di 3 prospect B2B italiani, ciascuno con: nome azienda, settore, "
        "sede (città + regione), contatto e motivazione dettagliata."
    ),
    agent=l_esploratore,
)


# ═══════════════════════════════════════════════
#  Task 2 — Analisi Produzione
# ═══════════════════════════════════════════════

analisi_produzione = Task(
    description=(
        "Leggi la configurazione di produzione dal file config.yaml usando il tool "
        "'Leggi Configurazione Produzione'. Poi calcola:\n"
        "  1. Costo unitario totale di un portachiavi NFC\n"
        "  2. Quanti pezzi possiamo produrre con il magazzino attuale\n"
        "  3. Tempo necessario per produrre un lotto di 100 pezzi\n"
        "  4. Se un ordine di 500+ pezzi giustifica l'acquisto della stampante nuova "
        "(analisi ammortamento con il nuovo costo unitario)\n\n"
        "Usa ESCLUSIVAMENTE i dati del config.yaml, non inventare numeri."
    ),
    expected_output=(
        "Report di produzione strutturato con: costo unitario completo, "
        "pezzi producibili con il magazzino attuale, tempi di consegna stimati "
        "e analisi ammortamento della stampante nuova."
    ),
    agent=l_analista,
    context=[ricerca_lead],
)


# ═══════════════════════════════════════════════
#  Task 3 — Stesura Email a Freddo
# ═══════════════════════════════════════════════

stesura_email = Task(
    description=(
        "Per OGNI prospect trovato dall'Esploratore, scrivi un'email a freddo "
        "professionale e personalizzata in italiano. L'email deve:\n"
        "  - Menzionare il nome dell'azienda e il motivo per cui li contattiamo\n"
        "  - Spiegare brevemente il prodotto (portachiavi NFC smart)\n"
        "  - Includere il costo indicativo per quantità (dai dati dell'Analista)\n"
        "  - REGOLA GEOGRAFICA OBBLIGATORIA:\n"
        "      • Se il prospect ha sede in PIEMONTE → proponi un meeting dal vivo "
        "a Cuneo\n"
        "      • Se il prospect è FUORI Piemonte → proponi una videochiamata\n"
        "  - Chiudere con una call-to-action chiara\n\n"
        "Formato output per ogni email: DESTINATARIO, OGGETTO, CORPO EMAIL."
    ),
    expected_output=(
        "Per ogni prospect: destinatario (nome + azienda), oggetto dell'email "
        "e corpo completo dell'email con la corretta CTA geografica."
    ),
    agent=il_venditore,
    context=[ricerca_lead, analisi_produzione],
)


# ═══════════════════════════════════════════════
#  Task 4 — Ricerca Innovazione (R&D)
# ═══════════════════════════════════════════════

ricerca_innovazione = Task(
    description=(
        "Cerca sul web le ultime novità nel campo dei gadget NFC. Esplora idee come:\n"
        "  - Card NFC personalizzabili (biglietto da visita digitale)\n"
        "  - Espositori da banco con NFC integrato\n"
        "  - Smart poster NFC per negozi e fiere\n"
        "  - Badge NFC per eventi e conferenze\n"
        "  - Qualsiasi altro gadget innovativo con tecnologia NFC\n\n"
        "Per ogni idea promettente, cerca anche:\n"
        "  - Fornitori di componenti (Alibaba, Made-in-China, ecc.)\n"
        "  - Costo stimato dei materiali\n"
        "  - Livello di difficoltà di realizzazione"
    ),
    expected_output=(
        "Report R&D con 2-3 idee di nuovi prodotti NFC. Per ciascuna: "
        "descrizione del prodotto, fornitori trovati, costi stimati "
        "e valutazione di fattibilità (facile/medio/difficile)."
    ),
    agent=l_innovatore,
)


# ═══════════════════════════════════════════════
#  Task 5 — Approvazione Finale (Human-in-the-Loop)
# ═══════════════════════════════════════════════

approvazione_finale = Task(
    description=(
        "Raccogli TUTTI i risultati delle task precedenti e componi un UNICO "
        "messaggio di resoconto da inviare al fondatore su Telegram.\n\n"
        "Il messaggio DEVE avere queste sezioni:\n\n"
        "--- INIZIO MESSAGGIO ---\n"
        "🎯 PROSPECT TROVATI\n"
        "[Per ogni prospect: nome, sede, motivazione — in forma sintetica]\n\n"
        "🏭 ANALISI PRODUZIONE\n"
        "[Costo unitario, pezzi disponibili, tempi stimati]\n\n"
        "✉️ BOZZE EMAIL\n"
        "[Per ogni prospect: A CHI scriviamo, PERCHÉ ha senso, BOZZA COMPLETA]\n\n"
        "💡 REPORT R&D\n"
        "[Idee trovate, fornitori, fattibilità]\n\n"
        "Rispondi 'OK' o 'Invia' per approvare l'invio delle email.\n"
        "Rispondi 'NO' per bloccare tutto.\n"
        "--- FINE MESSAGGIO ---\n\n"
        "Usa il tool 'richiedi_approvazione_telegram' per inviare questo messaggio "
        "e attendere la risposta del fondatore. Poi riporta la sua decisione."
    ),
    expected_output=(
        "Conferma dell'invio del resoconto su Telegram e risposta del fondatore: "
        "approvazione (OK/Invia) oppure rifiuto (NO) con eventuale motivazione."
    ),
    agent=il_capo,
    context=[ricerca_lead, analisi_produzione, stesura_email, ricerca_innovazione],
)


# Lista ordinata di tutte le task (per import in main.py)
tutte_le_task = [
    ricerca_lead,
    analisi_produzione,
    stesura_email,
    ricerca_innovazione,
    approvazione_finale,
]
