# Bugs

Prioriteit: 0 = breaking, 1 = belangrijk maar geen show-stopper, 2 = klein/cosmetisch.
Vink af (of verwijder de regel) zodra iets is opgelost en gepushed.

## Open

- **[1] test_strm_generator.py: 2 falende tests** - `TestWriteSporeStubs::test_creates_mkv_and_minfo` en `test_minfo_size_in_bytes` falen als de hele testsuite in 1 run draait (test-isolatie probleem, niet gereproduceerd als het bestand los draait). Faalt ook al op `main` vóór de Zilean-integratie, dus geen regressie - maar nog niet root-cause gefixt.
- **[?] Seerr claim vs code**: er werd aangenomen dat Seerr al verwijderd was, maar `seerr.py` en alle referenties (`app.py`, `monitor.py`, `catchup.py`, `health.py`, `webhook_parser.py`, `config.py`, `settings.py`) staan nog volledig actief in de codebase. Niet aangeraakt totdat bevestigd is of dit bewust moet gebeuren (zie ToDo.md).

## Opgelost

- **[0] Achtergrondtaken draaiden nooit automatisch** (2026-07-01): `scheduler.add_job(..., next_run_time=None)` werd overal in `app.py` gebruikt (27x) in de veronderstelling dat dit "laat de trigger bepalen" betekent. APScheduler's eigen documentatie zegt echter: `next_run_time=None` voegt de job **gepauzeerd** toe - hij krijgt nooit een eerstvolgende looptijd en vuurt dus nooit af, tenzij je expliciet `.resume()` aanroept (wat nergens gebeurde). Dit trof **elke** geplande taak: Auto-Approve, subtitle-herhaling (die sowieso geen schema had), strm-generator refresh, cleanup, monitor, auto-upgrade, season-pack consolidatie, wanted-recheck, trending, continue-watching, merge-versions, quota-check, watchdogs, prune, vacuum, retry-queue, catbox-gc, backup, en de nieuwe zilean-sync. Empirisch bevestigd met een losse APScheduler-test (0 van de verwachte runs zonder fix, correcte runs na verwijderen van de parameter). Fix: verwijder `next_run_time=None` overal, laat APScheduler het automatisch berekenen uit de trigger.
- **[0] Zilean "inactief"** (2026-07-01, PR #57): `ZILEAN_URL`/`ZILEAN_ENABLED` werden in `zilean.py`, `health.py`, `health_cache.py` en `app.py` als bevroren opstartwaarde uit `config.py` gelezen in plaats van via `settings.get()`. Wijzigingen via de Settings-UI werden dus genegeerd. Zilean is bovendien native ingebouwd (geen externe container meer), waardoor dit hele netwerk-afhankelijke faalpad nu weg is.
- **[1] Geen periodieke subtitle-herhaling** (2026-07-01): `strm_generator.backfill_all_subtitles()` bestond alleen als handmatige actie (`/ui/api/subtitles/search-all`), er was geen scheduled job. Toegevoegd: `SUBTITLE_BACKFILL_INTERVAL_HOURS` (default 6u).
