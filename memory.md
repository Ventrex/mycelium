# Memory

Losse technische feiten/gotchas die het waard zijn te onthouden voor volgende sessies,
zodat ze niet opnieuw uitgezocht hoeven worden (scheelt tokens/tijd).

## APScheduler: nooit `next_run_time=None` doorgeven aan `add_job()`

APScheduler's eigen docstring: *"pass None to add the job as paused"*. Het lijkt intuïtief
"laat de trigger bepalen" te betekenen maar is het tegenovergestelde: de job krijgt nooit
een `next_run_time` en vuurt dus **nooit** af totdat je expliciet `.resume()` aanroept.
Laat de parameter gewoon helemaal weg (niet op `undefined` zetten, niet op `None`) -
APScheduler berekent hem dan automatisch uit de trigger zodra de scheduler start.
Dit was 2026-07-01 de oorzaak van een prio-0 bug die letterlijk alle 27 geplande taken
in `app.py` blokkeerde (zie Bugs.md).

## Zilean native implementatie (sinds PR #57, 2026-07-01)

- Databron: `github.com/debridmediamanager/hashlists` (community-gedeelde DMM hashlists).
  Elke pagina is een `.html` bestand met een `<iframe src="https://debridmediamanager.com/hashlist#<payload>">`.
  `<payload>` is LZString `compressToEncodedURIComponent` van een JSON-array `[{"filename":..,"hash":..,"bytes":..}, ...]`.
- Download: `https://github.com/debridmediamanager/hashlists/archive/refs/heads/main.zip`
  (codeload, geen GitHub-API rate limit). Stand 2026-07-01: ~1.46GB zip, ~14.271 html-pagina's.
- `lz_string.py`: eigen vendored decompressor (alleen decompress, geen compress). De PyPI-package
  `lzstring` faalt te installeren in sandbox-achtige omgevingen door een verouderde `setup.py` +
  `future`-afhankelijkheid die botst met moderne `setuptools`. Vandaar zelf gevendorde, dependency-vrije versie.
- **Val niet in de val van WebFetch voor lange opaque strings** (compressed data, tokens, etc.):
  de tool laat een klein/snel model de pagina "samenvatten", en dat kan onopgemerkt 1 teken
  in een lange base64-achtige blob veranderen (bewezen: 1 teken `-`→`+` in een 4880-char fragment,
  identiek gereproduceerd met de originele JS `lz-string` library via Node - dus geen bug in de
  eigen decompressor, puur een WebFetch-transcriptiefout). Gebruik curl/requests voor exacte bytes
  zodra byte-exactheid ertoe doet (compressie, hashes, tokens).
- Architectuur: zie CLAUDE.md ("Bestanden" tabel: `zilean_index.py`, `lz_string.py`, `zilean.py`).

## Repo/CI

- `.github/workflows/` bevat alleen `release.yml` (draait op releases/tags, niet op PR's).
  `pull_request_read get_status`/`get_check_runs` op een PR geeft dus altijd leeg terug -
  dat is verwacht, geen indicatie dat er iets stuk is.
- GitHub-scope voor deze sessie: alleen `Ventrex/mycelium`.

## Workflow-afspraken met Ventrex

- PR's altijd als draft aanmaken; nooit zelf mergen. Ventrex merget zelf na review.
- Na een feature-branch merge: `docker compose up -d --build --remove-orphans` gebruiken
  op de NAS (niet zomaar `--build`), anders blijven verwijderde services (zoals de oude
  zilean/zilean-postgres containers) als orphans draaien.
- Ventrex let op tokenverbruik (weeklimiet) - antwoorden kort houden waar mogelijk,
  niet onnodig heruitleggen wat al eerder is uitgelegd.
