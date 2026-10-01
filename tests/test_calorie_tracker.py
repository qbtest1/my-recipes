"""Tracker integration checks using real HTTP, sessions, templates, and SQLite.

Run: venv/bin/python -m unittest discover -s tests -v
The server's startup hook is disabled so the application's recipes.db is untouched.
"""
import socket
import threading
import time
import unittest
from datetime import date

import requests
import uvicorn
from bs4 import BeautifulSoup
from sqlalchemy import Date, Float, Integer, String, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password, require_family
from app.database import Base, get_db
from app.main import app
from app.models import CalorieEntry, Family, User
from app.routers.calorie_tracker import router


class CalorieTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password("test-password")
        cls.socket = socket.socket()
        cls.socket.bind(("127.0.0.1", 0))
        cls.url = f"http://127.0.0.1:{cls.socket.getsockname()[1]}"
        cls.server = uvicorn.Server(uvicorn.Config(
            app, lifespan="off", log_level="error"
        ))
        cls.thread = threading.Thread(
            target=cls.server.run, kwargs={"sockets": [cls.socket]}, daemon=True
        )
        cls.thread.start()
        deadline = time.monotonic() + 10
        while not cls.server.started:
            if not cls.thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Test HTTP server did not start")
            time.sleep(0.01)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.socket.close()

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions() as db:
            for user_id, name in ((11, "owner"), (22, "peer"), (33, "no-family")):
                db.add(User(
                    id=user_id, username=name, email=f"{name}@example.test",
                    first_name=name, password_hash=self.password_hash,
                ))
            db.flush()
            db.add(Family(id=7, name="Shared", invite_code="test", created_by=11))
            db.flush()
            db.get(User, 11).family_id = 7
            db.get(User, 22).family_id = 7
            db.commit()

        def test_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = requests.Session()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(get_db)
        self.engine.dispose()

    def login(self, username="owner"):
        response = self.client.post(
            self.url + "/login",
            data={"username": username, "password": "test-password"},
            allow_redirects=False, timeout=5,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("session", self.client.cookies)

    def post_entry(self, **changes):
        data = {
            "food_name": "Oats", "servings": "1.5", "serving_size": "1 cup",
            "meal": "breakfast", "date": "2026-10-01", "calories": "150",
        }
        data.update(changes)
        return self.client.post(
            self.url + "/calorie-tracker/add", data=data,
            allow_redirects=False, timeout=5,
        )

    def test_schema_is_structured_and_has_required_user_and_calories(self):
        columns = CalorieEntry.__table__.columns
        for name in ("user_id", "food_name", "servings", "serving_size", "meal",
                     "date", "calories"):
            self.assertFalse(columns[name].nullable, name)
        self.assertIsInstance(columns.date.type, Date)
        self.assertTrue(columns.date.index)
        self.assertIsInstance(columns.meal.type, String)
        self.assertIsInstance(columns.calories.type, Integer)
        self.assertIsInstance(columns.servings.type, Float)
        for name in ("protein", "carbs", "fat"):
            self.assertTrue(columns[name].nullable)
            self.assertIsInstance(columns[name].type, Float)
        self.assertEqual(
            {fk.target_fullname for fk in columns.user_id.foreign_keys}, {"users.id"}
        )

    def test_post_persists_own_identity_and_optional_macros(self):
        self.login()
        response = self.post_entry(user_id="22")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/calorie-tracker")
        with self.sessions() as db:
            entry = db.query(CalorieEntry).one()
            self.assertEqual(entry.user_id, 11)
            self.assertEqual(entry.food_name, "Oats")
            self.assertEqual(entry.servings, 1.5)
            self.assertEqual(entry.serving_size, "1 cup")
            self.assertEqual(entry.meal, "breakfast")
            self.assertEqual(entry.date, date(2026, 10, 1))
            self.assertEqual(entry.calories, 150)
            self.assertEqual((entry.protein, entry.carbs, entry.fat), (None, None, None))
            self.assertIsNotNone(entry.created_at)
        self.assertEqual(self.post_entry(protein="", carbs="", fat="").status_code, 303)
        self.assertEqual(self.post_entry(protein="0", carbs="12.5", fat="2").status_code, 303)
        with self.sessions() as db:
            entries = db.query(CalorieEntry).order_by(CalorieEntry.id).all()
            self.assertEqual((entries[1].protein, entries[1].carbs, entries[1].fat), (None, None, None))
            self.assertEqual((entries[2].protein, entries[2].carbs, entries[2].fat), (0.0, 12.5, 2.0))

    def test_own_listing_excludes_peer_and_groups_days_and_meals(self):
        self.login("peer")
        self.assertEqual(self.post_entry(food_name="Peer secret").status_code, 303)
        self.login()
        for food, meal, day in (
            ("Evening", "dinner", "2026-10-02"),
            ("Earlier", "dinner", "2026-10-01"),
            ("Midday", "lunch", "2026-10-02"),
            ("Morning", "breakfast", "2026-10-02"),
        ):
            self.assertEqual(self.post_entry(
                food_name=food, meal=meal, date=day, protein="0"
            ).status_code, 303)
        queries = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT") and "calorie_entries" in statement:
                queries.append(statement)

        event.listen(self.engine, "before_cursor_execute", capture)
        response = self.client.get(self.url + "/calorie-tracker", timeout=5)
        event.remove(self.engine, "before_cursor_execute", capture)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(queries), 1)
        self.assertNotIn("Peer secret", response.text)
        soup = BeautifulSoup(response.text, "html.parser")
        self.assertEqual(
            [heading.text for heading in soup.select("h2.section-heading")],
            ["2026-10-02", "2026-10-01"],
        )
        self.assertEqual(
            [heading.text for heading in soup.select("h3.task-list-card-title")],
            ["Breakfast", "Lunch", "Dinner", "Dinner"],
        )
        self.assertEqual(
            [food.text for food in soup.select("li strong")],
            ["Morning", "Midday", "Evening", "Earlier"],
        )
        self.assertIn("Protein: 0.0 g per serving", response.text)
        self.assertNotIn("Carbs:", response.text)
        self.assertIn("1.5 × 1 cup", response.text)
        self.assertIn("150 calories per serving", response.text)

    def test_empty_state_and_form_contract(self):
        self.login()
        response = self.client.get(self.url + "/calorie-tracker", timeout=5)
        self.assertEqual(response.status_code, 200)
        self.assertIn("No calorie entries yet.", response.text)
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.select_one('form[action="/calorie-tracker/add"]')
        self.assertEqual(form["method"], "post")
        for name in ("food_name", "servings", "serving_size", "meal", "date", "calories"):
            self.assertTrue(form.select_one(f'[name="{name}"]').has_attr("required"))
        for name in ("protein", "carbs", "fat"):
            field = form.select_one(f'[name="{name}"]')
            self.assertFalse(field.has_attr("required"))
            self.assertEqual((field["type"], field["step"]), ("number", "any"))

    def test_every_route_requires_login_and_family(self):
        for route in router.routes:
            self.assertIn(require_family, [dep.call for dep in route.dependant.dependencies])
        for username, location in ((None, "/login"), ("no-family", "/family")):
            if username:
                self.login(username)
            for response in (
                self.client.get(self.url + "/calorie-tracker", allow_redirects=False, timeout=5),
                self.post_entry(),
            ):
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers["location"], location)
        with self.sessions() as db:
            self.assertEqual(db.query(CalorieEntry).count(), 0)

    def test_invalid_forms_do_not_persist(self):
        self.login()
        for changes in (
            {"calories": None}, {"meal": "snack"}, {"date": "invalid"},
            {"protein": "invalid"}, {"carbs": "invalid"}, {"fat": "invalid"},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.post_entry(**changes).status_code, 422)
        with self.sessions() as db:
            self.assertEqual(db.query(CalorieEntry).count(), 0)


if __name__ == "__main__":
    unittest.main()
