"""Opt-in live check for the configured Upstash REST session store.

Run with `vercel env run -e production -- py tests/check_upstash_live.py`.
The synthetic session is always deleted and neither credential is printed.
"""

import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.logic import handle_message
from bot.session_store import UpstashSessionStore


def child(command: str, chat_id: int) -> int:
    sessions = UpstashSessionStore.from_env()
    if sessions is None:
        return 2
    if command == "new":
        response = handle_message(chat_id, "/new", sessions=sessions)
        return 0 if "Кто отправитель" in response else 1
    if command == "sender":
        response = handle_message(chat_id, "ООО Межпроцессный тест", sessions=sessions)
        return 0 if "Откуда забрать груз" in response else 1
    if command == "origin":
        response = handle_message(chat_id, "Тестовый пункт отправления", sessions=sessions)
        return 0 if "Куда доставить груз" in response else 1
    if command == "cleanup":
        sessions.pop(chat_id, None)
        return 0
    return 2


def main() -> int:
    if not os.getenv("KV_REST_API_URL") or not os.getenv("KV_REST_API_TOKEN"):
        print("Upstash credentials are not configured.")
        return 2

    chat_id = 1_000_000_000 + int(uuid.uuid4().hex[:8], 16) % 1_000_000_000
    try:
        for command in ("new", "sender", "origin"):
            result = subprocess.run(
                [sys.executable, __file__, command, str(chat_id)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                print(f"Upstash {command} check failed (exit {result.returncode}).")
                return 1
        print("Telegram dialogue state survived across independent processes: OK.")
        return 0
    finally:
        cleanup = subprocess.run(
            [sys.executable, __file__, "cleanup", str(chat_id)],
            capture_output=True,
            text=True,
            check=False,
        )
        if cleanup.returncode:
            print("Warning: temporary integration-check key will expire automatically.")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in {"new", "sender", "origin", "cleanup"}:
        sys.exit(child(sys.argv[1], int(sys.argv[2])))
    sys.exit(main())
