# Changelog

All notable changes to Mycelium are documented in this file.

## [Unreleased]

### Added

- **"From the same creators" recommendations + crew on the detail page**: the movie/series detail view now lists the key crew (director / writer / showrunner) next to the cast, and a new row suggests other titles by the same writer/showrunner/director in an overlapping genre (e.g. My Name is Earl → Raising Hope via Greg Garcia). Backed by `tmdb.by_creators()` and `GET /ui/api/discover/by-creator`. Auto-requesting these is a planned follow-up.
- **Auto-approve fills whole movie collections**: when auto-approve queues a film that belongs to a TMDB collection (e.g. requesting Toy Story 4 also pulls Toy Story 1-3 and any future entry), the rest of the collection is queued too. On by default (`AUTO_APPROVE_FILL_COLLECTIONS`), blacklisted entries are skipped, and it never recurses.
- **Favorite actors also pull upcoming titles**: the favorite-actor auto-request no longer skips unreleased work, so future films become `upcoming` requests that are picked up on release and future series are monitored from the start (a long-deceased actor like Leslie Nielsen simply yields their full back catalogue).
- **Favorite actors now request the whole filmography by default**: the favorite-actor auto-request used to take only the 3 most recent (≤1 year) titles per actor. It now defaults to the actor's entire back catalogue with no per-actor cap (`FAVORITE_ACTOR_PER_ACTOR_LIMIT=0`, `FAVORITE_ACTOR_RECENCY_YEARS=0`, both tunable), still bounded by the daily budget. Soap operas (TMDB genre 10766) are now skipped alongside talk/news/reality, so one-off soap/talk-show guest spots are excluded, while real scripted guest roles (e.g. Bruce Willis in Friends) are still requested.
- **Per-series "Fill missing episodes"**: the series detail view now has a button that scans that one series for missing whole seasons (newly announced seasons included) and missing episodes, then requests them immediately - instead of only the global Wanted recheck. Backed by `monitor.recheck_series()` and `POST /ui/api/library/series/<imdb>/recheck`. (The automatic 6-hourly monitor already did this library-wide; this makes it on-demand per series.)
- **MDBList integration (per user)**: each user can connect their own MDBList API key from the Settings page; their MDBList lists sync into their watchlist every 30 minutes. With `MDBLIST_AUTO_REQUEST` enabled, synced items are also requested (downloaded), throttled to `MDBLIST_AUTO_REQUEST_LIMIT` new items per sync run, skipping already-requested/monitored titles. New `mdblist` plugin with its own `mdblist_keys` table and `/ui/api/mdblist/*` endpoints.
- **Daily trending auto-request**: with `AUTO_REQUEST_TRENDING` enabled, the top trending movies and shows are requested once a day, capped per type (`AUTO_REQUEST_TRENDING_MOVIE_LIMIT` / `AUTO_REQUEST_TRENDING_TV_LIMIT`, default 10 each). Reuses the same safety rules as the genre fill (skips already-requested, monitored, blacklisted and unreleased titles). Off by default; configurable under Admin → Settings → Automation, with a `POST /ui/api/trending-request/run-now` endpoint to trigger it manually.
- **Trakt watchlist auto-request**: with `TRAKT_AUTO_REQUEST` enabled, items synced from each user's Trakt watchlist are not just added to the Mycelium watchlist but also requested (downloaded). Throttled to `TRAKT_AUTO_REQUEST_LIMIT` new items per 30-minute sync run so it drains the backlog without flooding TorBox; already-requested movies and monitored series are skipped, and the normal quality filters apply. Configurable under Admin → Settings → Connections.
- **Self-hosted Zilean in docker-compose.yml**: `zilean` + `zilean-postgres` services bundled directly in the compose file, behind a `zilean` profile so they only start when opted in (`docker compose --profile zilean up -d`). Set `ZILEAN_URL=http://zilean:8181` to use the bundled instance instead of an external one.
- **Auto-Approve fills each genre to its own independent target**: every "Auto-fill trending" genre is filled separately up to its own per-genre limit (`AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT` / `AUTO_APPROVE_TV_PER_GENRE_LIMIT`), scanning up to `AUTO_APPROVE_MAX_PAGES` TMDB pages per genre. Movies and series have separate limits so films can no longer starve series and one genre cannot consume another's target (e.g. 9 movie genres at 20 = up to 180 movie queues). Already-requested movies, monitored series, blacklisted/unreleased/no-IMDb titles, filter misses and processor failures never count toward a target. Run-now returns a summary (`movies_queued`, `series_queued`, `total_queued`) and logs per genre: `scanned / skipped / queued / exhausted`.
- **Auto-Approve scheduling and limits editable from the UI**: the Auto-Approve tab now has a settings card to pick a schedule mode (Disabled / Every hour / Every X hours / Daily at HH:MM) and adjust the per-genre limits and max pages. Values persist in the settings DB and the scheduler reconfigures itself live (`AUTO_APPROVE_SCHEDULE_MODE`, `AUTO_APPROVE_INTERVAL_HOURS`, `AUTO_APPROVE_DAILY_TIME`).
- **Mobile-friendly layout**: the sidebar collapses into a drawer on small screens with a clear hamburger button, overlay and close button, is width-capped so it never exceeds the viewport, and the menu scrolls when long. The page no longer overflows horizontally and the header/content get sensible mobile padding. Desktop layout is unchanged.
- **Separate Discord webhooks for movies and shows**: movie notifications can go to `DISCORD_WEBHOOK_URL_MOVIES` and series to `DISCORD_WEBHOOK_URL_SHOWS`, each falling back to the shared `DISCORD_WEBHOOK_URL` when left empty.
- **Netflix-style profiles**: after signing in you pick a profile ("Who is watching?") before the app opens. Each account can have multiple profiles (name, avatar, age rating, kids mode), a default profile is auto-created from the username, the chosen profile is shown top-right, and the profile dropdown has a "Switch profile" option. Backed by the `profiles` table and `/ui/api/profiles` endpoints; `/ui/api/session` returns the selected profile and whether a choice is still required.
- **Age-appropriate Discover per profile**: the active profile's age rating / kids mode now hides mature genres (horror, thrillers, and also crime/war for the youngest) from Discover, Search and recommendations. Genre-based and safe: it never depends on TMDB certification data, so nothing crashes when that is missing, and 'all'/16/18 profiles see everything.
- **Cleaner profile picker**: the profile screen now shows just the profiles by default; add/edit lives behind a "Manage profiles" button and opens in a dialog instead of always being visible.
- **Logs page in the React UI**: a new admin-only Logs page (`/logs`, in the sidebar Manage section) with Server / Auto-Approve / Subtitles category tabs, newest-first, a refresh button and live auto-refresh. Backed by `GET /ui/api/logs?type=…`; the in-memory log buffer now stores structured entries (time, level, type, logger, message) and categorises each line by its logger.
- **Search bar in the topbar**: the search icon is now a real input box; typing and pressing Enter opens the Search page pre-filled via `?q=`. Desktop layout unchanged, shrinks on mobile.
- **Notifications section in the React Settings page**: admins can now set the default/movies/shows Discord webhooks and the notify-on-success/failure toggles directly from the main Settings page, instead of only the embedded `/admin` dashboard.
- **Per-release blacklist**: a "Wrong release" button on the detail view for any movie already in the library lets you reject just the current release (e.g. 4K but Russian audio) without removing the title - the release is blacklisted, its TorBox torrent is dropped, and a fresh search for a different release runs immediately.
- **Audio language preserved on auto-upgrade**: the resolution auto-upgrade job no longer swaps in a higher-quality release whose audio language doesn't match what's currently playing (untagged releases are treated as English; multi-audio releases are always compatible). Fixes a 1080p English release silently being "upgraded" to a 4K release dubbed in another language.

- **Favorite actors are clickable**: favorite-actor posters on the Auto-Approve page now open the actor's page and filmography (previously only a Remove button).

### Fixed

- **Requesting a series sometimes did nothing until the next monitor run**: when a freshly requested series had nothing cached on TorBox yet, its wanted-episode rows were only created on a successful immediate fetch, so otherwise the series sat monitored-but-empty until the 6-hourly monitor ran (looking like "requesting a series doesn't work"). A series request now always creates its wanted episodes and immediately runs a recheck to fetch whatever is available, instead of waiting. Also logs `Series request: <title> - monitoring seasons …`.
- **Multi-season series only got season 1 in the library**: when a series request spanned several seasons, each season is its own torrent pack, but only the first winning pack was materialised into `.strm` files. The remaining seasons were added to TorBox but never written to disk, so Jellyfin (and the folders) showed only Season 1. Every season's winning torrent now gets `.strm` files generated. (Catbox/lazy mode already wrote per-season during registration and is unaffected.)
- **Type-checking is clean again**: `tsc --noEmit` now passes with no errors. Added the missing Vite client types (`vite-env.d.ts`) so `import.meta.glob` in the plugin loader is typed, and completed the `TmdbItem.imdb_id` / `WatchlistItem.library_status` interfaces. This restores `tsc` as a guard against latent undefined-reference bugs like the blank-screen crash below.
- **Whole SPA showed a blank screen**: `Layout.tsx` called `useNavigate()` without importing it (an unused leftover), throwing a `ReferenceError` that crashed the entire React app on render. The dead call was removed so the app loads again.
- **Notifications crashed with `NameError: _discord_url_for`**: `notify.send()` called a helper that was never defined, so every Discord/Telegram notification raised and sent nothing. The helper is now implemented and selects the movies/shows webhook with a fallback to the default.
- **Auto-approve crashed on a saved minimum-rating**: `AUTO_ADD_MIN_RATING` was not registered as a float setting, so a value saved from the Settings UI came back as a string and the rating comparison (`rating < min_rating`) raised a `TypeError` that aborted the entire auto-approve run, queueing nothing. Float overrides are now parsed correctly, the rating/votes comparison coerces defensively, and one malformed title can no longer abort the whole run.
- **Unreleased movies got a .strm and showed in the library**: pre-release blockbusters (e.g. an unreleased Moana sequel) attract fake/junk cached torrents that the lazy path accepted, writing a `.strm` that appeared in Jellyfin and played garbage. Auto-approve now skips titles whose release/air date is in the future, and the processor refuses any movie that TMDB reports is not released yet (marking it `upcoming` to recheck later).
- **OpenSubtitles 406 errors hid the real reason**: download failures only logged the generic HTTP status, not OpenSubtitles' own error message (e.g. "daily quota exceeded"); now surfaced in the log line.
- **Auto-Approve reported success even when nothing was added**: the daily genre-fill job logged "N item(s) queued" and counted it against the per-genre/daily cap based only on whether `processor.process()` raised an exception, not its actual return value, so titles that ended up `wanted`/`failed`/`rate_limited` were silently counted as successes, capping the run early instead of trying more candidates.
- **Jellyfin library refresh spammed on every new .strm**: every new request, upgrade, or cleanup pass triggered its own `/Library/Refresh` call regardless of whether one had just run or Jellyfin was already mid-scan. Refreshes are now debounced (coalesced within a 60s window) and skipped entirely while Jellyfin reports a scan already in progress.
- **Hourly self-heal only logged, never repaired**: the hourly `.strm` health sample warned when a chunk of probed files were dead but left the actual fix to the next scheduled (daily) cleanup. It now triggers a cleanup pass immediately for Fixed-mode CDN links, and re-resolves the worst-degraded catbox items directly using their tracked failure history.

### Removed

- **Podnapisi subtitle provider**: the domain has gone offline (DNS no longer resolves); removed with no replacement.

## [0.5.6] - 2026-06-24

### Added

- **Content-language filter for Discover/Search**: allow/exclude titles by their TMDB original language, so e.g. Hindi-language (Bollywood) films can be hidden entirely. New language picker in the Movies/Shows and Search views. Separate from the existing audio-language release preference.
- **Blacklist teardown**: blacklisting a movie or show now removes that single title everywhere instead of only hiding it: its torrent is deleted from TorBox, its `.strm` files are removed, and the matching item is deleted from Jellyfin (matched on TMDB/IMDb provider id). Runs in the background; the TorBox account and Jellyfin server themselves are untouched.
- **Daily auto-approve with a cap**: the auto-approve scan now runs once per day at a configurable hour (`AUTO_APPROVE_DAILY_HOUR`) with a global per-run limit (`AUTO_APPROVE_DAILY_LIMIT`, default 100) so a single day cannot flood TorBox. Already-requested movies and monitored series are skipped, so nothing is queued twice.
- **Clickable cast**: actors in the detail view open a person page with their filmography, requestable directly.
- **Series library as posters**: the Library shows series as posters with browsable seasons and episodes; cached episodes are playable inline.
- **Search instant-play**: request and play a title directly from search, Netflix-style.

## [0.5.2] - 2026-06-12

### Added

- **Web Player VA-API**: hardware-accelerated HEVC transcoding via VA-API (`renderD128`); reduces CPU usage significantly on supported hardware
- **Web Player HEVC-always**: HEVC is always transcoded to HLS regardless of codec; direct serve only for H264 to avoid browser incompatibility
- Docker Compose: `videodriver` GID 937 added for VA-API `renderD128` access
- **Spore wrapper EAE detection**: also detects EAE need from output encoder args (e.g. Shield TV requesting `eac3_eae` output via eARC); skips injecting native decoder hint when output is `copy` to prevent EAE init failures on HTTP input

### Fixed

**Web Player**
- Black screen / corrupt green output on 10-bit HEVC with VA-API (Apollo Lake J3455)
- `scale_vaapi` failure on 10-bit HEVC sources
- Stale segments causing black screen after seek or restart
- Missing `/direct`, `/convert-hls`, `/hls-status` routes
- HLS buffer increased to prevent stalls on slow CDN
- Temp directory leak when HLS conversion crashes before session registration
- `ffmpeg.log` file handle not closed on `Popen` failure
- `shutil.rmtree` called before ffmpeg process exits (race condition)

**Security**
- Session fixation: `session.clear()` now called before writing new session keys on login
- `/torbox-webhook` and `/ui/api/repair-strms` now require authentication
- `/setup/save` now validates against a known-key allowlist (previously accepted arbitrary keys)
- `/health` no longer leaks internal exception details in the response body

**Data integrity**
- `cleanup.py`: new strm written via `process_torrent` before the old one is deleted
- `upgrader.py`: season-pack strms written before per-episode strms are removed
- `mp4_faststart.py`: `.fsh` cache written atomically via temp-file + rename; ftyp box fetched at actual size instead of hardcoded 64 bytes

**Logic**
- `torbox.py`: `metaDL_done` state never matched because `download_state` is lowercased before comparison — fixed to `metadl_done`
- `torbox.py`: createtorrent quota now recorded after HTTP success, not before (prevented quota inflation on network errors)
- `torrentio.py`: season-pack regex `s0?N` → `s0*N(?!\d)` to correctly match zero-padded season codes
- `catbox.py`: `release_idle()` no longer aborts on first network error — each torrent deletion is now wrapped in try/except
- `monitor.py`: aired episodes without a strm are now marked `wanted` in the DB (were silently left without status)
- `retry_queue.py`: startup crash on undefined `_CREATETORRENT_LIMIT` constant (should be `_CREATETORRENT_LIMIT_HOUR`)
- `db.py`: `_migrate()` ALTER TABLE loop now catches per-column errors instead of aborting remaining migrations

**Fresh install**
- Fixed crash `sqlite3.OperationalError: no such table: settings` on first boot when the DB is empty ([#34](https://github.com/corveck79/mycelium/issues/34))

---

## [0.5.1-dev] - 2026-05-29

### Added

- **Library poster grid**: movies tab now shows a paginated poster grid (24/page) with the same look as Discover and Watchlist
- **Library search and filters**: search box and All / Available / Wanted filter tabs in the movies view
- **Open in Jellyfin preference**: per-user toggle in Settings > Preferences; clicking a library poster opens the item directly in Jellyfin web instead of the detail modal
- **Jellyfin batch lookup**: Jellyfin item IDs are pre-fetched in one call so poster clicks are synchronous (no popup-blocker issues)
- **Lazy poster loading**: posters missing from the local cache are fetched on first render without blocking the page

### Fixed

- GitHub Actions arm64 build crash: removed dead `spore-builder` Dockerfile stage that compiled a C LD_PRELOAD library using `stat64`/`__xstat64` which do not exist on aarch64
- Jellyfin click mode not working after toggle: Settings now uses an optimistic session-cache update so Library reacts instantly without a page reload
- Detail modal not opening for older items that lack a stored `tmdb_id` (now resolved via `/ui/api/tmdb/find`)

---

## [0.5.0-dev] - 2026-05-28

### Added

- **Mycelium Spore** (experimental Plex integration): stream via stub MKV library + transcoder wrapper, no rclone or local storage required
- **Spore fast-start cache**: moov-first MP4 cache (`.fsh` files) built on first play so subsequent plays are instant
- **Spore track persistence**: audio/subtitle tracks and duration saved to DB after first ffprobe; stubs are regenerated with real tracks on container restart
- **Spore CDN preload**: fast-start cache and ffprobe run automatically when a CDN URL is first resolved, so first play is instant even before user interaction

### Fixed

- TorBox outage no longer causes a 6-hour retry delay for affected items
- HDR10+ no longer treated as a valid HDR10 fallback in the Dolby Vision P5 filter
- Bulk rename for items stored with raw IMDB codes as title (Admin > Maintenance > Fix IMDB titles)
- HEVC compatibility fix in the webplayer plugin for browser playback

---

## [0.4.2] - 2026-05-25

### Added

- `WEBHOOK_SECRET` auto-generation with copy button in admin Settings
- Metrics endpoint secured with optional Bearer token
- Rate limiting on authentication endpoints

### Fixed

- Setup wizard now closes after first run (re-open via Settings)
- WebDAV auth hardening and security headers

---

## [0.4.1] - 2026-05-25

### Added

- Docker Hub CI/CD pipeline on release tags (multi-arch images)
- Splash screen as login background

---

## [0.4.0] - 2026-05-25

### Added

- `LITE_MODE` for webhook-only deployments without heavy background schedulers
- Settings tab in admin dashboard (hot-reload quality filters and runtime config)

### Changed

- Setup wizard UI improved

---

## [0.3.0-beta] - 2026-05-24

### Added

- **Web Player plugin**: in-browser HLS player with subtitle picker
- **Trakt plugin**: watchlist sync and ratings integration
- **Plugin slot system**: plugins can inject components into the frontend (episode player, settings cards)
- Web Player: HDR detection and SDR-only release selection for browser compatibility
- Web Player: multi-audio HLS master playlist with separate audio streams

---

## [0.2.0-beta] - 2026-05-22

### Added

- **Multi-user authentication** with roles (admin/user) and pending approval flow
- **OIDC/SSO support** for single sign-on
- Users tab in admin with pending approval management
- Redesigned React SPA: Library status indicators, region picker

### Fixed

- Open redirect vulnerability on login
- `/setup` accessible without authentication

---

## [0.1.0-beta.1] - 2026-05-22

First public beta. Mycelium has been running in production for several
users; this release formalizes versioning and adds CI/CD.

### Added

- **React SPA** with Discover, Library, Watchlist, Search, Requests, and Wanted pages
- **Setup wizard** walks through TorBox, Jellyfin, TMDB, quality preferences, and Catbox config on first launch
- **Catbox mode** (lazy materialization): torrents added to TorBox on-demand at playback, removed after idle
- **Multi-user auth** with password and OIDC support, role-based access (admin/user)
- **Auto-upgrade**: background job upgrades existing releases when better quality becomes available
- **Season pack consolidation**: replaces individual episode files when a full season pack is found
- **Zilean + Torrentio combined search**: both sources queried and deduplicated for maximum coverage
- **Checkcached batching**: hashes sent in groups of 100 to avoid 414 URI Too Long errors
- **Language filtering**: exclude unwanted audio languages, prefer specific languages
- **Dolby Vision Profile 5 filter**: blocks DV releases without HDR10 fallback layer
- **Separate EXCLUDE_BLURAY option**: BluRay encodes allowed by default, remux filtered separately
- **Blacklist system**: failed info_hashes tracked and excluded from future attempts
- **Playability state tracking**: per-item failure reasons (TB_429, NO_RELEASE, TIMEOUT, etc.)
- **Discord and Telegram notifications** on success/failure
- **OpenSubtitles integration** for automatic subtitle downloads
- **WebDAV server** (optional) for Plex/Emby compatibility
- **RealDebrid support** as fallback debrid provider
- **Radarr/Sonarr bulk import** for migrating existing libraries
- **Community install guide** by Ventrex (EN/NL, Proxmox/NAS)
- **Admin dashboard** with Overview, Requests, Blacklist, Maintenance, Settings, and Logs tabs
- **Pagination** on admin tables (25/50/100/250 rows)
- **CI/CD**: GitHub Actions builds multi-arch Docker images on tag push to GHCR

### Fixed

- Startup crash when duplicate imdb_id rows exist in requests table
- Monitor loop continuing after checkcached 429 (now backs off 60s in catbox mode)
- Upgrader crash from renamed rate limit constant
- Source field showing first word of torrent name instead of torrentio/zilean
- REMUX filter blocking all BluRay encodes (now only blocks actual remux)

### Changed

- Admin page embeds seamlessly in SPA (no double topbar when accessed via sidebar)
- Admin colors matched to SPA palette
- Repair tab renamed to Maintenance with grouped action cards
- Quality preferences and filters are hot-reloadable via Settings (no restart needed)
