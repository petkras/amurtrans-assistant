"""Vercel Python Function: Telegram webhook."""

from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot.logic import handle_message  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond(200, {"status": "ok", "service": "AmurTrans Assistant"})

    def do_POST(self):
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not secret or not token:
            self._respond(503, {"error": "not configured"})
            return
        if self.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            self._respond(403, {"error": "forbidden"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 65536:
            self._respond(413, {"error": "invalid length"})
            return
        try:
            update = json.loads(self.rfile.read(length))
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            if text and chat_id is not None:
                payload = json.dumps({"chat_id": chat_id, "text": handle_message(chat_id, text)}, ensure_ascii=False).encode("utf-8")
                request = Request(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(request, timeout=12) as response:
                    if response.status != 200:
                        raise RuntimeError("Telegram sendMessage failed")
            self._respond(200, {"ok": True})
        except (ValueError, TypeError):
            self._respond(400, {"error": "invalid update"})
        except Exception:
            # Telegram will retry this update. Do not log user messages or tokens.
            self._respond(502, {"error": "send failed"})

    def _respond(self, status: int, body: dict):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
