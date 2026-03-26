"""
NFC Smart Keychains — Bot Telegram + Sistema Multi-Agente.

Avvia il bot Telegram che controlla tutto il sistema:
ricerca prospect, approvazione singola, invio email, CRM.

Avvia con:
    python main.py
"""

import io
import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv


def valida_env() -> None:
    """Verifica che le variabili d'ambiente essenziali siano configurate."""
    richieste = {
        "GOOGLE_API_KEY": "https://aistudio.google.com/apikey",
        "TELEGRAM_BOT_TOKEN": "@BotFather su Telegram",
        "TELEGRAM_CHAT_ID": "api.telegram.org/bot<TOKEN>/getUpdates",
    }
    mancanti = [k for k in richieste if not os.getenv(k)]
    if mancanti:
        print("❌ Variabili d'ambiente mancanti:")
        for k in mancanti:
            print(f"   {k} — {richieste[k]}")
        print("\n   Compila il file .env e riavvia.")
        sys.exit(1)

    if not os.getenv("SERPER_API_KEY"):
        print("⚠️  SERPER_API_KEY mancante — la ricerca web non funzionerà.")

    smtp_mancanti = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD") if not os.getenv(k)]
    if smtp_mancanti:
        print(f"⚠️  SMTP incompleto ({', '.join(smtp_mancanti)}) — l'invio email non funzionerà.")

    print()


def main() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)

    valida_env()

    print("=" * 50)
    print("🚀 NFC Smart Keychains — Avvio Bot Telegram")
    print("   Il bot resta in ascolto su Telegram.")
    print("   Scrivi /cerca sul bot per avviare una ricerca.")
    print("   Premi Ctrl+C per fermare.")
    print("=" * 50)
    print()

    from bot import NfcBot
    bot = NfcBot()
    bot.run()


if __name__ == "__main__":
    main()
