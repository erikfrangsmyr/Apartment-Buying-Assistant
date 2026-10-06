# Apartment Buying Assistant

Local-first API that helps evaluate Swedish bostadsrätter: store curated buying tips, your own criteria,
neighborhoods, housing associations (BRF) with renovation history, listings and evaluations — and compute
the real monthly cost of a purchase.

Python + FastAPI + SQLite (stdlib `sqlite3`). No auth, no cloud, no external services.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/) (`pip install uv`).

```bash
uv sync                                    # install dependencies
uv run python scripts/init_db.py           # create data/apartment.db and load seed data
uv run uvicorn app.main:app --port 8765 --reload
```

Open the interactive docs at http://127.0.0.1:8765/docs.

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
| `db/seed.sql` | 18 Swedish BRF/bostadsrätt tips plus example criteria and neighborhoods (idempotent) |
| `app/main.py` | FastAPI app factory |
| `app/routers/` | One router per resource, plus `calculations` |
| `scripts/init_db.py` | Create/seed the database |
| `tests/` | pytest suite (uses a temporary database) |

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET/POST | `/tips` | `?category=brf_finance\|renovation\|legal\|viewing\|cost\|negotiation`, `?min_importance=1-5` |
| GET/POST | `/criteria` | `?kind=hard\|soft`; `value` is any JSON (list for operator `in`) |
| GET/POST | `/neighborhoods` | `?municipality=` |
| GET/POST | `/associations` | `?neighborhood_id=`; `GET /associations/{id}` includes renovations |
| GET/POST | `/associations/{id}/renovations` | kind: roof, facade, stambyte, windows, elevator, other |
| GET/POST | `/listings` | `?status=watching\|viewed\|bid\|rejected`, `?neighborhood_id=`, `?association_id=` |
| GET/POST | `/evaluations` | `?listing_id=`; `red_flags` is a list of strings |
| POST | `/calculations/monthly-cost` | See below |

Every resource also has `GET /<resource>/{id}`. Constraint violations (duplicates, unknown foreign keys)
return `409`; invalid input returns `422`.

### Monthly cost

```bash
curl -s -X POST http://127.0.0.1:8765/calculations/monthly-cost \
  -H 'content-type: application/json' \
  -d '{"price": 4000000, "down_payment": 600000, "interest_rate": 3.5, "monthly_fee": 4000, "operating_costs": 800}'
```

Returns loan amount, belåningsgrad, interest (before and after the 30 %/21 % ränteavdrag), amortering,
avgift, drift and totals. If `amortization_rate` is omitted it follows the amorteringskrav (2 % above 70 %
belåningsgrad, 1 % above 50 %). Warnings flag loans above the 90 % bolånetak or amortering below the
requirement. The rules are simplified — confirm with your bank.
