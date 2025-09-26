# Provider Catalog

A lean procurement catalog that ingests NASPO-style Excel listings, stores normalized data in PostgreSQL, and exposes a minimal FastAPI + React experience for high-speed search, filtering, and price comparison.

NOTE: DEVELOPMENTAL ONLY, REQUIRES FURTHER SECURITY PRACTISES BEFORE PRODUCTION

## Features

- PostgreSQL schema covering providers, brands, categories, products, provider listings, optional attributes, images, and inventory fields.
- Postgres full text search (tsvector) and trigram indexes for fast SKU/name lookup and fuzzy matching.
- Repeatable ETL script that normalizes NASPO spreadsheets, cleans values, and produces summary metrics by provider/brand/category before loading.
- FastAPI backend with endpoints:
  - `GET /search`: full-text search with provider/brand/category facets and sort controls.
  - `GET /products/{id}`: enriched product details and offers.
  - `GET /providers/{id}` and `/providers/{id}/offerings`: provider metadata and catalog listings.
  - `GET /compare?sku=`: price comparison for a manufacturer part number across suppliers.
- React + TypeScript + Tailwind UI with global search, facet sidebar, sorting, tabbed browsing, and a price comparison drawer + tab.
- Docker Compose stack (PostgreSQL, API, static frontend) with Alembic migrations and sample env files.

## Getting started

### Prerequisites

- Docker and Docker Compose
- Optional: Python 3.11+ and Node.js 18+ for local (non-container) runs

### Running with Docker Compose

```bash
docker compose up --build
```

Services:
- API available at `http://localhost:8000` (FastAPI docs at `/docs`).
- Frontend available at `http://localhost:5173`.
- PostgreSQL exposed on `localhost:5432` (user/password `postgres` / `postgres`).

The backend container automatically applies Alembic migrations on startup.

### Applying migrations locally

From `backend/`:

```bash
pip install -r requirements.txt
alembic upgrade head
```

Set `DATABASE_URL` to point to your database (see `backend/.env.example`).

### Loading NASPO spreadsheets

1. Ensure the database is running and migrated.
2. Copy the spreadsheet locally and run:

```bash
cd backend
python -m app.scripts.load_catalog path/to/catalog.xlsx --sheet "NASPO August 2025"
```

The loader cleans text, coerces prices to numerics, deduplicates vendor/SKU pairs, and prints provider, category, and brand coverage counts before committing rows into the normalized tables.

### Frontend development

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` (see `.env.example`) to point at the running backend.

## Project structure

```
backend/        FastAPI application, models, migrations, ETL scripts
frontend/       React + TypeScript + Tailwind UI (Vite)
```

## Testing

- Backend: run `pytest` (tests can be added under `backend/tests/`).
- Frontend: run `npm run lint` for static analysis.
- End-to-end: `docker compose up` and exercise UI/API.

## Notes

- Postgres extensions `pg_trgm` are enabled automatically by the initial migration.
- The API leans on native Postgres search instead of external search stacks to keep operations auditable.
- Ratings, workflows, and complex contracting features are intentionally omitted to focus on clarity and numeric accuracy.
