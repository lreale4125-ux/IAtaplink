# IAtaplink — NFC Smart Keychains

Sistema autonomo basato su **CrewAI + Google Gemini**, controllato interamente da **Telegram**.  
Cerca prospect, scrive email personalizzate, le invia dopo approvazione e tiene traccia di tutto in un CRM.

---

## Indice

- [Come funziona](#come-funziona)
- [Architettura](#architettura)
- [Modello di vendita](#modello-di-vendita)
- [Produzione](#produzione)
- [I 4 agenti AI](#i-4-agenti-ai)
- [Modelli Gemini utilizzati](#modelli-gemini-utilizzati)
- [Comandi Telegram](#comandi-telegram)
- [Flusso completo /cerca](#flusso-completo-cerca)
- [Deep Research /rd](#deep-research-rd)
- [CRM Database](#crm-database)
- [Struttura del progetto](#struttura-del-progetto)
- [Setup completo](#setup-completo)
- [Configurazione .env](#configurazione-env)
- [Configurazione config.yaml](#configurazione-configyaml)
- [Avvio](#avvio)
- [Troubleshooting](#troubleshooting)

---

## Come funziona

1. Avvii `python main.py` → il bot Telegram parte e resta in ascolto
2. Scrivi `/cerca` su Telegram → 4 agenti AI cercano prospect, calcolano costi, scrivono email e fanno R&D
3. Il bot ti presenta ogni prospect **uno alla volta** su Telegram
4. Rispondi **OK** → l'email B2B viene inviata automaticamente via SMTP
5. Rispondi **NO** → il prospect viene salvato come bozza nel CRM
6. Tutto viene registrato nel database CRM (SQLite)

Puoi anche lanciare `/rd` per un'analisi approfondita del mercato NFC con Gemini 2.5 Pro.

---

## Architettura

```
                        ┌──────────────┐
                        │   TELEGRAM   │  Tu controlli tutto da qui
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │      bot.py         │  Bot Telegram (loop principale)
                    │  gestisce comandi,  │
                    │  approvazione,      │
                    │  email SMTP, CRM    │
                    └──────────┬──────────┘
                               │  /cerca
                    ┌──────────▼──────────┐
                    │      CrewAI         │  Framework multi-agente
                    │  4 agenti in        │
                    │  sequenza           │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
    │ Esploratore│      │  Venditore  │     │ Innovatore  │
    │ (2.5 Pro) │      │  (2.5 Pro)  │     │ (2.5 Flash) │
    │ cerca lead │      │ scrive email│     │ R&D prodotti│
    └───────────┘      └─────────────┘     └─────────────┘
          │
    ┌─────▼─────┐      ┌─────────────┐     ┌─────────────┐
    │  Analista  │      │   Serper    │     │    SQLite   │
    │ (2.0 FLite)│      │  (ricerca)  │     │    (CRM)    │
    │ costi/prezzi│     └─────────────┘     └─────────────┘
    └───────────┘
```

---

## Modello di vendita

Il sistema utilizza un **modello di vendita duale**:

| | Vendita Singola (B2C) | Vendita B2B |
|---|---|---|
| **Quantità** | 1 — 299 pezzi | 300+ pezzi |
| **Target** | Privati, freelancer, piccole attività | Aziende (fiere, eventi, onboarding) |
| **Margine** | 70% (prezzo pieno) | Scaglioni: -20%, -30%, -40% |
| **Outreach** | Tono amichevole, social/e-commerce | Email professionale automatica |
| **Regola geografica** | — | Piemonte = meeting Cuneo, altrove = videochiamata |

### Listino prezzi calcolato

Con il costo unitario attuale di **€0.407/pz**:

| Fascia | Prezzo/pz | Sconto |
|--------|-----------|--------|
| Vendita singola (1-299 pz) | ~€1.36 | — |
| B2B 300-499 pz | ~€1.09 | -20% |
| B2B 500-999 pz | ~€0.95 | -30% |
| B2B 1000+ pz | ~€0.81 | -40% |

*I prezzi sono configurabili in `config.yaml`.*

---

## Produzione

| Dato | Valore |
|------|--------|
| **Stampante** | Bambu Lab A1 Mini |
| **Batch** | 14 pezzi per batch |
| **Tempo batch** | 11 ore |
| **Tempo per 100 pz** | ~88 ore (8 batch) |

### Costi unitari di produzione

| Componente | Costo/pz | Note |
|-----------|----------|------|
| Elettricità | €0.01 | ~stima per stampa |
| Filamento PLA | €0.30 | Refill 4-5 rotoli @ €14.94/kg, ~50 pz/kg |
| Tag NFC | €0.07 | 100 pz = €7.00 |
| Anello ferro | €0.027 | 100 pz = €2.67 |
| **TOTALE** | **€0.407** | |

### Listino filamento Bambu Lab PLA (refill senza bobina)

| Quantità | Prezzo | Sconto |
|----------|--------|--------|
| 1-3 rotoli | €22.99 | Listino |
| 4-5 rotoli | €14.94 | -35% |
| 6-9 rotoli | €12.64 | -45% |
| 10+ rotoli | €11.50 | -50% |

---

## I 4 agenti AI

| # | Agente | Cosa fa | Modello | Tool |
|---|--------|---------|---------|------|
| 1 | **L'Esploratore** | Cerca prospect B2C (profili tipo) e B2B (aziende reali con email) | Gemini 2.5 Pro | Serper Search |
| 2 | **L'Analista** | Legge config.yaml, calcola costi, produce listino prezzi | Gemini 2.0 Flash Lite | Config Reader |
| 3 | **Il Venditore** | Scrive email personalizzate per ogni prospect | Gemini 2.5 Pro | — |
| 4 | **L'Innovatore** | Cerca nuovi prodotti NFC, fornitori, trend | Gemini 2.5 Flash | Serper Search |

Il ruolo di "Capo" (approvazione, invio email, salvataggio CRM) è gestito dal bot Telegram — è logica deterministica, non serve un agente AI.

---

## Modelli Gemini utilizzati

| Modello | Usato per | RPM | RPD | Perché |
|---------|-----------|-----|-----|--------|
| **Gemini 2.5 Pro** | Esploratore, Venditore | 150 | 1K | Massima intelligenza per trovare prospect reali e scrivere email persuasive |
| **Gemini 2.5 Flash** | Innovatore | 1K | 10K | Buon rapporto qualità/velocità per ricerca R&D |
| **Gemini 2.0 Flash Lite** | Analista, parsing JSON | 4K | Unlimited | Calcoli semplici e parsing, minimo costo |
| **Gemini 2.5 Pro** | Deep Research (/rd) | 150 | 1K | Analisi di mercato approfondita |

---

## Comandi Telegram

| Comando | Descrizione |
|---------|-------------|
| `/cerca` | Lancia i 4 agenti AI, poi presenta ogni prospect per approvazione |
| `/rd` | Deep Research: analisi completa del mercato NFC con Gemini 2.5 Pro |
| `/stats` | Mostra statistiche dal CRM (prospect, email, sessioni) |
| `/help` | Lista dei comandi disponibili |

### Risposte durante l'approvazione

| Risposta | Effetto |
|----------|---------|
| `OK` / `SÌ` / `YES` / `S` / `INVIA` | Approva. Se B2B con email → invia automaticamente |
| `NO` / qualsiasi altro testo | Rifiuta. Salva come bozza nel CRM |

---

## Flusso completo /cerca

```
Tu: /cerca
│
Bot: "🔍 Avvio ricerca prospect..."
│
├── CrewAI: Esploratore cerca 2 profili B2C + 2 aziende B2B
├── CrewAI: Analista calcola costi e listino prezzi
├── CrewAI: Venditore scrive email personalizzate
├── CrewAI: Innovatore cerca nuovi prodotti NFC
│
Bot: "🏭 ANALISI PRODUZIONE" → report costi e prezzi
Bot: "💡 REPORT R&D" → nuove idee prodotto
│
Bot: "📋 Trovati 4 prospect. Li esaminiamo uno alla volta."
│
├── "🏢 Prospect 1/4 (B2B)"
│   Nome: Acme Srl
│   Sede: Milano, Lombardia
│   Email: info@acme.it
│   📧 Email da inviare: [bozza completa]
│   ✅ OK per approvare e inviare  /  ❌ NO per rifiutare
│
│   Tu: OK
│   Bot: "✅ Email inviata a info@acme.it"
│   → Salvato nel CRM con stato "inviato"
│
├── "👤 Prospect 2/4 (B2C)"
│   Nome: Professionisti freelancer
│   📧 Messaggio: [bozza]
│   Tu: OK
│   Bot: "✅ Prospect B2C approvato e salvato nel CRM."
│
├── ... (altri prospect)
│
Bot: "━━━ SESSIONE COMPLETATA ━━━"
     Prospect esaminati: 4
     Approvati: 3
     Email inviate: 2
     Errori email: 0
```

---

## Deep Research /rd

Il comando `/rd` lancia un'analisi di mercato approfondita usando **Gemini 2.5 Pro** direttamente (non via CrewAI). L'analisi copre:

1. **Mercato NFC Italia 2026** — dimensione, trend, segmenti
2. **Concorrenza** — competitor, prodotti, prezzi, differenziazione
3. **Target B2C** — buyer persona, canali, pricing, marketing
4. **Target B2B** — settori, dimensioni aziende, decision maker
5. **Nuovi prodotti NFC** — idee, fornitori, costi, fattibilità
6. **Canali di vendita** — online, offline, omnicanale
7. **Raccomandazioni strategiche** — azioni immediate, piano 6 mesi, rischi

Il report viene inviato direttamente su Telegram, diviso in parti se troppo lungo.

---

## CRM Database

Il file `crm.db` viene creato automaticamente nella cartella del progetto.

### Tabelle

| Tabella | Campi principali | Descrizione |
|---------|------------------|-------------|
| `prospect` | nome, tipo (B2C/B2B), settore, sede, contatto, motivazione, stato | Tutti i prospect trovati |
| `messaggio` | prospect_id, canale, destinatario, oggetto, corpo, stato, data_invio | Email/messaggi con stato (bozza/inviato/errore) |
| `sessione` | data, prospect_b2c, prospect_b2b, email_inviate, email_errori, approvazione | Log di ogni esecuzione di /cerca |

### Accesso ai dati

I dati sono in SQLite — puoi consultarli con qualsiasi client SQLite (DB Browser, DBeaver, linea di comando `sqlite3 crm.db`).

---

## Struttura del progetto

```
AiProdoct/
│
├── main.py              # Entry point: carica .env, valida config, avvia bot
├── bot.py               # Bot Telegram: comandi, approvazione, email SMTP, CRM, deep research
├── agents.py            # 4 agenti CrewAI con modelli Gemini ottimizzati
├── tasks.py             # 4 task sequenziali con output strutturato
├── tools.py             # Tool CrewAI: lettore config.yaml con calcolo listino
├── crm.py               # CRM SQLite: prospect, messaggi, sessioni
│
├── config.yaml          # Configurazione produzione (A1 Mini, costi reali, listino)
├── requirements.txt     # Dipendenze Python
├── .env                 # Variabili d'ambiente (NON committare!)
├── .env.example         # Template .env
├── .gitignore           # Esclude .env, crm.db, __pycache__, ecc.
│
└── crm.db               # Database CRM (creato automaticamente)
```

### Dipendenze dei file

```
main.py
  └── bot.py
        ├── agents.py
        │     └── tools.py (leggi_configurazione)
        │           └── config.yaml
        ├── tasks.py
        │     └── agents.py
        ├── crm.py
        │     └── crm.db (SQLite)
        └── google.generativeai (parsing JSON + deep research)
```

---

## Setup completo

### 1. Prerequisiti

- Python 3.11+ installato
- Un account Google (per Gemini API — gratuita)
- Un account Telegram
- Un account email con SMTP attivo (Gmail consigliato)

### 2. Clona e prepara l'ambiente

```bash
cd C:\Users\sacca\Desktop\iataplink\IAtaplink\AiProdoct

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 3. Configura il .env

Copia `.env.example` in `.env` e compila tutti i valori (vedi sezione sotto).

### 4. Avvia

```bash
python main.py
```

Poi apri Telegram e scrivi `/cerca` al bot.

---

## Configurazione .env

| Variabile | Descrizione | Come ottenerla |
|-----------|-------------|----------------|
| `GOOGLE_API_KEY` | Chiave API Google Gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — gratuita, 1500 req/giorno con 2.5 Pro |
| `TELEGRAM_BOT_TOKEN` | Token del bot Telegram | Crea un bot con [@BotFather](https://t.me/BotFather) su Telegram |
| `TELEGRAM_CHAT_ID` | Il tuo ID chat Telegram | Manda `/start` al bot, poi visita `https://api.telegram.org/bot<TOKEN>/getUpdates` — cerca `"chat":{"id":123456}` |
| `SERPER_API_KEY` | Chiave per ricerca web | [serper.dev](https://serper.dev/) — 2500 ricerche gratis |
| `SMTP_HOST` | Server SMTP | `smtp.gmail.com` (Gmail) oppure `smtp-mail.outlook.com` (Outlook) |
| `SMTP_PORT` | Porta SMTP | `587` (standard TLS) |
| `SMTP_USER` | Indirizzo email mittente | La tua email (es. `tuonome@gmail.com`) |
| `SMTP_PASSWORD` | App Password | **NON** la password normale! Vedi sotto |
| `SMTP_SENDER_NAME` | Nome visualizzato | Es. `IAtaplink — NFC Smart Keychains` |

### Come creare un'App Password Gmail

1. Vai su [myaccount.google.com](https://myaccount.google.com/)
2. Sicurezza → Verifica in due passaggi (attivala se non l'hai)
3. Cerca "Password per le app" (o vai su [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))
4. Crea una password per "Posta" → "Windows Computer"
5. Copia la password di 16 caratteri nel `.env` come `SMTP_PASSWORD`

---

## Configurazione config.yaml

Il file `config.yaml` contiene tutti i dati di produzione. I valori attuali sono configurati per la tua situazione specifica (A1 Mini, costi reali).

| Sezione | Cosa contiene | Quando modificare |
|---------|---------------|-------------------|
| `azienda` | Nome, sede, regione | Se cambi sede |
| `vendita` | Soglia B2B (300), margini, scaglioni | Se vuoi cambiare i prezzi |
| `costi` | Costi unitari per componente | Se cambiano i prezzi dei fornitori |
| `filamento` | Listino filamento per quantità | Se cambia il listino Bambu Lab |
| `magazzino` | Scorte attuali | Aggiorna dopo ogni acquisto/produzione |
| `produzione` | Stampante, batch, tempi | Se cambi stampante o setup |
| `ammortamento` | Costo stampante nuova, target | Se acquisti nuova stampante |

---

## Avvio

```bash
# Attiva l'ambiente virtuale
.venv\Scripts\activate

# Avvia il bot
python main.py
```

Il bot stamperà nel terminale:
```
🚀 NFC Smart Keychains — Avvio Bot Telegram
   Il bot resta in ascolto su Telegram.
   Scrivi /cerca sul bot per avviare una ricerca.
   Premi Ctrl+C per fermare.

🤖 Bot Telegram in ascolto...
```

Su Telegram riceverai:
```
🤖 IAtaplink — NFC Smart Keychains Bot attivo!

Comandi:
  /cerca — Avvia ricerca prospect (4 agenti AI)
  /rd — Deep Research mercato NFC (Gemini 2.5 Pro)
  /stats — Statistiche CRM
  /help — Mostra comandi
```

Per fermare il bot: premi **Ctrl+C** nel terminale.

---

## Troubleshooting

| Problema | Soluzione |
|----------|----------|
| `❌ GOOGLE_API_KEY mancante` | Compila il .env con la chiave da [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `❌ TELEGRAM_BOT_TOKEN mancante` | Crea un bot con @BotFather e copia il token |
| `⚠️ SMTP incompleto` | Configura SMTP_HOST, SMTP_USER, SMTP_PASSWORD nel .env |
| `ERRORE: credenziali SMTP` | Verifica che l'App Password sia corretta (16 caratteri, senza spazi) |
| Il bot non risponde su Telegram | Verifica che TELEGRAM_CHAT_ID sia corretto. Manda /start al bot e ricontrolla |
| Email non arrivano | Controlla la cartella spam. Verifica che SMTP_USER sia l'email corretta |
| `Errore polling Telegram` | Problema di rete temporaneo — il bot riprova automaticamente |
| CrewAI timeout | I modelli Pro possono essere lenti. Aspetta qualche minuto |
| `quota exceeded` | Hai superato i limiti RPM/RPD di Gemini. Aspetta qualche minuto o usa modelli Flash |
| Prospect senza email | L'Esploratore non ha trovato email. Puoi rifiutare (NO) e cercare di nuovo |

---

## Stack tecnologico

| Componente | Tecnologia | Versione |
|-----------|------------|----------|
| LLM principale | Google Gemini 2.5 Pro | via LiteLLM |
| LLM economico | Google Gemini 2.0 Flash Lite | via LiteLLM |
| Framework agenti | CrewAI | ≥ 0.80 |
| Ricerca web | Serper.dev | via crewai_tools |
| Bot | Telegram Bot API | polling con requests |
| Email | SMTP (Gmail/Outlook) | smtplib Python |
| Database | SQLite | crm.py |
| Config | YAML | config.yaml |
