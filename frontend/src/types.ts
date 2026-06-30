export type MediaType = 'movie' | 'tv';

export interface TmdbItem {
  tmdb_id: number;
  media_type: MediaType;
  title: string;
  original_title?: string;
  year: string | null;
  rating: number;
  votes: number;
  popularity: number;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  genre_ids?: number[];
  library_status?: string | null;
  original_language?: string;
}

export interface Provider {
  id: number;
  name: string;
  logo_path: string | null;
  priority?: number;
}

export interface TmdbDetail extends TmdbItem {
  imdb_id?: string;
  runtime?: number;
  genres?: string[];
  tagline?: string;
  status?: string;
  homepage?: string;
  seasons?: Array<{
    season_number: number;
    episode_count: number;
    name: string;
    poster_path: string | null;
    air_date: string | null;
  }>;
  number_of_seasons?: number;
  number_of_episodes?: number;
  cast?: Array<{ id?: number; name: string; character: string; profile_path: string | null }>;
  trailers?: Array<{ key: string; name: string; site: string }>;
  providers?: { flatrate: Provider[]; link: string | null };
  recommendations?: TmdbItem[];
  collection?: {
    id: number;
    name: string;
    poster_path: string | null;
    backdrop_path: string | null;
  } | null;
  is_blacklisted?: boolean;
  virtual_item_token?: string;
  info_hash?: string;
  release_quality?: string | null;
}

export interface Genre {
  id: number;
  name: string;
}

export interface Language {
  iso_639_1: string;
  english_name: string;
  name: string;
}

export interface LanguagePrefs {
  allowed: string[];
  excluded: string[];
}

export interface DiscoverPrefs {
  hidden_genres: number[];
  genre_order: number[];
  year_from: number | null;
  year_to: number | null;
  genre_years: Record<string, { from: number | null; to: number | null }>;
}

export interface AutoApproveRule {
  enabled: boolean;
  year_from: number | null;
  year_to: number | null;
  auto_request_trending: boolean;
  min_votes: number | null;
}

export type AutoApproveRules = Record<string, AutoApproveRule>;

export type AutoApproveScheduleMode = 'disabled' | 'hourly' | 'every_x_hours' | 'daily_time';

export interface AutoApproveSettings {
  schedule: {
    mode: AutoApproveScheduleMode;
    interval_hours: number;
    daily_time: string;
    daily_hour?: number;
    daily_minute?: number;
    description?: string;
  };
  description: string;
  movie_per_genre_limit: number;
  tv_per_genre_limit: number;
  max_pages: number;
}

export interface AutoApproveSettingsInput {
  schedule_mode: AutoApproveScheduleMode;
  interval_hours: number;
  daily_time: string;
  movie_per_genre_limit: number;
  tv_per_genre_limit: number;
  max_pages: number;
}

export interface NotificationSettings {
  discord_webhook_url: string;
  discord_webhook_url_movies: string;
  discord_webhook_url_shows: string;
  notify_on_success: boolean;
  notify_on_failure: boolean;
}

export type LogType = 'server' | 'auto_approve' | 'subtitles';

export interface LogEntry {
  time: string;
  level: string;
  type: LogType;
  name: string;
  message: string;
}

export interface TmdbPerson {
  tmdb_id: number;
  media_type: 'person';
  name: string;
  profile_path: string | null;
  known_for_department: string | null;
  popularity: number;
  known_for: TmdbItem[];
}

export type FilmographyItem = TmdbItem & { character?: string };

export interface PersonDetail {
  tmdb_id: number;
  name: string;
  biography: string;
  profile_path: string | null;
  birthday: string | null;
  place_of_birth: string | null;
  known_for_department: string | null;
  filmography: FilmographyItem[];
  is_blacklisted?: boolean;
  is_favorite?: boolean;
}

export type BlacklistKind = 'movie' | 'tv' | 'person';

export interface ContentBlacklistItem {
  id: number;
  kind: BlacklistKind;
  tmdb_id: number;
  title: string;
  image: string | null;
  created_at: string;
}

export interface FavoriteActor {
  tmdb_id: number;
  name: string;
  profile_path: string | null;
  created_at: string;
}

export interface Collection {
  tmdb_id: number;
  name: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  parts: TmdbItem[];
}

export interface WatchlistItem {
  id: number;
  user_id: number;
  imdb_id: string;
  tmdb_id: number | null;
  media_type: MediaType;
  title: string;
  poster_path: string | null;
  added_at: string;
}

export interface UserRecord {
  id: number;
  username: string;
  role: 'admin' | 'user';
  quota_monthly: number;
  auto_approve: boolean;
  enabled: boolean;
  last_login: string | null;
  created_at: string;
}

export interface UserRequest {
  id: number;
  user_id: number;
  username?: string;
  imdb_id: string;
  tmdb_id: number | null;
  media_type: MediaType;
  title: string;
  status: 'pending' | 'approved' | 'denied';
  reviewed_at: string | null;
  note: string | null;
  created_at: string;
}


export interface Profile {
  id: number;
  user_id: number;
  name: string;
  avatar: string;
  age_rating: 'all' | '6' | '9' | '12' | '16' | '18';
  kids_mode: boolean;
  created_at: string;
  updated_at: string;
}

export interface SessionInfo {
  authenticated: boolean;
  jellyfin_url?: string | null;
  profiles_required?: boolean;
  selected_profile?: Profile | null;
  user?: {
    id: number;
    username: string;
    role: string;
    auto_approve: boolean;
    region: string;
    library_click_jellyfin?: boolean;
  } | null;
}

export interface WantedMovie {
  imdb_id: string;
  tmdb_id: number | null;
  title: string;
  reason: string | null;
  attempts: number;
  added_at: string;
  last_checked: string | null;
}

export interface WantedEpisode {
  id: number;
  imdb_id: string;
  tmdb_id: number | null;
  title: string;
  season: number;
  episode: number;
  air_date: string | null;
  status: string;
  attempt_count: number;
  first_attempted: string | null;
  last_attempted: string | null;
}

export interface SubtitleItem {
  title: string;
  year?: string | null;
  media_type: 'movie' | 'series';
  imdb_id: string | null;
  season?: number | null;
  episode?: number | null;
  strm: string;
  languages: string[];
}
