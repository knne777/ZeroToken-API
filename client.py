#!/usr/bin/env python3
"""Interactive Terminal Chat Client for ZeroToken API."""

import sys
import requests

API_URL = "http://localhost:8000/api/v1/chat"


def main():
    provider = "agy"
    model = None
    conversation_id = None

    print("=" * 60)
    print("  ZeroToken API - Chat Interactivo")
    print("=" * 60)
    print(f"Proveedor actual: {provider}")
    print("Comandos disponibles:")
    print("  /new      -> Iniciar un nuevo chat (resetea el contexto)")
    print("  /provider -> Cambiar de proveedor (agy / claude / codex)")
    print("  /id       -> Ver el ID de conversación actual")
    print("  exit      -> Salir")
    print("=" * 60)
    print()

    while True:
        try:
            prompt = input("Tú > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if not prompt:
            continue

        if prompt.lower() in ("exit", "quit", ":q"):
            print("¡Hasta luego!")
            break

        if prompt == "/new":
            conversation_id = None
            print("\n🔄 Nueva conversación iniciada.\n")
            continue

        if prompt == "/id":
            print(f"\nID de conversación actual: {conversation_id or 'Ninguno (iniciará en el próximo mensaje)'}\n")
            continue

        if prompt.startswith("/provider"):
            parts = prompt.split()
            if len(parts) > 1:
                provider = parts[1]
                conversation_id = None
                print(f"\n🔄 Proveedor cambiado a: {provider} (se inició nueva conversación)\n")
            else:
                print(f"\nProveedor actual: {provider}. Usa: /provider [agy|claude|codex]\n")
            continue

        payload = {
            "message": prompt,
            "provider": provider,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if model:
            payload["model"] = model

        print("\n[Pensando...]")
        try:
            resp = requests.post(API_URL, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                conversation_id = data.get("conversation_id")
                reply = data.get("response", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                duration = data.get("duration_seconds", 0)

                print(f"\nAI ({provider}) > {reply}\n")
                print(f"--- [Turno: {data.get('num_turns', 1)} | Duración: {duration:.1f}s | Tokens: {tokens}] ---\n")
            else:
                err = resp.json().get("message", resp.text)
                print(f"\n❌ Error ({resp.status_code}): {err}\n")
        except Exception as e:
            print(f"\n❌ Error de conexión con ZeroToken API: {e}\n")


if __name__ == "__main__":
    main()
