"""
NFC Smart Keychains — Sistema multi-agente con CrewAI.

Avvia con:
    python main.py
"""

import os
import sys

import yaml
from crewai import Crew, Process
from dotenv import load_dotenv


def carica_config(path: str = "config.yaml") -> dict:
    """Carica e restituisce il file di configurazione YAML."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(config_path):
        print(f"❌ File {path} non trovato.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def valida_env() -> None:
    """Verifica che le variabili d'ambiente essenziali siano configurate."""
    richieste = {
        "OPENAI_API_KEY": "Chiave API OpenAI (https://platform.openai.com/api-keys)",
        "TELEGRAM_BOT_TOKEN": "Token del bot Telegram (@BotFather)",
        "TELEGRAM_CHAT_ID": "Chat ID Telegram del fondatore",
    }
    mancanti = [k for k in richieste if not os.getenv(k)]
    if mancanti:
        print("❌ Variabili d'ambiente mancanti:")
        for k in mancanti:
            print(f"   {k} — {richieste[k]}")
        print("\n   Copia .env.example in .env e compila i valori.")
        sys.exit(1)

    if not os.getenv("SERPER_API_KEY"):
        print(
            "⚠️  SERPER_API_KEY non configurata. La ricerca web potrebbe non funzionare.\n"
            "   Registrati su https://serper.dev/ per ottenere una chiave gratuita.\n"
        )


def main() -> None:
    # Carica .env dalla stessa cartella dello script
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)

    valida_env()
    config = carica_config()

    azienda = config.get("azienda", {})
    print("=" * 60)
    print("🚀 NFC Smart Keychains — Sistema Multi-Agente")
    print(f"   Azienda: {azienda.get('nome', 'N/A')}")
    print(f"   Sede:    {azienda.get('sede', 'N/A')}, {azienda.get('regione', 'N/A')}")
    print("=" * 60)
    print()

    # Import qui per evitare errori se le env non sono configurate
    from agents import (
        il_capo,
        l_analista,
        l_esploratore,
        l_innovatore,
        il_venditore,
    )
    from tasks import tutte_le_task

    crew = Crew(
        agents=[l_esploratore, l_analista, il_venditore, l_innovatore, il_capo],
        tasks=tutte_le_task,
        process=Process.sequential,
        verbose=True,
    )

    print("▶️  Avvio crew...\n")
    risultato = crew.kickoff()

    print("\n" + "=" * 60)
    print("✅ Esecuzione completata!")
    print("=" * 60)
    print(risultato)


if __name__ == "__main__":
    main()
