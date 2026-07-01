# ToDo

Prioriteit: Hoog / Middel / Laag (grove inschatting, geef gerust zelf een andere prio mee).

## Hoog

- **Auto-Approve "doorlopend ophalen zonder cap"** (idee van Ventrex, 2026-07-01): TorBox heeft geen harde opslaglimiet, dus Auto-Approve hoeft niet te stoppen bij een dagcap - het moet continu doorzoeken en morgen verdergaan waar het gebleven is. **Nog niet gedaan** - dit vereist een rearchitectuur van de scan-cursor/limiet-logica in `auto_approve.py` zelf (los van de zichtbaarheid, die inmiddels wel is opgelost, zie Bugs.md 2026-07-01 "Auto-approved series waren onzichtbaar"). Geschatte impact: ongeveer een dag werk.
- **Spore: aparte strm+mkv koppeling per titel**: `library_status.py` (nieuw, 2026-07-01) aggregeert nu wel status over `virtual_items`, maar koppelt nog niet expliciet een Jellyfin-strm-locatie aan een Plex-stub-mkv-locatie voor hetzelfde item. Zou `regenerate_spore_stubs` als aparte scan kunnen vervangen door een directe koppeling in dezelfde view/tabel.

## Middel

- **Bevestigen of Seerr daadwerkelijk verwijderd moet worden.** Zie Bugs.md - de code is nog volledig aanwezig. Als dit de bedoeling is: `seerr.py` verwijderen + alle referenties in `app.py`, `monitor.py`, `catchup.py`, `health.py`, `webhook_parser.py`, `config.py`, `settings.py` opschonen (vergelijkbare scope als de Zilean-opschoning).
- **Re-resolve knop in Library tab** (al genoemd in CLAUDE.md "Bekende open punten"): nu alleen via curl (`POST /ui/api/virtual-items/<token>/re-resolve`).
- **Playability state tabel in UI** (al genoemd in CLAUDE.md): backend-endpoint (`/ui/api/playability-state`) bestaat al, geen UI-weergave.

## Laag

- **Plex audio/subtitle wisselen na eerste play**: stub wordt na eerste play bijgewerkt met echte tracks, maar Plex moet daarna handmatig opnieuw analyseren ("Fix Incorrect Match"). Geen automatische trigger.
- **Root-cause van de 2 falende `test_strm_generator.py` tests bij volledige testsuite-run** (zie Bugs.md) - waarschijnlijk test-isolatie, geen productie-impact voor zover bekend, maar nog niet uitgezocht.
