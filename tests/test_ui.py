import unittest
from pathlib import Path
from types import SimpleNamespace

from chatbot.main import app
from chatbot.api.dependencies import get_chatbot


class UITest(unittest.TestCase):
    def test_ui_is_served_at_root(self):
        root_route = next(
            route for route in app.routes if getattr(route, "path", None) == "/"
        )
        self.assertEqual(root_route.name, "index")

        html = (
            Path(__file__).parents[1]
            / "src"
            / "chatbot"
            / "static"
            / "index.html"
        ).read_text()
        self.assertIn('id="auth-form"', html)
        self.assertIn('id="composer"', html)

    def test_chatbot_dependency_reuses_app_instance(self):
        chatbot = object()
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(chatbot=chatbot))
        )
        self.assertIs(get_chatbot(request), chatbot)


if __name__ == "__main__":
    unittest.main()
