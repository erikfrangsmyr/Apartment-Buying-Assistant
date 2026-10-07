# Genväg på skrivbordet (Windows)

## En gång

1. I projektmappen (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create-desktop-shortcut.ps1
```

2. (Valfritt) Token och LAN-delning:

```powershell
copy scripts\share.local.ps1.example scripts\share.local.ps1
notepad scripts\share.local.ps1
```

Sätt `$AppShareToken` om du använder `APP_SHARE_TOKEN`, och `$ListenShare = $true` om Jenny ska nå servern på Wi‑Fi/Tailscale (`--share`).

## Varje gång

Dubbelklicka **Apartment Buying Assistant** på skrivbordet.

- Ett **serverfönster** öppnas (lämna det öppet medan du använder appen).
- Webbläsaren öppnas på `http://127.0.0.1:8642/app` (med `?token=...` om du satte token i `share.local.ps1`).

Om servern redan kör på samma port öppnas bara webbläsaren.
