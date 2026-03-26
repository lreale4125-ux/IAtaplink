"""
4 agenti del sistema IAtaplink — NFC Smart Keychains.

Il ruolo di "Capo" (approvazione, invio email, CRM) è gestito dal
bot Telegram (bot.py), non da un agente CrewAI.

Modelli Gemini assegnati per task:
  - Pro (2.5 Pro):        ricerca prospect + copywriting email   → massima qualità
  - Smart (2.5 Flash):    R&D e innovazione                     → buon rapporto
  - Economico (2.5 Flash): calcoli semplici da config            → minimo costo
"""

from crewai import Agent
from crewai_tools import SerperDevTool

from tools import leggi_configurazione

web_search = SerperDevTool()

SEDE = "Cuneo"
REGIONE = "Piemonte"
SOGLIA_B2B = 300

LLM_ECONOMICO = "gemini/gemini-2.5-flash"   # 4K RPM, Unlimited RPD — calcoli
LLM_SMART = "gemini/gemini-2.5-flash"             # 1K RPM, 10K RPD — ricerca R&D
LLM_PRO = "gemini/gemini-2.5-pro"                 # 150 RPM, 1K RPD — lead gen + copywriting


# ═══════════════════════════════════════════════
#  1. L'ESPLORATORE — Lead Generation (PRO)
# ═══════════════════════════════════════════════

l_esploratore = Agent(
    role="L'Esploratore — Agente Lead Generation",
    goal=(
        "Trovare potenziali clienti italiani per portachiavi NFC smart "
        "personalizzabili. Cerchi DUE tipi di prospect:\n"
        f"  A) CLIENTI SINGOLI / PICCOLE ATTIVITÀ (< {SOGLIA_B2B} pz)\n"
        f"  B) AZIENDE B2B (≥ {SOGLIA_B2B} pz)\n"
        "Per ogni prospect B2B è OBBLIGATORIO trovare un indirizzo email reale."
    ),
    backstory=(
        "Sei un esperto di ricerca commerciale nel mercato italiano, sia B2C che B2B. "
        "Sai individuare sia privati/professionisti interessati a gadget tech NFC "
        "sia aziende che organizzano eventi, fiere o onboarding. "
        "Cerchi dati reali e verificabili, mai inventati. "
        "Per i prospect B2B cerchi SEMPRE un indirizzo email di contatto reale, "
        "verificando sui siti web ufficiali delle aziende."
    ),
    tools=[web_search],
    llm=LLM_PRO,
    verbose=True,
    allow_delegation=False,
)


# ═══════════════════════════════════════════════
#  2. L'ANALISTA — Produzione & Logistica (ECONOMICO)
# ═══════════════════════════════════════════════

l_analista = Agent(
    role="L'Analista di Produzione — Agente Logistica",
    goal=(
        "Leggere config.yaml, calcolare costi/magazzino/ammortamento e "
        "proporre un listino prezzi differenziato:\n"
        f"  • Vendita SINGOLA (< {SOGLIA_B2B} pz): margine alto\n"
        f"  • Vendita B2B (≥ {SOGLIA_B2B} pz): scaglioni con margine ridotto"
    ),
    backstory=(
        "Sei un ingegnere di produzione meticoloso. La stampante è una "
        "Bambu Lab A1 Mini. Conosci ogni dettaglio dei costi: elettricità, "
        "filamento PLA, tag NFC, anelli in ferro. Usi SOLO i dati dal "
        "file di configurazione. Calcoli costi unitari, margini e tempi "
        "di produzione con precisione."
    ),
    tools=[leggi_configurazione],
    llm=LLM_ECONOMICO,
    verbose=True,
    allow_delegation=False,
)


# ═══════════════════════════════════════════════
#  3. IL VENDITORE — Outreach & Email (PRO)
# ═══════════════════════════════════════════════

il_venditore = Agent(
    role="Il Venditore — Agente Outreach",
    goal=(
        "Scrivere comunicazioni personalizzate per ogni prospect.\n"
        "  • B2C: tono amichevole, prezzo al pezzo, invito a contattarci.\n"
        "  • B2B: tono professionale, prezzi a scaglioni, regola geografica "
        f"({REGIONE} = meeting a {SEDE}, altrove = videochiamata)."
    ),
    backstory=(
        "Sei un copywriter commerciale esperto in outreach italiano, capace "
        "di adattare il tono sia per il consumatore finale sia per il buyer "
        "aziendale. Scrivi messaggi concisi, diretti e personalizzati. "
        "Non sei aggressivo. Sottolinei il valore concreto dei portachiavi "
        "NFC smart e chiudi con una call-to-action chiara."
    ),
    tools=[],
    llm=LLM_PRO,
    verbose=True,
    allow_delegation=False,
)


# ═══════════════════════════════════════════════
#  4. L'INNOVATORE — Ricerca & Sviluppo (SMART)
# ═══════════════════════════════════════════════

l_innovatore = Agent(
    role="L'Innovatore — Agente Ricerca & Sviluppo",
    goal=(
        "Cercare sul web nuove idee per prodotti NFC e trovare fornitori. "
        "Valuta anche idee adatte alla vendita singola B2C."
    ),
    backstory=(
        "Sei un ricercatore appassionato di innovazione nel campo NFC e IoT. "
        "Monitori costantemente trend tecnologici, nuovi prodotti su Alibaba, "
        "Kickstarter e Product Hunt. Quando trovi un'idea valida, cerchi subito "
        "fornitori e costi dei componenti per valutarne la fattibilità."
    ),
    tools=[web_search],
    llm=LLM_SMART,
    verbose=True,
    allow_delegation=False,
)
