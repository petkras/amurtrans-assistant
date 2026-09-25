import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

from bot.session_store import UpstashSessionStore


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


class SessionStoreTests(unittest.TestCase):
    def test_session_survives_between_store_instances_and_expires_by_ttl(self):
        redis_values = {}
        expiries = {}

        def fake_urlopen(request, timeout):
            self.assertEqual(timeout, 4.0)
            parsed = urlsplit(request.full_url)
            parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
            self.assertEqual(request.headers.get("Authorization"), "Bearer test-token")
            command, key = parts[0].upper(), parts[1]
            if command == "SET":
                redis_values[key] = request.data.decode("utf-8")
                expiries[key] = parse_qs(parsed.query).get("EX", [None])[0]
                result = "OK"
            elif command == "GET":
                raw = redis_values.get(key)
                result = json.loads(raw) if raw is not None else None
            elif command == "DEL":
                result = int(key in redis_values)
                redis_values.pop(key, None)
            else:
                self.fail(f"Unexpected Redis command: {command}")
            return _Response({"result": result})

        first_instance = UpstashSessionStore("https://redis.example", "test-token")
        second_instance = UpstashSessionStore("https://redis.example", "test-token")
        session = {"values": {"sender": "ООО Тест"}, "awaiting": "origin", "updated_at": 1}
        with patch("bot.session_store.urlopen", side_effect=fake_urlopen):
            first_instance[123] = session
            self.assertEqual(second_instance.get(123), session)
            self.assertEqual(expiries["amurtrans:session:123"], "1800")
            second_instance.pop(123, None)
            self.assertIsNone(first_instance.get(123))


if __name__ == "__main__":
    unittest.main()
