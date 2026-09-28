import os
import sys
import unittest
import json
from unittest import mock

import pandas as pd

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

    def test_chat_route_rejects_non_string_message_with_400(self):
        client = app.app.test_client()

        response = client.post("/api/chat", json={"message": ["not", "a", "string"]})

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

    def test_chat_route_scopes_data_to_the_active_ville(self):
        # Sans bornage, une question sur Lyon recommandait les annonces les
        # moins chères de tout le master — donc Vieux-Lille (ex: "Perrache").
        df = pd.DataFrame({
            "ville": ["Lyon", "Lille"],
            "quartier": ["Confluence", "Vieux-Lille"],
        })
        client = app.app.test_client()

        with mock.patch.object(app.data_loader, "get_data", return_value=df), \
                mock.patch.object(app.chat_service, "get_chat_result", return_value={"response": "ok"}) as chat:
            response = client.post("/api/chat", json={"message": "Analyse Perrache", "ville": "lyon"})

        self.assertEqual(response.status_code, 200)
        scoped_df = chat.call_args.args[2]
        self.assertEqual(scoped_df["ville"].tolist(), ["Lyon"])


if __name__ == "__main__":
    unittest.main()
