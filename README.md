# 🏠 Family Portal

A multi-tenant family hub — recipes, calendars, and more. Each family gets their own private space with shared recipes and events.

## Quick Start

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Getting Started

1. **Register** — Create your account with name, email, username, and password
2. **Create a Family** — Give your family a name and get an invite code
3. **Share the invite code** — Other family members register and join using the code
4. **Start using the portal!** — Add recipes, calendar events, and more

## Features

### 🔐 Authentication & Multi-Tenancy
- User accounts with secure bcrypt password hashing
- Create a family and invite members via shareable invite codes
- All content is scoped to your family — other families can't see your data
- Each family member gets a unique color for calendar events

### 🍽️ Recipes
- Paste a recipe URL and the app scrapes it automatically
- Extracts ingredients, directions, tools, and spices
- Search recipes by keyword across all fields
- Edit recipes and track modifications (Modified badge)
- Set a custom image for any recipe

### 📅 Family Calendar
- Monthly calendar view with color-coded events per family member
- Click any day to see details and add events
- Filter by family member
- Assign multiple family members to an event
- Add locations to events
- Edit and delete events

### 🥗 Calorie Tracker
- Personal food log for every user (entries are private to you)
- Log foods for breakfast, lunch, and dinner with serving size, calories, protein, carbs, and fat
- Per-meal and daily totals
- Browse previous days or jump to any date

### 🏠 Dashboard
- Quick links to all features
- Upcoming events at a glance
- Recent recipes

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Auth:** passlib + bcrypt, Starlette SessionMiddleware
- **Frontend:** Jinja2 templates, vanilla CSS/JS
- **Scraping:** recipe-scrapers library + BeautifulSoup JSON-LD fallback
