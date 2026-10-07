# Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

## Bash (macOS / Linux / WSL)

```bash
uv sync
uv run python scripts/init_db.py
uv run python scripts/serve.py --reload
```

API: http://127.0.0.1:8642 — interactive docs at `/docs`.

Override port: `uv run python scripts/serve.py --port 9123` or `APP_PORT=9123`.

Database path: `data/apartment.db` by default; `APARTMENT_DB` or `scripts/init_db.py --db PATH`.

## PowerShell (Windows, no WSL)

```powershell
uv sync
uv run python scripts/init_db.py
uv run python scripts/serve.py --reload
```

API: `http://127.0.0.1:8642` (or `$env:APP_PORT = "9123"` before serve).

### SSH clone via Origin (optional)

```powershell
$key = Join-Path $env:USERPROFILE ".ssh\id_ed25519_origin"
Test-Path $key   # must be True
$env:GIT_SSH_COMMAND = "ssh -i `"$key`" -o IdentitiesOnly=yes"
git clone ssh://git@git-ssh.origin.cursor.com/erik-frangsmyr/Apartment-Buying-Assistant.git
```

Register the `.pub` key in **Cursor Settings → Origin → SSH keys** first.

GitHub mirror: https://github.com/erikfrangsmyr/Apartment-Buying-Assistant

## Reset database after pulling new seed data

Run **three separate commands** — do not paste arrows (`→`) or semicolons as one line:

```bash
git pull
uv run python scripts/init_db.py --reset
uv run python scripts/serve.py
```

`--reset` drops and recreates tables, then reloads `db/seed.sql`.
