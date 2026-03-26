"""
Bot Telegram per IAtaplink — NFC Smart Keychains.

Controlla l'intero sistema multi-agente da Telegram:
  /cerca   → ricerca prospect + email, approva/rifiuta uno alla volta
  /analisi → report produzione, costi, listino prezzi
  /idee    → report R&D nuovi prodotti NFC
  /rd      → deep research mercato NFC con Gemini 2.5 Pro
  /export  → scarica file JSON con tutti i prospect e stato email
  /stats   → statistiche CRM
  /help    → comandi disponibili

Dopo l'approvazione di un prospect B2B, l'email viene inviata automaticamente.
Tutti i prospect vengono salvati nel CRM (SQLite).
"""

import json
import os
import re
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

POLLING_TIMEOUT_SEC = 30
TELEGRAM_MAX_LEN = 4096


class NfcBot:
    """Bot Telegram che orchestra ricerca, approvazione, invio email e CRM."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.base = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

        if not self.token or not self.chat_id:
            print("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati nel .env")
            sys.exit(1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Loop principale
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def run(self):
        """Avvia il bot in polling continuo."""
        from crm import init_db
        init_db()

        self._flush_updates()
        self.invia(
            "🤖 IAtaplink — NFC Smart Keychains Bot attivo!\n\n"
            "Comandi:\n"
            "  /cerca — Ricerca prospect + email\n"
            "  /analisi — Report produzione e listino\n"
            "  /idee — Nuovi prodotti NFC (R&D)\n"
            "  /rd — Deep Research mercato NFC\n"
            "  /export — Scarica file prospect\n"
            "  /stats — Statistiche CRM\n"
            "  /help — Mostra comandi"
        )
        print("🤖 Bot Telegram in ascolto...")

        while True:
            try:
                testo = self._poll_message()
                if testo:
                    self._gestisci_comando(testo)
            except KeyboardInterrupt:
                self.invia("👋 Bot in fase di spegnimento.")
                print("\n👋 Bot fermato.")
                break
            except Exception as e:
                print(f"⚠️ Errore nel loop principale: {e}")
                time.sleep(5)

    def _gestisci_comando(self, testo: str):
        cmd = testo.strip().lower()
        if cmd in ("/cerca", "cerca", "/start"):
            self._processo_ricerca()
        elif cmd in ("/analisi", "analisi"):
            self._processo_analisi()
        elif cmd in ("/idee", "idee"):
            self._processo_idee()
        elif cmd in ("/rd", "rd", "/research", "research"):
            self._deep_research()
        elif cmd in ("/export", "export"):
            self._esporta_prospect()
        elif cmd in ("/stats", "stats"):
            self._mostra_stats()
        elif cmd in ("/help", "help", "?"):
            self._mostra_help()
        else:
            self.invia("Comando non riconosciuto. Scrivi /help per i comandi.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Processo di ricerca completo
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _processo_ricerca(self):
        self.invia(
            "🔍 Avvio ricerca prospect...\n"
            "Ci vorranno alcuni minuti. Ti avviso appena ho i risultati."
        )

        try:
            from tasks import task_cerca
            task_outputs = self._esegui_crew(task_cerca)
        except Exception as e:
            self.invia(f"❌ Errore durante la ricerca:\n{e}")
            return

        output_ricerca = task_outputs[0] if len(task_outputs) > 0 else ""
        output_email = task_outputs[2] if len(task_outputs) > 2 else ""

        prospects = self._parse_prospects(output_email, output_ricerca)

        if not prospects:
            self.invia(
                "⚠️ Non sono riuscito a estrarre i prospect strutturati.\n"
                "Ecco l'output grezzo delle email:"
            )
            self.invia(self._tronca(output_email))
            return

        self.invia(f"📋 Trovati {len(prospects)} prospect. Li esaminiamo uno alla volta.")

        approvati = 0
        email_ok = 0
        email_err = 0

        for i, p in enumerate(prospects, 1):
            self.invia(self._formatta_prospect(p, i, len(prospects)))

            risposta = self._poll_message(timeout=3600)
            if not risposta:
                self.invia("⏰ Timeout. Salvo come bozza e passo al prossimo.")
                self._salva_crm(p, inviata=False)
                continue

            if risposta.strip().upper() in ("OK", "SI", "SÌ", "YES", "S", "Y", "INVIA"):
                approvati += 1

                if p.get("tipo", "").upper() == "B2B" and p.get("contatto_email"):
                    esito = self._invia_email_smtp(
                        p["contatto_email"],
                        p.get("email_oggetto", "NFC Smart Keychains — Proposta"),
                        p.get("email_corpo", ""),
                    )
                    if esito.startswith("OK"):
                        email_ok += 1
                        self.invia(f"✅ Approvato! Email inviata a {p['contatto_email']}")
                    else:
                        email_err += 1
                        self.invia(f"✅ Approvato, ma errore email: {esito}")
                    self._salva_crm(p, inviata=esito.startswith("OK"))
                else:
                    tipo = p.get("tipo", "").upper()
                    self._salva_crm(p, inviata=False)
                    if tipo == "B2C":
                        self.invia("✅ Prospect B2C approvato e salvato nel CRM.")
                    else:
                        self.invia("✅ Approvato e salvato (email non disponibile).")
            else:
                self._salva_crm(p, inviata=False)
                self.invia("❌ Rifiutato. Salvato nel CRM come bozza.")

        from crm import registra_sessione
        registra_sessione(
            prospect_b2c=sum(1 for p in prospects if p.get("tipo", "").upper() == "B2C"),
            prospect_b2b=sum(1 for p in prospects if p.get("tipo", "").upper() == "B2B"),
            email_inviate=email_ok,
            email_errori=email_err,
            approvazione=f"approvati {approvati}/{len(prospects)}",
        )

        self.invia(
            "━━━ SESSIONE COMPLETATA ━━━\n"
            f"📊 Prospect esaminati: {len(prospects)}\n"
            f"✅ Approvati: {approvati}\n"
            f"📧 Email inviate: {email_ok}\n"
            f"❌ Errori email: {email_err}\n\n"
            "Scrivi /cerca per una nuova ricerca."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Esecuzione CrewAI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _esegui_crew(self, tasks: list) -> list[str]:
        """Lancia la crew CrewAI con le task fornite e restituisce gli output."""
        from crewai import Crew, Process

        agents = list({t.agent for t in tasks})

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()

        outputs = []
        if hasattr(result, "tasks_output"):
            for to in result.tasks_output:
                outputs.append(str(to.raw) if hasattr(to, "raw") else str(to))
        else:
            outputs.append(str(result))

        return outputs

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Parsing dei prospect dall'output CrewAI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _parse_prospects(self, email_output: str, search_output: str) -> list[dict]:
        """
        Parsing a cascata: TOON → delimitatori legacy → Gemini fallback.
        """
        prospects = self._parse_toon(email_output)
        if prospects:
            return prospects

        prospects = self._parse_con_delimitatori(email_output)
        if prospects:
            return prospects

        return self._parse_con_gemini(email_output, search_output)

    @staticmethod
    def _parse_toon(testo: str) -> list[dict]:
        """Parsing del formato TOON (prospects[N]{...}: ...)."""
        try:
            from toon_format import decode as toon_decode

            if "prospects[" not in testo and "{" not in testo:
                return []

            match = re.search(
                r"(prospects\[\d+\]\{[^}]+\}:.*?)(?:\n\n|\Z)",
                testo,
                re.DOTALL,
            )
            if not match:
                return []

            decoded = toon_decode(match.group(1))
            prospects = decoded.get("prospects", []) if isinstance(decoded, dict) else decoded
            if isinstance(prospects, list) and prospects:
                return prospects
        except Exception as e:
            print(f"⚠️ Errore parsing TOON: {e}")
        return []

    @staticmethod
    def _parse_con_delimitatori(testo: str) -> list[dict]:
        """Parsing basato sui delimitatori ---PROSPECT--- / ---FINE_PROSPECT---."""
        blocchi = re.findall(
            r"---PROSPECT---(.*?)---FINE_PROSPECT---",
            testo,
            re.DOTALL,
        )
        if not blocchi:
            return []

        campi_map = {
            "TIPO": "tipo",
            "NOME": "nome",
            "SETTORE": "settore",
            "CITTA": "sede_citta",
            "CITTÀ": "sede_citta",
            "REGIONE": "sede_regione",
            "EMAIL": "contatto_email",
            "MOTIVAZIONE": "motivazione",
            "OGGETTO_EMAIL": "email_oggetto",
            "OGGETTO EMAIL": "email_oggetto",
            "CORPO_EMAIL": "email_corpo",
            "CORPO EMAIL": "email_corpo",
        }

        prospects = []
        for blocco in blocchi:
            p = {}
            for riga in blocco.strip().split("\n"):
                riga = riga.strip()
                if ":" in riga:
                    chiave, _, valore = riga.partition(":")
                    chiave_norm = chiave.strip().upper()
                    if chiave_norm in campi_map:
                        campo = campi_map[chiave_norm]
                        if campo == "email_corpo" and p.get("email_corpo"):
                            p["email_corpo"] += "\n" + valore.strip()
                        else:
                            p[campo] = valore.strip()
                elif p.get("email_corpo") is not None:
                    p["email_corpo"] = p.get("email_corpo", "") + "\n" + riga

            if p.get("nome"):
                prospects.append(p)

        return prospects

    def _parse_con_gemini(self, email_output: str, search_output: str) -> list[dict]:
        """Fallback: usa Gemini 2.5 Flash per estrarre i prospect via TOON."""
        try:
            import google.generativeai as genai
            from toon_format import decode as toon_decode

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = (
                "Analizza questi output e estrai TUTTI i prospect trovati.\n"
                "Rispondi SOLO in formato TOON (Token-Oriented Object Notation).\n\n"
                f"OUTPUT RICERCA:\n{search_output[:3000]}\n\n"
                f"OUTPUT EMAIL:\n{email_output[:3000]}\n\n"
                "Rispondi con ESATTAMENTE questo formato TOON (niente markdown, niente ```):\n\n"
                "prospects[N]{nome,tipo,settore,sede_citta,sede_regione,contatto_email,motivazione,email_oggetto,email_corpo}:\n"
                '  nome azienda,B2B,settore,citta,regione,email@example.com,motivazione,"oggetto email","corpo email completo"\n\n'
                "Dove N è il numero di prospect trovati. Usa le virgolette per valori con virgole."
            )

            response = model.generate_content(prompt)
            testo = response.text.strip()

            if testo.startswith("```"):
                testo = re.sub(r"^```(?:toon|json)?\s*", "", testo)
                testo = re.sub(r"\s*```$", "", testo)

            try:
                decoded = toon_decode(testo)
                prospects = decoded.get("prospects", decoded) if isinstance(decoded, dict) else decoded
                if isinstance(prospects, list):
                    return prospects
            except Exception:
                pass

            return json.loads(testo) if testo.startswith("[") else []
        except Exception as e:
            print(f"⚠️ Errore parsing Gemini/TOON: {e}")
            return []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Formattazione messaggi Telegram
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _formatta_prospect(p: dict, idx: int, tot: int) -> str:
        tipo = p.get("tipo", "?").upper()
        emoji = "👤" if tipo == "B2C" else "🏢"

        msg = f"━━━ {emoji} Prospect {idx}/{tot} ({tipo}) ━━━\n\n"
        if p.get("nome"):
            msg += f"Nome: {p['nome']}\n"
        if p.get("settore"):
            msg += f"Settore: {p['settore']}\n"
        if p.get("sede_citta"):
            msg += f"Sede: {p['sede_citta']}"
            if p.get("sede_regione"):
                msg += f", {p['sede_regione']}"
            msg += "\n"
        if p.get("contatto_email"):
            msg += f"Email: {p['contatto_email']}\n"
        if p.get("motivazione"):
            msg += f"Motivazione: {p['motivazione']}\n"

        if p.get("email_oggetto") or p.get("email_corpo"):
            msg += f"\n📧 Email da inviare:\n"
            if p.get("email_oggetto"):
                msg += f"Oggetto: {p['email_oggetto']}\n"
            if p.get("email_corpo"):
                corpo = p["email_corpo"]
                if len(corpo) > 2000:
                    corpo = corpo[:2000] + "...[troncata]"
                msg += f"\n{corpo}\n"

        msg += "\n✅ OK per approvare"
        if tipo == "B2B" and p.get("contatto_email"):
            msg += " e inviare l'email"
        msg += "\n❌ NO per rifiutare"

        return msg

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Invio email via SMTP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _invia_email_smtp(destinatario: str, oggetto: str, corpo: str) -> str:
        host = os.getenv("SMTP_HOST", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        sender_name = os.getenv("SMTP_SENDER_NAME", "NFC Smart Keychains")

        if not all([host, user, password]):
            return "ERRORE: credenziali SMTP non configurate nel .env"

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{user}>"
        msg["To"] = destinatario
        msg["Subject"] = oggetto
        msg.attach(MIMEText(corpo, "plain", "utf-8"))

        html_body = corpo.replace("\n", "<br>\n")
        html = (
            '<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#333;">'
            f"<p>{html_body}</p>"
            '<hr style="border:none;border-top:1px solid #ddd;margin-top:20px;">'
            f'<p style="font-size:11px;color:#999;">{sender_name}</p>'
            "</body></html>"
        )
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
            return "OK"
        except smtplib.SMTPException as e:
            return f"ERRORE: {e}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CRM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _salva_crm(prospect: dict, inviata: bool = False):
        from crm import salva_prospect, salva_messaggio

        tipo = prospect.get("tipo", "B2C").upper()
        if tipo not in ("B2C", "B2B"):
            tipo = "B2C"

        pid = salva_prospect(
            nome=prospect.get("nome", "Sconosciuto"),
            tipo=tipo,
            settore=prospect.get("settore", ""),
            sede_citta=prospect.get("sede_citta", ""),
            sede_regione=prospect.get("sede_regione", ""),
            contatto=prospect.get("contatto_email", ""),
            motivazione=prospect.get("motivazione", ""),
        )

        if prospect.get("email_corpo"):
            salva_messaggio(
                corpo=prospect["email_corpo"],
                prospect_id=pid,
                canale="email",
                destinatario=prospect.get("contatto_email", ""),
                oggetto=prospect.get("email_oggetto", ""),
                stato="inviato" if inviata else "bozza",
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Analisi Produzione (/analisi)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _processo_analisi(self):
        self.invia(
            "🏭 Avvio analisi produzione...\n"
            "Calcolo costi, listino e ammortamento."
        )

        try:
            from tasks import task_analisi
            task_outputs = self._esegui_crew(task_analisi)
        except Exception as e:
            self.invia(f"❌ Errore durante l'analisi:\n{e}")
            return

        report = task_outputs[0] if task_outputs else "Nessun output."

        self.invia("🏭 REPORT ANALISI PRODUZIONE\n" + "═" * 35)
        parti = self._split_report(report, 3500)
        for i, parte in enumerate(parti, 1):
            if len(parti) > 1:
                self.invia(f"[Parte {i}/{len(parti)}]\n\n{parte}")
            else:
                self.invia(parte)
        self.invia("━━━ ANALISI COMPLETATA ━━━")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Ricerca Innovazione (/idee)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _processo_idee(self):
        self.invia(
            "💡 Avvio ricerca nuovi prodotti NFC...\n"
            "Cerco idee, fornitori e costi."
        )

        try:
            from tasks import task_idee
            task_outputs = self._esegui_crew(task_idee)
        except Exception as e:
            self.invia(f"❌ Errore durante la ricerca idee:\n{e}")
            return

        report = task_outputs[0] if task_outputs else "Nessun output."

        self.invia("💡 REPORT R&D — NUOVI PRODOTTI NFC\n" + "═" * 35)
        parti = self._split_report(report, 3500)
        for i, parte in enumerate(parti, 1):
            if len(parti) > 1:
                self.invia(f"[Parte {i}/{len(parti)}]\n\n{parte}")
            else:
                self.invia(parte)
        self.invia("━━━ RICERCA IDEE COMPLETATA ━━━")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Deep Research (Gemini 2.5 Pro)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _deep_research(self):
        """Analisi approfondita del mercato NFC usando Gemini 2.5 Pro."""
        self.invia(
            "🔬 Avvio Deep Research con Gemini 2.5 Pro...\n"
            "Analisi approfondita del mercato NFC italiano.\n"
            "Potrebbe richiedere qualche minuto."
        )

        try:
            import google.generativeai as genai

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-2.5-pro")

            prompt = (
                "Sei un analista di mercato esperto. Fai un'analisi APPROFONDITA "
                "del mercato dei gadget NFC in Italia nel 2026. L'analisi è per una "
                "startup con sede a Cuneo (Piemonte) che produce portachiavi NFC "
                "smart personalizzabili con stampante 3D (Bambu Lab A1 Mini).\n\n"
                "Il modello di vendita è duale:\n"
                "- B2C: vendita singola sotto 300 pezzi (privati, freelancer, piccole attività)\n"
                "- B2B: vendita bulk da 300 pezzi in su (aziende, eventi, fiere)\n\n"
                "ANALIZZA IN DETTAGLIO:\n\n"
                "1. MERCATO NFC ITALIA 2026\n"
                "   - Dimensione stimata del mercato gadget NFC\n"
                "   - Trend di crescita\n"
                "   - Segmenti più promettenti\n\n"
                "2. CONCORRENZA\n"
                "   - Principali competitor italiani nel settore NFC\n"
                "   - I loro prodotti, prezzi, punti di forza e debolezza\n"
                "   - Come differenziarsi\n\n"
                "3. TARGET B2C — CLIENTI SINGOLI\n"
                "   - Profili di buyer persona ideali\n"
                "   - Canali di acquisizione (social, marketplace, fiere)\n"
                "   - Pricing ottimale per vendita singola\n"
                "   - Strategie di marketing consigliata\n\n"
                "4. TARGET B2B — AZIENDE\n"
                "   - Settori aziendali più ricettivi\n"
                "   - Dimensioni aziende target\n"
                "   - Decision maker da contattare\n"
                "   - Ciclo di vendita tipico\n\n"
                "5. NUOVI PRODOTTI NFC\n"
                "   - Prodotti NFC innovativi da sviluppare\n"
                "   - Fornitori componenti (con link se possibile)\n"
                "   - Stima costi e fattibilità\n\n"
                "6. CANALI DI VENDITA CONSIGLIATI\n"
                "   - Online: marketplace, e-commerce, social selling\n"
                "   - Offline: fiere, negozi, partnership\n"
                "   - Strategia omnicanale suggerita\n\n"
                "7. RACCOMANDAZIONI STRATEGICHE\n"
                "   - Top 3 azioni immediate da fare\n"
                "   - Piano a 6 mesi\n"
                "   - Rischi principali e come mitigarli\n\n"
                "Sii specifico con nomi, numeri e link dove possibile."
            )

            response = model.generate_content(prompt)
            report = response.text

            self.invia("🔬 DEEP RESEARCH — ANALISI MERCATO NFC ITALIA\n" + "═" * 40)

            parti = self._split_report(report, 3500)
            for i, parte in enumerate(parti, 1):
                if len(parti) > 1:
                    self.invia(f"[Parte {i}/{len(parti)}]\n\n{parte}")
                else:
                    self.invia(parte)

            self.invia(
                "━━━ DEEP RESEARCH COMPLETATA ━━━\n"
                "Il report è stato generato con Gemini 2.5 Pro.\n"
                "Scrivi /cerca per avviare una ricerca prospect basata su questi dati."
            )

        except Exception as e:
            self.invia(f"❌ Errore Deep Research: {e}")

    @staticmethod
    def _split_report(testo: str, max_len: int = 3500) -> list[str]:
        """Divide un testo lungo in parti rispettando i paragrafi."""
        if len(testo) <= max_len:
            return [testo]

        parti = []
        while testo:
            if len(testo) <= max_len:
                parti.append(testo)
                break

            punto_taglio = testo.rfind("\n\n", 0, max_len)
            if punto_taglio == -1:
                punto_taglio = testo.rfind("\n", 0, max_len)
            if punto_taglio == -1:
                punto_taglio = max_len

            parti.append(testo[:punto_taglio])
            testo = testo[punto_taglio:].lstrip("\n")

        return parti

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Export prospect (/export)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _esporta_prospect(self):
        from crm import esporta_prospect

        rows = esporta_prospect()
        if not rows:
            self.invia("📂 Nessun prospect salvato nel CRM.")
            return

        b2b = [r for r in rows if r["tipo"] == "B2B"]
        b2c = [r for r in rows if r["tipo"] == "B2C"]
        inviate = sum(1 for r in rows if r.get("email_stato") == "inviato")

        self.invia(
            f"📂 Export CRM: {len(rows)} prospect\n"
            f"  B2B: {len(b2b)} | B2C: {len(b2c)}\n"
            f"  Email inviate: {inviate}\n\n"
            "Genero il file..."
        )

        export_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "prospect_export.json"
        )
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        self._invia_documento(export_path, f"prospect_export_{len(rows)}.json")

    def _invia_documento(self, filepath: str, filename: str):
        """Invia un file come documento su Telegram."""
        try:
            with open(filepath, "rb") as f:
                requests.post(
                    f"{self.base}/sendDocument",
                    data={"chat_id": self.chat_id},
                    files={"document": (filename, f, "application/json")},
                    timeout=60,
                )
        except requests.RequestException as e:
            self.invia(f"⚠️ Errore invio file: {e}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Comandi info
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _mostra_stats(self):
        from crm import statistiche
        s = statistiche()
        self.invia(
            "📊 Statistiche CRM\n\n"
            f"Prospect totali: {s['totale_prospect']}\n"
            f"  B2C: {s['prospect_b2c']}\n"
            f"  B2B: {s['prospect_b2b']}\n"
            f"Email inviate: {s['email_inviate']}\n"
            f"Sessioni totali: {s['sessioni_totali']}"
        )

    def _mostra_help(self):
        self.invia(
            "🤖 IAtaplink — NFC Smart Keychains Bot\n\n"
            "Comandi:\n"
            "  /cerca — Ricerca prospect B2C + B2B\n"
            "  /analisi — Report produzione, costi e listino\n"
            "  /idee — Nuovi prodotti NFC (R&D)\n"
            "  /rd — Deep Research mercato NFC\n"
            "  /export — Scarica file JSON con tutti i prospect\n"
            "  /stats — Statistiche CRM\n"
            "  /help — Questo messaggio\n\n"
            "Durante la revisione prospect:\n"
            "  OK / SÌ — Approva (email B2B inviata automaticamente)\n"
            "  NO — Rifiuta (salvato come bozza nel CRM)"
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Telegram helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def invia(self, testo: str):
        """Invia un messaggio su Telegram, spezzandolo se troppo lungo."""
        while testo:
            blocco = testo[:TELEGRAM_MAX_LEN]
            testo = testo[TELEGRAM_MAX_LEN:]
            try:
                requests.post(
                    f"{self.base}/sendMessage",
                    json={"chat_id": self.chat_id, "text": blocco},
                    timeout=30,
                )
            except requests.RequestException as e:
                print(f"⚠️ Errore invio Telegram: {e}")

    def _poll_message(self, timeout: int | None = None) -> str | None:
        """Attende un messaggio dall'utente. Senza timeout, blocca indefinitamente."""
        deadline = time.time() + timeout if timeout else None

        while True:
            if deadline and time.time() > deadline:
                return None
            try:
                r = requests.get(
                    f"{self.base}/getUpdates",
                    params={"offset": self.last_update_id + 1, "timeout": POLLING_TIMEOUT_SEC},
                    timeout=POLLING_TIMEOUT_SEC + 10,
                )
                for update in r.json().get("result", []):
                    self.last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    if str(msg.get("chat", {}).get("id")) == str(self.chat_id):
                        return msg.get("text", "")
            except requests.RequestException as e:
                print(f"⚠️ Errore polling Telegram: {e}")
                time.sleep(5)

    def _flush_updates(self):
        """Scarta gli update vecchi all'avvio."""
        try:
            r = requests.get(
                f"{self.base}/getUpdates",
                params={"offset": -1, "limit": 1},
                timeout=30,
            )
            results = r.json().get("result", [])
            if results:
                self.last_update_id = results[-1]["update_id"]
        except requests.RequestException:
            pass

    @staticmethod
    def _tronca(testo: str, max_len: int = 3500) -> str:
        if len(testo) <= max_len:
            return testo
        return testo[:max_len] + "\n...[troncato]"
