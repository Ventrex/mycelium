import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, tmdbImg } from '../api';
import { usePluginSlot } from '../hooks/usePluginSlots';
import { useWatched } from '../hooks/useWatched';
import DetailModal from '../components/DetailModal';
import type { TmdbItem } from '../types';

type Tab = 'movies' | 'series';

const PAGE_SIZE = 24;

export default function Library() {
  const [tab, setTab] = useState<Tab>('movies');
  return (
    <div>
      <div className="flex gap-2 border-b border-border mb-5">
        {(['movies', 'series'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize transition ${
              tab === t ? 'border-accent text-white' : 'border-transparent text-muted hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === 'movies' ? <MoviesPanel /> : <SeriesPanel />}
    </div>
  );
}

function MoviesPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['library-movies'],
    queryFn: api.libraryMovies,
  });
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });
  const canPlay = !!(session?.user as any)?.webplayer_enabled;
  const clickJellyfin = !!(session?.user as any)?.library_click_jellyfin;
  const jellyfinUrl = session?.jellyfin_url ?? null;
  const watched = useWatched();
  const MoviePlayer = usePluginSlot('movie-player');

  const [playMovie, setPlayMovie] = useState<{ imdb_id: string; title: string } | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<'all' | 'available' | 'wanted'>('all');

  // DetailModal state (tmdb_id + mediaType)
  const [modalItem, setModalItem] = useState<{ tmdb_id: number; title: string } | null>(null);

  const items = useMemo(() => data?.items || [], [data]);

  const filtered = useMemo(() => {
    let list = items;
    if (filter === 'available') list = list.filter((m: any) => m.status === 'success');
    else if (filter === 'wanted') list = list.filter((m: any) => m.status !== 'success');
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((m: any) => (m.title || '').toLowerCase().includes(q));
    }
    return list;
  }, [items, filter, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = useMemo(
    () => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filtered, page],
  );

  // Reset to page 1 when search/filter changes
  const handleSearch = (v: string) => { setSearch(v); setPage(1); };
  const handleFilter = (v: typeof filter) => { setFilter(v); setPage(1); };

  const handlePosterClick = useCallback(async (m: any) => {
    if (canPlay && playMovie === null && false) return; // unused branch, kept for clarity
    if (clickJellyfin && jellyfinUrl && m.imdb_id) {
      // Look up Jellyfin item ID, then open in a new tab
      try {
        const res = await api.jellyfinItem(m.imdb_id);
        if (res.jellyfin_id) {
          const base = (res.jellyfin_url || jellyfinUrl).replace(/\/$/, '');
          window.open(`${base}/web/index.html#!/details?id=${res.jellyfin_id}`, '_blank');
          return;
        }
      } catch { /* fall through to modal */ }
    }
    // Default: open detail modal if tmdb_id is available
    if (m.tmdb_id) {
      setModalItem({ tmdb_id: m.tmdb_id, title: m.title });
    }
  }, [clickJellyfin, jellyfinUrl, canPlay, playMovie]);

  if (isLoading) return <div className="text-muted">Loading...</div>;

  const available = items.filter((m: any) => m.status === 'success').length;
  const wanted    = items.length - available;

  return (
    <>
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          type="search"
          placeholder="Search movies..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="flex-1 bg-card border border-border rounded-lg px-3 py-2 text-sm
                     placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <div className="flex gap-1">
          {([
            ['all',       `All (${items.length})`],
            ['available', `Available (${available})`],
            ['wanted',    `Wanted (${wanted})`],
          ] as const).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => handleFilter(v)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                filter === v
                  ? 'border-accent bg-accent/10 text-white'
                  : 'border-border text-muted hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Poster grid */}
      {paginated.length === 0 ? (
        <p className="text-muted text-sm py-8 text-center">No movies found.</p>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
          {paginated.map((m: any) => (
            <MovieCard
              key={m.imdb_id}
              movie={m}
              isWatched={watched.has(m.imdb_id)}
              canPlay={canPlay}
              onPlay={() => setPlayMovie({ imdb_id: m.imdb_id, title: m.title })}
              onClick={() => handlePosterClick(m)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            type="button"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-border text-sm text-muted
                       hover:text-white disabled:opacity-30 transition"
          >
            Prev
          </button>
          <span className="text-sm text-muted">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded border border-border text-sm text-muted
                       hover:text-white disabled:opacity-30 transition"
          >
            Next
          </button>
        </div>
      )}

      {/* Webplayer */}
      {playMovie && MoviePlayer && (
        <MoviePlayer
          imdb_id={playMovie.imdb_id}
          media_type="movie"
          title={playMovie.title}
          onClose={() => setPlayMovie(null)}
        />
      )}

      {/* Detail modal */}
      {modalItem && (
        <DetailModal
          tmdbId={modalItem.tmdb_id}
          mediaType="movie"
          onClose={() => setModalItem(null)}
          onSelectItem={(item: TmdbItem) => {
            if (item.tmdb_id) setModalItem({ tmdb_id: item.tmdb_id, title: item.title });
          }}
        />
      )}
    </>
  );
}

function MovieCard({
  movie,
  isWatched,
  canPlay,
  onPlay,
  onClick,
}: {
  movie: any;
  isWatched: boolean;
  canPlay: boolean;
  onPlay: () => void;
  onClick: () => void;
}) {
  const poster = tmdbImg.poster(movie.poster_path);
  const isAvailable = movie.status === 'success';
  const isWanted    = !isAvailable;

  return (
    <div className="group relative flex flex-col">
      <button
        type="button"
        onClick={onClick}
        className="relative aspect-[2/3] rounded-lg overflow-hidden bg-card border border-border
                   hover:border-accent/60 transition focus:outline-none focus:border-accent"
        title={movie.title}
      >
        {poster ? (
          <img
            src={poster}
            alt={movie.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center p-2">
            <span className="text-[10px] text-muted text-center leading-tight line-clamp-4">
              {movie.title}
            </span>
          </div>
        )}

        {/* Status badge */}
        {isWanted && (
          <div className="absolute top-1 left-1">
            <span className="text-[9px] px-1 py-0.5 rounded bg-yellow-500/90 text-black font-semibold">
              Wanted
            </span>
          </div>
        )}
        {isWatched && (
          <div className="absolute top-1 right-1">
            <span className="text-[9px] px-1 py-0.5 rounded bg-green-600/90 text-white font-semibold">
              ✓
            </span>
          </div>
        )}

        {/* Quality badge */}
        {movie.quality && (
          <div className="absolute bottom-1 left-1">
            <span className="text-[9px] px-1 py-0.5 rounded bg-black/70 text-white font-mono">
              {movie.quality}
            </span>
          </div>
        )}

        {/* Play overlay */}
        {canPlay && isAvailable && (
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100
                          transition-opacity flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onPlay(); }}
              className="text-xs px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-500
                         text-white font-semibold transition-colors"
              title="Play in browser"
            >
              ▶ Play
            </button>
          </div>
        )}
      </button>

      {/* Title below card */}
      <p className="mt-1 text-[11px] text-muted leading-tight line-clamp-2 text-center px-0.5">
        {movie.title}
        {movie.year ? <span className="text-[10px]"> ({movie.year})</span> : null}
      </p>
    </div>
  );
}

function SeriesPanel() {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const { data, isLoading } = useQuery({
    queryKey: ['library-series-episodes'],
    queryFn: () => fetch('/ui/api/library/series-episodes').then(r => r.json()),
  });
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });
  const canPlay = !!(session?.user as any)?.webplayer_enabled;
  const traktConnected = !!(session?.user as any)?.trakt_connected;
  const PlayerModal = usePluginSlot('episode-player');
  const [playEp, setPlayEp] = useState<{
    imdb_id: string; season: number; episode: number; title: string
  } | null>(null);

  // Per-episode watched data: only fetch when trakt is connected
  const { data: watchedEpsData } = useQuery({
    queryKey: ['trakt-watched-episodes'],
    queryFn: api.traktWatchedEpisodes,
    enabled: traktConnected,
    staleTime: 5 * 60 * 1000,
  });
  // watchedEps: { imdb_id: { "1": [1,2,3], "2": [1] } }
  const watchedEps = useMemo(
    () => watchedEpsData?.shows ?? {},
    [watchedEpsData],
  );

  if (isLoading) return <div className="text-muted">Loading...</div>;
  const series: any[] = data?.series || [];

  const toggle = (title: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(title) ? next.delete(title) : next.add(title);
      return next;
    });
  };

  return (
    <>
    <div>
      <p className="text-muted text-sm mb-4">{series.length} series in library</p>
      <div className="space-y-1">
        {series.map((s: any) => {
          const isOpen = expanded.has(s.title);
          const totalEps = s.seasons.reduce((n: number, se: any) => n + se.episodes.length, 0);
          const missingList: {season: number; episode: number}[] = s.missing || [];
          const missingCount = missingList.length;
          const missingSet = new Set(missingList.map((m: any) => `${m.season}-${m.episode}`));
          const showWatched = watchedEps[s.imdb_id] ?? {};
          return (
            <div key={s.title} className="border border-border rounded">
              <button
                type="button"
                onClick={() => toggle(s.title)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-card transition text-left"
              >
                <span className="font-medium">{s.title}</span>
                <span className="text-muted text-xs">
                  {s.seasons.length} season{s.seasons.length !== 1 ? 's' : ''} · {totalEps} episodes
                  {missingCount > 0 && (
                    <span className="text-red-400 ml-2">{missingCount} missing</span>
                  )}
                  <span className="ml-2">{isOpen ? '▲' : '▼'}</span>
                </span>
              </button>
              {isOpen && (
                <div className="border-t border-border px-4 py-3 space-y-2 bg-card/50">
                  {s.seasons.map((se: any) => {
                    const seasonMissing = missingList
                      .filter((m: any) => m.season === se.season)
                      .map((m: any) => m.episode);
                    const allEps = new Set([...se.episodes, ...seasonMissing]);
                    const sorted = Array.from(allEps).sort((a, b) => a - b);
                    const watchedInSeason = new Set<number>(showWatched[String(se.season)] ?? []);
                    return (
                      <div key={se.season}>
                        <div className="text-xs text-muted mb-1">
                          Season {String(se.season).padStart(2, '0')}{se.year ? ` (${se.year})` : ''} - {se.episodes.length} episode{se.episodes.length !== 1 ? 's' : ''}
                          {seasonMissing.length > 0 && (
                            <span className="text-red-400 ml-1">({seasonMissing.length} missing)</span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {sorted.map((ep: number) => {
                            const isWanted  = missingSet.has(`${se.season}-${ep}`);
                            const isWatched = watchedInSeason.has(ep);
                            const playable  = !isWanted && canPlay && s.imdb_id;
                            const label = `E${String(ep).padStart(2, '0')}`;

                            if (isWanted) {
                              return (
                                <span key={ep}
                                  className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400"
                                  title="Wanted - not yet cached"
                                >
                                  {label}
                                </span>
                              );
                            }
                            if (playable) {
                              return (
                                <button
                                  key={ep}
                                  type="button"
                                  onClick={() => setPlayEp({
                                    imdb_id: s.imdb_id,
                                    season: se.season,
                                    episode: ep,
                                    title: `${s.title} S${String(se.season).padStart(2,'0')}E${String(ep).padStart(2,'0')}`,
                                  })}
                                  className={`text-xs px-2 py-0.5 rounded transition-colors
                                    ${isWatched
                                      ? 'bg-green-500/20 text-green-400 hover:bg-green-600 hover:text-white'
                                      : 'bg-accent/20 text-accent hover:bg-indigo-600 hover:text-white'
                                    }`}
                                  title={isWatched ? 'Watched - play again' : 'Play in browser'}
                                >
                                  ▶ {label}
                                </button>
                              );
                            }
                            // available but no webplayer
                            return (
                              <span key={ep}
                                className={`text-xs px-2 py-0.5 rounded
                                  ${isWatched ? 'bg-green-500/20 text-green-400' : 'bg-accent/20 text-accent'}`}
                                title={isWatched ? 'Watched' : 'Available'}
                              >
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>

    {playEp && PlayerModal && (
      <PlayerModal
        imdb_id={playEp.imdb_id}
        media_type="tv"
        title={playEp.title}
        season={playEp.season}
        episode={playEp.episode}
        onClose={() => setPlayEp(null)}
      />
    )}
    </>
  );
}
