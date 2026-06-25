# Changelog

All notable changes to Mycelium are documented in this file.

## [Unreleased]

### Added

- **Subliminal subtitle fallback**: multi-provider subtitle search (Addic7ed, TVsubtitles, Gestdown, BSPlayer), free and no API key needed, used as an extra/fallback subtitle source alongside OpenSubtitles for `.strm` generation (movies and series) and the web player's in-browser subtitle search. Shares `OPENSUBTITLES_LANGUAGES` for language selection; toggle with `SUBLIMINAL_ENABLED` (on by default).
- **Self-hosted Zilean in docker-compose.yml**: `zilean` + `zilean-postgres` services bundled directly in the compose file, behind a `zilean` profile so they only start when opted in (`docker compose --profile zilean up -d`). Set `ZILEAN_URL=http://zilean:8181` to use the bundled instance instead of an external one.
- **Bazarr in docker-compose.yml** as an alternative subtitle source: `radarr` + `sonarr` + `bazarr` services bundled behind a `bazarr` profile (`docker compose --profile bazarr up -d`). Radarr/Sonarr run in metadata-only mode (no indexers/download client needed) purely so Bazarr knows what's in the library.

### Fixed

- **bsplayer log noise**: the subliminal library logged a full traceback at ERROR level on every retry against an unreachable mirror; now silenced (and its connect timeout lowered to 5s) since `subliminal_fallback.py` already reports the same failure as one clean line.

### Removed

- **Podnapisi subtitle provider**: the domain has gone offline (DNS no longer resolves); removed in favor of the subliminal-based fallback above.

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
