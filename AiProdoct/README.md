# NFC Smart Keychains — Sistema Multi-Agente

Sistema autonomo basato su **CrewAI** per gestire vendite, logistica e R&D di una startup B2B che produce portachiavi NFC smart personalizzabili per aziende.

## Struttura del progetto

```
AiProdoct/
  main.py              # Entrypoint: carica config, valida env, avvia la Crew
  agents.py            # Definizione dei 5 agenti con ruoli e tool
  tasks.py             # 5 task sequenziali con dipendenze di contesto
  tools.py             # Tool personalizzati: Telegram approval + config reader
  config.yaml          # Configurazione business (costi, magazzino, produzione)
  requirements.txt     # Dipendenze Python
  .env.example         # Template variabili d'ambiente
  .gitignore
```

## I 5 agenti

| # | Nome | Ruolo | Tool |
|---|------|-------|------|
| 1 | **Il Capo** | Direttore Operativo — coordina il team, invia resoconto su Telegram, attende approvazione | `TelegramApprovalTool` |
| 2 | **L'Esploratore** | Lead Generation — cerca aziende B2B target con contatti e motivazione | `SerperDevTool` |
| 3 | **Il Venditore** | Outreach — scrive email a freddo personalizzate con regola geografica | — |
| 4 | **L'Analista** | Produzione & Logistica — calcola costi, magazzino, ammortamento | `leggi_configurazione` |
| 5 | **L'Innovatore** | R&D — cerca nuove idee per gadget NFC e fornitori componenti | `SerperDevTool` |

## Flusso di esecuzione

```
Esploratore ──→ Analista ──→ Venditore ──→ Innovatore ──→ Capo
  (lead)        (costi)      (email)       (R&D)         (Telegram → attesa OK)
```

1. **L'Esploratore** cerca 3 prospect B2B italiani con motivazione
2. **L'Analista** legge `config.yaml`, calcola costi/magazzino/ammortamento
3. **Il Venditore** scrive email personalizzate rispettando la regola geografica:
   - Prospect in Piemonte → propone meeting dal vivo a Cuneo
   - Prospect fuori Piemonte → propone videochiamata
4. **L'Innovatore** cerca nuove idee prodotto NFC e fornitori
5. **Il Capo** raccoglie tutto, invia su Telegram e **attende l'approvazione** del fondatore

## Regole di business

- **Approvazione obbligatoria**: nessuna email viene inviata senza OK su Telegram
- **Regola geografica**: Piemonte = meeting dal vivo a Cuneo; altrimenti = videochiamata
- **Il sistema tecnico di redirect NFC è gestito esternamente** — gli agenti non toccano database o codice web

## Setup

1. Installa le dipendenze:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

2. Configura le variabili d'ambiente:
   - Copia `.env.example` in `.env`
   - Compila: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SERPER_API_KEY`

3. Personalizza `config.yaml` con i tuoi dati reali di produzione

## Avvio

```bash
python main.py
```

Il sistema eseguira i 5 agenti in sequenza. Alla fine, riceverai un messaggio su Telegram con il resoconto completo e potrai rispondere **OK** per approvare o **NO** per bloccare.

## Configurazione (`config.yaml`)

| Sezione | Contenuto |
|---------|-----------|
| `azienda` | Nome, sede, descrizione |
| `costi` | Elettricita, filamento, NFC, anello ferro (EUR/pezzo) |
| `magazzino` | Quantita attuali di materiali |
| `produzione` | Capacita batch stampante, tempo per batch |
| `ammortamento` | Costo stampante nuova, target vendite, costo unitario obiettivo |
