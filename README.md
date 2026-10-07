# Apartment Buying Assistant

Local-first API that helps evaluate Swedish bostadsrätter: store curated buying tips, your own criteria,
neighborhoods, housing associations (BRF) with renovation history, listings and evaluations — rule-based
BRF screening, and compute the real monthly cost of a purchase.

**BRF guide:** [docs/brf-evaluation-guide.md](docs/brf-evaluation-guide.md) — what to read in the årsredovisning,
red/green flags, and viewing questions (Swedish, for non-experts).

Python + FastAPI + SQLite (stdlib `sqlite3`). No auth, no cloud, no external services.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/) (`pip install uv`). Windows (no WSL): see [docs/local-dev.md](docs/local-dev.md).

```bash
uv sync                                    # install dependencies
uv run python scripts/init_db.py           # create data/apartment.db and load seed data
uv run python scripts/serve.py --reload    # serves on http://127.0.0.1:8642
```

Open **http://127.0.0.1:8642/app** in your browser for the web UI (listings, utvärdering, månadskostnad).
The start page is http://127.0.0.1:8642/ — API docs remain at `/docs`.

### Workflow: one listing

After you pull changes that update `db/seed.sql` (e.g. a new object like Diligensvägen 4), refresh your local DB and start the API. **Run each line separately** — never paste documentation arrows (`→`) or chained commands as a single shell line (e.g. `git pull uv run ... --reset` will break).

```bash
git pull
uv run python scripts/init_db.py --reset
uv run python scripts/serve.py
```

Then evaluate a listing (replace `ID` with the listing id from `GET /listings`):

```bash
curl -s -X POST http://127.0.0.1:8642/listings/ID/evaluate | jq
```

Open the interactive docs at http://127.0.0.1:8642/docs.

The default port is **8642**. Override it with the `--port` flag or the `APP_PORT` env var (the flag wins):

```bash
uv run python scripts/serve.py --port 9123
APP_PORT=9123 uv run python scripts/serve.py
```

`--host` / `APP_HOST` changes the bind address (default `127.0.0.1`).

The app also creates and seeds the database on startup if it doesn't exist, so the init script is optional.
Use `scripts/init_db.py --reset` to start over, `--no-seed` for empty tables, or `--db PATH` / the
`APARTMENT_DB` env var to use another file.

## Tests

```bash
uv run pytest
```

## Layout

| Path | What |
| --- | --- |
| `db/schema.sql` | Schema v1: `tips`, `criteria`, `neighborhoods`, `associations`, `renovations`, `listings`, `evaluations` |
| `db/seed.sql` | Swedish BRF/bostadsrätt tips plus example criteria and neighborhoods (idempotent) |
| `docs/brf-evaluation-guide.md` | Practical BRF evaluation guide (årsredovisning, thresholds, flags) |
| `app/main.py` | FastAPI app factory |
| `app/routers/` | One router per resource, plus `calculations` and `ui` |
| `templates/` | Jinja2 HTML for the browser UI |
| `static/` | CSS and client JS for `/app` |
| `scripts/init_db.py` | Create/seed the database |
| `scripts/serve.py` | Run the API (`--port` / `APP_PORT`, default 8642) |
| `tests/` | pytest suite (uses a temporary database) |

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET/POST | `/tips` | `?category=brf_finance\|renovation\|legal\|viewing\|cost\|negotiation`, `?min_importance=1-5` |
| GET/POST | `/criteria` | `?kind=hard\|soft`; `value` is any JSON (list for operator `in`) |
| GET/POST | `/neighborhoods` | `?municipality=` |
| GET/POST | `/associations` | `?neighborhood_id=`; `GET /associations/{id}` includes renovations |
| POST | `/associations/assess` | Rule-based BRF score from JSON (no DB write); see [BRF guide](docs/brf-evaluation-guide.md) |
| GET/POST | `/associations/{id}/renovations` | kind: roof, facade, stambyte, windows, elevator, other |
| GET/POST | `/listings` | `?status=watching\|viewed\|bid\|rejected`, `?neighborhood_id=`, `?association_id=` |
| POST | `/listings/{id}/evaluate` | Score listing vs `criteria`; optional BRF assess; writes `evaluations` |
| GET/POST | `/evaluations` | `?listing_id=`; `red_flags` is a list of strings |
| POST | `/calculations/monthly-cost` | See below |

Every resource also has `GET /<resource>/{id}`. Constraint violations (duplicates, unknown foreign keys)
return `409`; invalid input returns `422`.

### Monthly cost

```bash
curl -s -X POST http://127.0.0.1:8642/calculations/monthly-cost \
  -H 'content-type: application/json' \
  -d '{"price": 4000000, "down_payment": 600000, "interest_rate": 3.5, "monthly_fee": 4000, "operating_costs": 800}'
```

Returns loan amount, belåningsgrad, interest (before and after the 30 %/21 % ränteavdrag), amortering,
avgift, drift and totals. If `amortization_rate` is omitted it follows the amorteringskrav (2 % above 70 %
belåningsgrad, 1 % above 50 %). Warnings flag loans above the 90 % bolånetak or amortering below the
requirement. The rules are simplified — confirm with your bank.
