import unittest
from pathlib import Path

from chatbot.main import app


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


if __name__ == "__main__":
    unittest.main()
