# ToDo

Prioriteit: Hoog / Middel / Laag (grove inschatting, geef gerust zelf een andere prio mee).

## Hoog

- **Request-status database + "doorlopend ophalen zonder cap"** (idee van Ventrex, 2026-07-01): TorBox heeft geen harde opslaglimiet (gedeeld met andere gebruikers), dus Auto-Approve hoeft niet te stoppen bij een dagcap - het moet gewoon continu doorzoeken en morgen verdergaan waar het gebleven is. Voorstel: een aparte tabel/db die per item de status bijhoudt, bijvoorbeeld:
  - `aangevraagd` → `aanwezig in TorBox` → periodieke check of de `.strm` nog werkt (elke X uur/dagen)
  - Dit vervangt/vult de huidige `requests` + `virtual_items` tabellen aan met een expliciete voortgangsstatus per titel, zodat Auto-Approve niet steeds dezelfde TMDB-pagina's opnieuw hoeft te scannen om te bepalen wat al gedaan is.
  - Geschatte impact: rearchitectuur van een deel van `auto_approve.py` + `db.py`, ongeveer een dag werk (niet een quick fix).
- **Spore: aparte strm+mkv koppeling in dezelfde statustabel**: bovenstaande database kan per titel 2 locaties bijhouden (de `.strm` voor Jellyfin en de stub `.mkv` voor Plex/Spore), zodat Spore-stubs makkelijker in sync te houden zijn met de "hoofd" strm-registratie in plaats van een aparte scan (`regenerate_spore_stubs`).

## Middel

- **Bevestigen of Seerr daadwerkelijk verwijderd moet worden.** Zie Bugs.md - de code is nog volledig aanwezig. Als dit de bedoeling is: `seerr.py` verwijderen + alle referenties in `app.py`, `monitor.py`, `catchup.py`, `health.py`, `webhook_parser.py`, `config.py`, `settings.py` opschonen (vergelijkbare scope als de Zilean-opschoning).
- **Re-resolve knop in Library tab** (al genoemd in CLAUDE.md "Bekende open punten"): nu alleen via curl (`POST /ui/api/virtual-items/<token>/re-resolve`).
- **Playability state tabel in UI** (al genoemd in CLAUDE.md): backend-endpoint (`/ui/api/playability-state`) bestaat al, geen UI-weergave.

## Laag

- **Plex audio/subtitle wisselen na eerste play**: stub wordt na eerste play bijgewerkt met echte tracks, maar Plex moet daarna handmatig opnieuw analyseren ("Fix Incorrect Match"). Geen automatische trigger.
- **Root-cause van de 2 falende `test_strm_generator.py` tests bij volledige testsuite-run** (zie Bugs.md) - waarschijnlijk test-isolatie, geen productie-impact voor zover bekend, maar nog niet uitgezocht.
