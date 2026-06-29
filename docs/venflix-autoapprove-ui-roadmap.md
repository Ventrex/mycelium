# VenFlix roadmap: Auto-Approve, logs, navigation and profiles

## Context
Auto-Approve currently feels unreliable: sometimes it queues nothing for a while, sometimes a few titles. It also appears to mostly pick trending/popular content and series barely get added.

Current desired behaviour is different: Auto-Approve should fill the library per enabled genre, not from one shared global cap.

## Root cause found
`auto_approve.py` currently uses one shared `total_cap` across Movies + Shows and then visits eligible movie/tv genre streams round-robin.

Current behaviour:

- `AUTO_APPROVE_DAILY_LIMIT_MOVIE` is treated as the shared total cap.
- `AUTO_APPROVE_DAILY_LIMIT_TV` is only a series sub-cap.
- `AUTO_APPROVE_PER_GENRE_LIMIT` exists, but the shared total cap can stop the run before every genre reaches that limit.
- Series are easy to starve because movies and series share the same top-level budget.

Relevant current code:

- `auto_approve.py`
- `_fill_round_robin(total_cap, series_subcap, ...)`
- `run(total_limit=None, tv_limit=None)`

## Required change 1: Auto-Approve must be per genre
Change Auto-Approve so each enabled genre can queue its own target amount.

Example:

- Movies tab has 9 genres enabled.
- Per-genre movie target = 20.
- Auto-fill trending enabled for all 9.
- Result should attempt to queue 20 successful movies per genre = up to 180 movie requests.

Same for Shows:

- Shows tab has N genres enabled.
- Per-genre show target = 20.
- Result should attempt to queue 20 successful shows per genre.

Important rules:

- Already requested movies/shows must be skipped and must not count toward the per-genre target.
- Already monitored series must be skipped and must not count toward the per-genre target.
- Blacklisted movie/show/actor must be skipped.
- Unreleased content must be skipped.
- If a candidate fails because it already exists, is blacklisted, has no IMDb mapping, or processor rejects it, continue until the per-genre target is reached or TMDB pages are exhausted.
- Keep `min_votes`, `year_from`, `year_to`, rating filters and region support.
- Support separate per-genre limits for Movies and Shows.

Suggested setting names:

- `AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT`
- `AUTO_APPROVE_TV_PER_GENRE_LIMIT`
- `AUTO_APPROVE_MAX_PAGES`

The old daily global cap can remain as a safety cap if needed, but it must not block normal per-genre filling unless explicitly configured.

## Required change 2: Auto-Approve schedule configurable from Settings
Add UI settings to control when Auto-Approve runs.

Need options:

- Disabled
- Every hour
- Every X hours
- Daily at HH:MM, for example 04:00

Example desired config:

- Auto-Approve runs every night at 04:00.
- Or run every 1 hour.
- Or run every 5 hours.

Persist these in the settings table and make the scheduler use them without code changes.

Suggested settings:

- `AUTO_APPROVE_SCHEDULE_MODE`: `disabled | hourly | every_x_hours | daily_time`
- `AUTO_APPROVE_INTERVAL_HOURS`: integer
- `AUTO_APPROVE_DAILY_TIME`: `HH:MM`

Update `app.py` scheduler setup so Auto-Approve uses these settings.

## Required change 3: Separate Discord webhooks for Movies and Shows
Currently notifications go to one Discord webhook.

Add support for separate Discord webhooks:

- `DISCORD_WEBHOOK_URL_MOVIES`
- `DISCORD_WEBHOOK_URL_SHOWS`
- keep existing `DISCORD_WEBHOOK_URL` as fallback/default

Behaviour:

- Movie notifications go to Movies webhook if configured, else default webhook.
- TV/show notifications go to Shows webhook if configured, else default webhook.
- Keep enriched metadata from PR #27 if present.

## Required change 4: Logs in main UI, split by type
Move logs out of only Admin iframe-style view and expose them as a proper frontend page.

Add a main React page for logs, ideally admin-only.

Log categories:

- Server Logs: app/server/docker/backend general logs
- Auto-Approve Logs: all auto_approve runs, decisions, skipped reasons, queued counts
- Subtitles Logs: subtitle search/download/failure logs

Desired behaviour:

- Logs visible from normal React UI.
- Filter by type.
- Recent logs first.
- Include timestamp, level, type, message.
- Keep server-side buffer or database table for structured logs.

## Required change 5: Clean up navigation/sidebar
The left sidebar is too full.

Normal users should only see:

- Discover
- Shows
- Movies
- Library
- Watchlist
- Search
- My Requests
- Wanted
- Settings

Admin/Manage section should contain:

- Auto-Approve
- Blacklist
- Admin
- Subtitles
- Logs

Manual should move to the top-right as a book icon.

Profile should also move top-right. Clicking the profile opens a menu:

- Settings
- Manual
- Log out

Consider moving Search into the top bar to reduce sidebar size even more.

## Required change 6: Netflix-style profile selection after login
After login, show a profile picker with name + icon/avatar.

Concept:

- User logs in with account/email/password.
- Under that account, user can create family profiles.
- Each profile has:
  - display name
  - icon/avatar
  - age rating / allowed content level
  - optional kids mode

Content filtering:

- Discover/Movies/Shows should respect selected profile age limit.
- Requests should record which profile requested something.
- Watchlist/library preferences should be profile-aware.

This is bigger and should be a later PR. First implement backend schema and UI skeleton if needed.

## Suggested implementation phases

### Phase 1 — Auto-Approve backend fix

- Change Auto-Approve to per-genre target logic.
- Add structured logging for each genre.
- Keep existing UI mostly unchanged.
- Add tests.

### Phase 2 — Auto-Approve settings UI

- Add schedule controls.
- Add per-genre movie/show limit controls.
- Wire scheduler.

### Phase 3 — Discord split webhooks

- Add movie/show webhook settings.
- Route notifications by media type.

### Phase 4 — React navigation cleanup + logs page

- Move profile/manual top-right.
- Split Manage section.
- Add logs page.

### Phase 5 — Netflix-style profiles

- Add profile database tables.
- Profile picker after login.
- Age filtering.

## Acceptance criteria for Phase 1

- If 9 movie genres are enabled and movie per-genre limit is 20, the run attempts up to 180 successful movie queues.
- Duplicate/already requested items do not count toward the limit.
- Shows use their own per-genre limit and are not starved by movies.
- Logs clearly show per genre: scanned, skipped, queued, exhausted.
- `Run now` returns a useful summary: movies queued, shows queued, per-genre results.
- Existing tests still pass, except known unrelated tests if already failing before this work.
