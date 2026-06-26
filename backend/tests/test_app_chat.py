import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class ChatRouteTest(unittest.TestCase):
    def test_chat_route_rejects_missing_message_cleanly(self):
        client = app.app.test_client()

        response = client.post("/api/chat", json={"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"response": "Silence... Tu n'as rien à dire ?"},
        )

    def test_chat_route_accepts_text_plain_json_without_preflight(self):
        client = app.app.test_client()

        response = client.post(
            "/api/chat",
            data=json.dumps({"message": "   "}),
            content_type="text/plain",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"response": "Silence... Tu n'as rien à dire ?"},
        )


if __name__ == "__main__":
    unittest.main()
