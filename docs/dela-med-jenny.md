# Dela appen med Jenny (servern kör bara på Eriks PC)

Apartment Buying Assistant är **lokal först**: databasen och API:et ligger på Eriks Windows-dator. Jenny öppnar bara webbläsaren — inget installeras på hennes telefon eller dator.

## Scenario A — samma hemma-Wi‑Fi

1. På Eriks PC, i projektmappen:

```powershell
$env:APP_SHARE_TOKEN="välj-en-hemlig-sträng"
uv run python scripts/serve.py --share
```

2. Skriptet skriver ut:
   - `http://127.0.0.1:8642/app` (Erik lokalt)
   - LAN-adresser, t.ex. `http://192.168.1.42:8642/app`
   - en rad på svenska för Jenny

3. Skicka Jenny länken med token om du satte `APP_SHARE_TOKEN`:

   `http://192.168.x.x:8642/app?token=välj-en-hemlig-sträng`

4. Om sidan inte laddas: **Windows-brandvägg** — tillåt Python/uvicorn för **privata nätverk** på port **8642** (eller din `APP_PORT`).

Utan token (bara `--share` på betrott hemma-Wi‑Fi) fungerar `/app` utan `?token=`, men API-anrop från UI:t är fortfarande öppna på LAN. Med token skyddas `/app` och `/static`.

## Scenario B — Jenny på mobilnät / inte hemma

Servern ska **fortfarande köra på Eriks PC**. Exponera den säkert med ett privat nätverk:

### Tailscale (gratis, rekommenderat)

1. Erik: installera [Tailscale för Windows](https://tailscale.com/download/windows).
2. Jenny: installera Tailscale på telefon (iOS/Android) och **gå med i samma tailnet** (samma konto eller inbjudan).
3. På Erik, kör servern med `--share` (och token):

```powershell
$env:APP_SHARE_TOKEN="välj-en-hemlig-sträng"
uv run python scripts/serve.py --share
```

4. I Tailscale-appen eller `tailscale ip -4` på Erik: notera **100.x.x.x**-adressen.
5. Skicka Jenny:

   `http://100.x.x.x:8642/app?token=välj-en-hemlig-sträng`

Brandvägg på Windows: tillåt port 8642 för Tailscale/privata profiler om det behövs.

### Cloudflare Tunnel (alternativ)

Om ni redan använder Cloudflare kan Erik köra `cloudflared tunnel` mot `localhost:8642`. Använd **alltid** `APP_SHARE_TOKEN` om tunneln når utanför hemmet. Se [Cloudflare Tunnel-dokumentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

## Miljövariabler

| Variabel | Syfte |
|----------|--------|
| `APP_SHARE_TOKEN` eller `SHARE_TOKEN` | Om satt: kräver `?token=...` eller header `X-Share-Token` för `/app` och `/static` |
| `APP_SHARE_MODE` | Sätts automatiskt av `--share` (visar “Dela” i sidfoten) |
| `APP_PORT` | Standard 8642 |

## Säkerhet

- Lägg **inte** token i git eller i en publik chatt utanför familjen.
- Öppna inte port 8642 direkt mot internet utan token och utan att ni förstår risken.
- `/health` och API-dokumentation (`/docs`) är avsiktligt utan token — håll tunneln/Tailscale privat.

## Om Jenny bara ser “Be Erik om länken med token”

Servern kräver token men länken saknar `?token=`. Erik skickar om hela länken inklusive token.
