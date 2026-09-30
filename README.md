# Media Tracker

[![CI](https://github.com/berylhu43/your_fav_literary_creation/actions/workflows/ci.yml/badge.svg)](https://github.com/berylhu43/your_fav_literary_creation/actions/workflows/ci.yml)

A Django app for logging the movies, TV shows, and books you've watched or read, rating them, and writing reviews. It pulls metadata from TMDB and Google Books, and recommends new titles with an LLM based on your own rating history.

The app has two sides:

- **Personal:** your media diary. Log a work, give it a half-star rating from 0 to 5, write a review, then edit, delete, or search your records.
- **Public:** a shared discovery area. Browse popular movies and TV (filterable by genre), search any title, open cast and crew pages, and read everyone's reviews of a work.

The backend serves two frontends. One is server-rendered with Django templates. The other is a REST API (DRF, token auth) that a separate React SPA calls.

## Features

- **Search, then cache.** A search hits TMDB (movies/TV) or Google Books (books). Clicking a result saves it to the local `Catalog`, and duplicates are caught by `source` + `external_id`.
- **One review per user per work.** A database constraint enforces this. Submitting a second review for the same work updates the first one.
- **Cast & crew.** Saved works get `Artist`/`Credit` rows. An artist's page fetches their full TMDB filmography live.
- **Discovery.** Popular movie and TV poster walls with genre filters. External API responses are cached for an hour.
- **LLM recommendations.** The user describes what they want in their own words. The LLM turns that into filters, the DB pulls matching items from the user's rating history, and a second LLM call turns that history into specific picks. See [llm_design.md](./llm_design.md).
- **Douban import.** A management command matches an exported Douban "watched" list against TMDB, writes a report you can edit, then commits it as reviews.

## Tech stack

| | |
|---|---|
| Backend | Python 3.12, Django 6.1, Django REST Framework |
| Database | SQLite (dev), PostgreSQL (CI / production) |
| External data | TMDB, Google Books |
| LLM | DeepSeek via the OpenAI-compatible SDK |
| Serving | Gunicorn + WhiteNoise, Docker |
| Deployment | AWS ECR → ECS Express Mode (Fargate) + RDS PostgreSQL; frontend on Amplify |
| Tooling | pytest-django, ruff, GitHub Actions |

## Project layout

```
config/            settings, root URLs, WSGI/ASGI
accounts/          register / login / logout (HTML + token API)
catalog/           works, genres, artists/credits, external API clients,
                   discovery, search, management commands
reviews/           user ratings & reviews (HTML views + ReviewViewSet)
recommendations/   LLM recommendation pipeline (home page)
templates/         shared base templates
```

In each app, `views.py` (HTML) and `api_views.py` (REST) are both thin and call the same `services.py`, which holds the business logic. External HTTP calls are all in `clients.py`.

## Getting started

### 1. Install

```bash
git clone git@github.com:berylhu43/your_fav_literary_creation.git
cd your_fav_literary_creation
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in the values. The settings module loads `.env` automatically.

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | Django secret key |
| `DEBUG` | for local dev | Set to `True` locally (defaults to `False`) |
| `TMDB_API_KEY` | for movie/TV features | TMDB v3 API key |
| `GOOGLE_BOOKS_API_KEY` | for book features | Google Books API key |
| `DEEPSEEK_API_KEY` | for recommendations | DeepSeek API key |
| `ALLOWED_HOSTS` | production | Comma-separated; defaults to `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | production | Extra frontend origins (localhost:5173/3000 are already allowed) |
| `CSRF_TRUSTED_ORIGINS` | production | Comma-separated, used when `DEBUG` is off |
| `DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_PORT` | optional | Use PostgreSQL. If `DATABASE_HOST` is unset, SQLite is used |

### 3. Run

```bash
python manage.py migrate          # also seeds the initial genres
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/.

## Main routes

| Path | What it is |
|---|---|
| `/` | LLM recommendations (login required) |
| `/catalog/` | Discovery: popular walls, genre filters, search |
| `/catalog/<id>/` | Work detail and the place to add/edit/delete your review |
| `/reviews/` | My records |
| `/accounts/` | Login / register / logout |
| `/api/...` | REST API |
| `/admin/` | Django admin |

The endpoints, request/response shapes, and auth rules are in [api_contract_for_frontend.md](./api_contract_for_frontend.md). Authenticated requests send `Authorization: Token <token>` (get one from `POST /api/token/`).

## Management commands

```bash
# Import Douban history: match against TMDB first (no DB writes), review the CSV, then commit
python manage.py import_douban match douban_watched.json --out match_report.csv
python manage.py import_douban commit match_report.csv --user <username>

# Re-fetch fields for existing Catalog rows from their source API
python manage.py backfill_catalog --fields vote_average --dry-run --limit 10
python manage.py backfill_catalog --all-fields --media-types movie tv book
```

## Tests & lint

```bash
ruff check .
python -m pytest -v
```

CI (`.github/workflows/ci.yml`) runs ruff and pytest on every push and PR to `main`. The tests run against a PostgreSQL 16 service container, not SQLite.

## Docker

```bash
docker build --platform linux/amd64 -t media-tracker .
docker run -p 8000:8000 --env-file .env media-tracker
```

The image serves the app with Gunicorn on port 8000. Static files are collected at build time and served by WhiteNoise. The image contains no secrets; all configuration is passed in as environment variables at runtime.

## Documentation

- [design.md](./design.md): architecture, data model, the reasoning behind key design decisions, and how the project was delivered in stages
- [llm_design.md](./llm_design.md): the recommendation pipeline and prompt design
- [api_contract_for_frontend.md](./api_contract_for_frontend.md): REST API contract
- [frontend_map.md](./frontend_map.md): React page map and data needs for each page
