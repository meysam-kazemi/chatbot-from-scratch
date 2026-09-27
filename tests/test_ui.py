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
        self.assertIn('className = "conversation-menu"', html)
        self.assertNotIn('id="rename-chat"', html)
        self.assertNotIn('id="delete-chat"', html)
        self.assertIn("body { margin: 0; overflow: hidden", html)
        self.assertIn(".conversation-list { min-height: 0", html)
        self.assertIn(".messages { min-height: 0", html)
        self.assertIn("marked@18.0.14", html)
        self.assertIn("dompurify@3.4.16", html)
        self.assertIn("DOMPurify.sanitize(marked.parse(content)", html)
        self.assertIn("function renderMarkdownFallback", html)
        self.assertIn("line.match(/^(#{1,6})", html)

    def test_chatbot_dependency_reuses_app_instance(self):
        chatbot = object()
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(chatbot=chatbot))
        )
        self.assertIs(get_chatbot(request), chatbot)


if __name__ == "__main__":
    unittest.main()
