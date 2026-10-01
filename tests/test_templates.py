"""Real Jinja2 render tests for the calorie-tracker nav/dashboard links.

Run with: python3 -m unittest tests.test_templates -v

These tests render the ACTUAL templates (app/templates/base.html and
app/templates/dashboard.html) through a real Jinja2 Environment -- the same
templating engine the FastAPI app uses via Jinja2Templates -- and assert the
rendered HTML contains the new /calorie-tracker entry points in the right
place. Reverting either template edit makes these fail.
"""
from __future__ import annotations

import os
import unittest

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "templates")


class FakeRequest:
    """Minimal stand-in for starlette.Request -- just the session dict the
    templates actually touch (request.session.get("user_id"))."""

    def __init__(self, session: dict):
        self.session = session


def make_env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR))


class TestBaseNavCalorieLink(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    def test_authenticated_nav_includes_calorie_tracker_link(self):
        template = self.env.get_template("base.html")
        html = template.render(request=FakeRequest({"user_id": 1}))

        self.assertIn('<a href="/calorie-tracker">Calories</a>', html)

        # It must live inside the authenticated nav, alongside the other
        # feature links -- not duplicated into the logged-out branch.
        recipes_idx = html.index('<a href="/recipes">Recipes</a>')
        tasks_idx = html.index('<a href="/tasks">Tasks</a>')
        family_idx = html.index('<a href="/family">Family</a>')
        calorie_idx = html.index('<a href="/calorie-tracker">Calories</a>')

        self.assertTrue(recipes_idx < tasks_idx < calorie_idx < family_idx)

    def test_logged_out_nav_has_no_calorie_tracker_link(self):
        """Proves the link is genuinely scoped to the authenticated branch:
        reverting the base.html edit would make the authenticated test above
        fail, but a naive unconditional link (e.g. placed outside the
        {% if %}) would still pass that test while failing this one."""
        template = self.env.get_template("base.html")
        html = template.render(request=FakeRequest({}))

        self.assertNotIn("/calorie-tracker", html)
        self.assertIn('<a href="/login">Login</a>', html)


class TestDashboardCalorieCard(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    def test_dashboard_links_includes_calorie_tracker_card(self):
        template = self.env.get_template("dashboard.html")
        html = template.render(
            request=FakeRequest({"user_id": 1}),
            current_user=None,
            recent_recipes=[],
            upcoming_events=[],
            family_members=[],
            recent_task_lists=[],
        )

        self.assertIn(
            '<a href="/calorie-tracker" class="dashboard-link-card">', html
        )
        self.assertIn('<span class="dashboard-link-icon">\U0001F34E</span>', html)

        # Card must sit inside the .dashboard-links block, after the
        # existing Tasks card (matches the exact structure requested).
        links_block_start = html.index('<div class="dashboard-links">')
        links_block_end = html.index("</div>", links_block_start)
        tasks_card_idx = html.index('<a href="/tasks" class="dashboard-link-card">')
        calorie_card_idx = html.index(
            '<a href="/calorie-tracker" class="dashboard-link-card">'
        )

        self.assertTrue(links_block_start < tasks_card_idx < calorie_card_idx < links_block_end)


if __name__ == "__main__":
    unittest.main()
