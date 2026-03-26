"""
Task del sistema NFC Smart Keychains — suddivise per comando Telegram.
Comunicazione inter-agente in formato TOON (Token-Oriented Object Notation).

  /cerca   → task_cerca:   ricerca lead + analisi + stesura email
  /analisi → task_analisi: solo analisi produzione + listino
  /idee    → task_idee:    solo ricerca innovazione R&D
"""

from crewai import Task

from agents import l_analista, l_esploratore, l_innovatore, il_venditore

SOGLIA_B2B = 300

TOON_INTRO = (
    "IMPORTANTE: rispondi usando formato TOON (Token-Oriented Object Notation) "
    "per dati strutturati. TOON usa indentazione per oggetti annidati e "
    "header tabulari per array uniformi. Esempio:\n"
    "campo: valore\n"
    "lista[2]{col1,col2}:\n"
    "  valore1,valore2\n"
    "  valore3,valore4\n\n"
)


# ═══════════════════════════════════════════════
#  Ricerca Lead (B2C + B2B)
# ═══════════════════════════════════════════════

ricerca_lead = Task(
    description=(
        TOON_INTRO
        + "Cerca potenziali clienti italiani per portachiavi NFC smart.\n\n"
        "CATEGORIA A — VENDITA SINGOLA (B2C):\n"
        "  Cerca 2 profili di potenziali clienti singoli:\n"
        "  - Professionisti/freelancer, piccoli negozi, influencer\n\n"
        "CATEGORIA B — VENDITA B2B (ordini da "
        f"{SOGLIA_B2B} pezzi in su):\n"
        "  Cerca 2 aziende B2B italiane REALI.\n"
        "  Per i B2B l'EMAIL di contatto è OBBLIGATORIA.\n\n"
        "OUTPUT in formato TOON:\n"
        "prospect[N]{tipo,nome,settore,sede_citta,sede_regione,contatto_email,motivazione}:\n"
        "  B2C,Nome Persona,settore,citta,regione,,motivazione\n"
        "  B2B,Nome Azienda,settore,citta,regione,email@azienda.it,motivazione"
    ),
    expected_output=(
        "Tabella TOON con 4 prospect (2 B2C + 2 B2B). "
        "Campi: tipo, nome, settore, sede_citta, sede_regione, contatto_email, motivazione."
    ),
    agent=l_esploratore,
)


# ═══════════════════════════════════════════════
#  Analisi Produzione + Pricing
# ═══════════════════════════════════════════════

analisi_produzione = Task(
    description=(
        TOON_INTRO
        + "Leggi la configurazione usando il tool 'Leggi Configurazione Produzione'.\n"
        "Il tool restituisce dati già in formato TOON.\n\n"
        "Riporta nel tuo output TOON:\n"
        "  1. Costo unitario totale\n"
        "  2. Pezzi producibili con il magazzino attuale\n"
        "  3. Tempi di produzione (Bambu Lab A1 Mini: 14 pz / 11 ore)\n"
        "  4. Listino prezzi: vendita singola e scaglioni B2B\n"
        "  5. Analisi ammortamento stampante nuova"
    ),
    expected_output=(
        "Report in formato TOON con: costo unitario, pezzi producibili, "
        "tempi, listino prezzi, ammortamento."
    ),
    agent=l_analista,
    context=[ricerca_lead],
)


# ═══════════════════════════════════════════════
#  Stesura Messaggi (B2C + B2B)
# ═══════════════════════════════════════════════

stesura_email = Task(
    description=(
        TOON_INTRO
        + "Per OGNI prospect dell'Esploratore, scrivi un messaggio in italiano.\n\n"
        "PER PROSPECT B2C:\n"
        "  - Tono amichevole, focus uso personale/networking\n"
        "  - Prezzo al pezzo dalla fascia singola dell'Analista\n\n"
        "PER PROSPECT B2B:\n"
        "  - Tono professionale, email a freddo\n"
        "  - Prezzi a scaglioni dall'Analista\n"
        "  - Se sede in PIEMONTE → meeting a Cuneo\n"
        "  - Se fuori Piemonte → videochiamata\n\n"
        "FORMATO OUTPUT TOON (segui esattamente):\n\n"
        "prospects[N]{tipo,nome,settore,sede_citta,sede_regione,contatto_email,"
        "motivazione,email_oggetto,email_corpo}:\n"
        '  B2B,Azienda Srl,Tech,Milano,Lombardia,info@az.it,motivazione,'
        '"NFC Smart Keychains - Proposta","Gentile... testo completo email"\n'
        '  B2C,Mario Rossi,Freelance,Roma,Lazio,,motivazione,'
        '"Portachiavi NFC Smart","Ciao Mario... testo completo"\n\n'
        "REGOLE:\n"
        "- Usa virgolette per valori che contengono virgole\n"
        "- email_corpo deve essere il testo COMPLETO del messaggio\n"
        "- N deve corrispondere al numero di prospect"
    ),
    expected_output=(
        "Tabella TOON prospects[N]{...}: con tutti i campi per ogni prospect."
    ),
    agent=il_venditore,
    context=[ricerca_lead, analisi_produzione],
)


# ═══════════════════════════════════════════════
#  Analisi Produzione standalone (per /analisi)
# ═══════════════════════════════════════════════

analisi_standalone = Task(
    description=(
        TOON_INTRO
        + "Leggi la configurazione usando il tool 'Leggi Configurazione Produzione'.\n"
        "Il tool restituisce dati già in formato TOON.\n\n"
        "Riporta nel tuo output TOON:\n"
        "  1. Costo unitario totale (elettricità + filamento + NFC + anello)\n"
        "  2. Pezzi producibili con il magazzino attuale\n"
        "  3. Tempi di produzione (Bambu Lab A1 Mini: 14 pz / 11 ore)\n"
        "  4. Listino prezzi: vendita singola (margine 70%) e scaglioni B2B\n"
        "  5. Analisi ammortamento stampante nuova\n"
        "  6. Collo di bottiglia e suggerimenti per scalare"
    ),
    expected_output=(
        "Report in formato TOON con: costo unitario, pezzi producibili, "
        "tempi, listino prezzi, ammortamento, suggerimenti."
    ),
    agent=l_analista,
)


# ═══════════════════════════════════════════════
#  Ricerca Innovazione standalone (per /idee)
# ═══════════════════════════════════════════════

ricerca_innovazione = Task(
    description=(
        TOON_INTRO
        + "Cerca sul web le ultime novità nei gadget NFC.\n\n"
        "OUTPUT in formato TOON:\n"
        "idee[N]{nome,descrizione,target,fornitori,costo_stimato,fattibilita}:\n"
        '  Card NFC,"Biglietto da visita digitale NFC",B2C+B2B,Alibaba/AliExpress,0.50-2.00 EUR,alta\n'
        '  Smart Poster,"Poster con tag NFC per info interattive",B2B,NXP/STMicro,3.00-5.00 EUR,media\n\n'
        "Cerca almeno 3 idee con fornitori reali e costi verificati."
    ),
    expected_output=(
        "Tabella TOON idee[N]{...}: con 2-3 idee NFC innovative, "
        "fornitori, costi e fattibilità."
    ),
    agent=l_innovatore,
)


# Gruppi di task per ogni comando
task_cerca = [ricerca_lead, analisi_produzione, stesura_email]
task_analisi = [analisi_standalone]
task_idee = [ricerca_innovazione]
