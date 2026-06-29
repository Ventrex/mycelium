import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, tmdbImg } from '../api';
import type { AutoApproveRule, AutoApproveRules, AutoApproveSettings, FavoriteActor, Genre, MediaType, TmdbItem } from '../types';
import PersonModal from '../components/PersonModal';
import DetailModal from '../components/DetailModal';

const EMPTY_RULE: AutoApproveRule = {
  enabled: false,
  year_from: null,
  year_to: null,
  auto_request_trending: false,
  min_votes: null,
};

export default function AutoApprove() {
  const [mediaType, setMediaType] = useState<MediaType>('movie');

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Auto-Approve</h1>
        <RunNowButton />
      </div>
      <p className="text-sm text-muted">
        Turn on auto-approve for a genre/year range to skip the request queue for matching
        items. Turn on &quot;auto-fill trending&quot; to let Mycelium request popular titles in
        that genre on its own, Netflix-style.
      </p>
      <AutoApproveSettingsCard />
      <div className="flex gap-2">
        {(['movie', 'tv'] as const).map((mt) => (
          <button
            key={mt}
            type="button"
            onClick={() => setMediaType(mt)}
            className={`px-4 py-1.5 rounded-lg text-sm border ${
              mediaType === mt
                ? 'border-accent bg-accent/10 text-white'
                : 'border-border text-muted hover:text-white'
            }`}
          >
            {mt === 'movie' ? 'Movies' : 'Shows'}
          </button>
        ))}
      </div>
      <RuleTable mediaType={mediaType} />
      <FavoriteActorsPanel />
    </div>
  );
}


function AutoApproveSettingsCard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['auto-approve-settings'],
    queryFn: api.autoApproveSettingsGet,
  });
  const [form, setForm] = useState({
    schedule_mode: 'daily_time' as AutoApproveSettings['schedule']['mode'],
    interval_hours: 12,
    daily_time: '04:00',
    movie_per_genre_limit: 50,
    tv_per_genre_limit: 50,
    max_pages: 10,
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!data) return;
    setForm({
      schedule_mode: data.schedule.mode,
      interval_hours: data.schedule.interval_hours,
      daily_time: data.schedule.daily_time,
      movie_per_genre_limit: data.movie_per_genre_limit,
      tv_per_genre_limit: data.tv_per_genre_limit,
      max_pages: data.max_pages,
    });
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.autoApproveSettingsSet(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auto-approve-settings'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const setNumber = (key: 'interval_hours' | 'movie_per_genre_limit' | 'tv_per_genre_limit' | 'max_pages', value: string) => {
    setForm((prev) => ({ ...prev, [key]: Math.max(1, Number(value) || 1) }));
  };

  if (isLoading) {
    return <div className="border border-border rounded-lg p-4 text-sm text-muted">Loading schedule...</div>;
  }

  return (
    <section className="border border-border rounded-lg p-4 bg-card/40 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold">Schedule & limits</h2>
          <p className="text-sm text-muted">Current schedule: {data?.description || 'Unknown'}</p>
        </div>
        {saved && <span className="text-xs text-green-400">Saved ✓</span>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Schedule mode</span>
          <select
            value={form.schedule_mode}
            onChange={(e) => setForm((prev) => ({ ...prev, schedule_mode: e.target.value as AutoApproveSettings['schedule']['mode'] }))}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          >
            <option value="disabled">Disabled</option>
            <option value="hourly">Every hour</option>
            <option value="every_x_hours">Every X hours</option>
            <option value="daily_time">Daily at HH:MM</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Interval hours</span>
          <input
            type="number"
            min={1}
            value={form.interval_hours}
            onChange={(e) => setNumber('interval_hours', e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Daily time</span>
          <input
            type="time"
            value={form.daily_time}
            onChange={(e) => setForm((prev) => ({ ...prev, daily_time: e.target.value || '04:00' }))}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          />
        </label>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Movie per-genre limit</span>
          <input
            type="number"
            min={1}
            value={form.movie_per_genre_limit}
            onChange={(e) => setNumber('movie_per_genre_limit', e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Show per-genre limit</span>
          <input
            type="number"
            min={1}
            value={form.tv_per_genre_limit}
            onChange={(e) => setNumber('tv_per_genre_limit', e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Max TMDB pages</span>
          <input
            type="number"
            min={1}
            value={form.max_pages}
            onChange={(e) => setNumber('max_pages', e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-2"
          />
        </label>
      </div>

      {mutation.isError && <div className="text-xs text-red-400">{(mutation.error as Error).message}</div>}
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-60 font-semibold text-sm"
      >
        {mutation.isPending ? 'Saving...' : 'Save schedule & limits'}
      </button>
    </section>
  );
}

function FavoriteActorsPanel() {
  const qc = useQueryClient();
  const [personId, setPersonId] = useState<number | null>(null);
  const [detail, setDetail] = useState<{ id: number; type: MediaType } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ['favorite-actors'],
    queryFn: api.favoriteActors,
  });
  const removeMut = useMutation({
    mutationFn: (tmdb_id: number) => api.favoriteActorRemove(tmdb_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['favorite-actors'] }),
  });

  const actors = data?.items || [];
  const openItem = (it: TmdbItem) => setDetail({ id: it.tmdb_id, type: it.media_type });

  return (
    <section className="border-t border-border pt-6">
      <h2 className="text-lg font-bold mb-1">Favorite actors</h2>
      <p className="text-sm text-muted mb-4">
        Mycelium auto-requests recent movies/shows for actors you favorite. Click an actor to
        open their page and filmography; use Search to add new favorites.
      </p>
      {isLoading ? (
        <div className="text-muted text-sm">Loading...</div>
      ) : actors.length === 0 ? (
        <div className="text-muted text-sm">No favorite actors yet.</div>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-6 md:grid-cols-8 gap-3">
          {actors.map((a: FavoriteActor) => (
            <div key={a.tmdb_id} className="text-left">
              <button
                type="button"
                onClick={() => setPersonId(a.tmdb_id)}
                title={`Open ${a.name}`}
                className="block w-full aspect-[2/3] rounded-md overflow-hidden bg-bg border border-border
                            hover:border-accent transition-colors"
              >
                {tmdbImg.profile(a.profile_path) ? (
                  <img
                    src={tmdbImg.profile(a.profile_path)!}
                    alt={a.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-xs text-muted p-2 text-center flex items-center justify-center h-full">
                    {a.name}
                  </div>
                )}
              </button>
              <div className="text-[11px] mt-1 font-semibold leading-tight line-clamp-2">{a.name}</div>
              <button
                type="button"
                onClick={() => removeMut.mutate(a.tmdb_id)}
                disabled={removeMut.isPending}
                className="mt-1 w-full text-[10px] px-1.5 py-1 rounded border border-red-600/50 text-red-400
                            hover:bg-red-600/10 disabled:opacity-60"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      <PersonModal
        personId={personId}
        onClose={() => setPersonId(null)}
        onSelectItem={(it) => {
          setPersonId(null);
          openItem(it);
        }}
      />
      <DetailModal
        tmdbId={detail?.id ?? null}
        mediaType={detail?.type ?? null}
        onClose={() => setDetail(null)}
        onSelectItem={openItem}
      />
    </section>
  );
}

function RunNowButton() {
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [summary, setSummary] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: api.autoApproveRunNow,
    onMutate: () => {
      setStatus('running');
      setSummary(null);
    },
    onSuccess: (data) => {
      setStatus('done');
      setSummary(`${data.movies_queued} movies, ${data.series_queued} shows queued (${data.total_queued} total)`);
    },
    onError: () => setStatus('idle'),
  });
  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={status === 'running'}
        className="px-3 py-1.5 rounded-lg border border-border hover:border-accent/50 text-sm disabled:opacity-60"
      >
        {status === 'running' ? 'Running...' : status === 'done' ? 'Done ✓' : '▶ Run now'}
      </button>
      {summary && <div className="text-xs text-muted">{summary}</div>}
    </div>
  );
}

function RuleTable({ mediaType }: { mediaType: MediaType }) {
  const queryClient = useQueryClient();
  const { data: genresData, isLoading: genresLoading } = useQuery({
    queryKey: ['discover-genres-all', mediaType],
    queryFn: () => api.genres(mediaType),
  });
  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ['auto-approve-rules', mediaType],
    queryFn: () => api.autoApproveRulesGet(mediaType),
  });

  const [rules, setRules] = useState<AutoApproveRules>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setRules(rulesData?.rules || {});
  }, [rulesData]);

  const saveMutation = useMutation({
    mutationFn: () => api.autoApproveRulesSet(mediaType, rules),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-approve-rules', mediaType] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const update = (genreId: number, patch: Partial<AutoApproveRule>) => {
    setRules((prev) => ({
      ...prev,
      [String(genreId)]: { ...(prev[String(genreId)] || EMPTY_RULE), ...patch },
    }));
  };

  if (genresLoading || rulesLoading) {
    return <div className="text-muted text-sm py-6">Loading...</div>;
  }

  const genres: Genre[] = genresData?.all_genres || [];

  return (
    <div className="space-y-3">
      <div className="border border-border rounded-lg overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-bg/60 text-muted text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-3 py-2">Genre</th>
              <th className="text-center px-3 py-2">Auto-approve</th>
              <th className="text-center px-3 py-2">From</th>
              <th className="text-center px-3 py-2">To</th>
              <th className="text-center px-3 py-2">Min votes</th>
              <th className="text-center px-3 py-2">Auto-fill trending</th>
            </tr>
          </thead>
          <tbody>
            {genres.map((g) => {
              const rule = rules[String(g.id)] || EMPTY_RULE;
              return (
                <tr key={g.id} className="border-t border-border">
                  <td className="px-3 py-2 whitespace-nowrap">{g.name}</td>
                  <td className="text-center px-3 py-2">
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={(e) => update(g.id, { enabled: e.target.checked })}
                      className="accent-accent"
                    />
                  </td>
                  <td className="text-center px-3 py-2">
                    <input
                      type="number"
                      value={rule.year_from ?? ''}
                      onChange={(e) =>
                        update(g.id, { year_from: e.target.value ? Number(e.target.value) : null })
                      }
                      className="w-20 bg-bg border border-border rounded px-1.5 py-1 text-xs text-center"
                    />
                  </td>
                  <td className="text-center px-3 py-2">
                    <input
                      type="number"
                      value={rule.year_to ?? ''}
                      onChange={(e) =>
                        update(g.id, { year_to: e.target.value ? Number(e.target.value) : null })
                      }
                      className="w-20 bg-bg border border-border rounded px-1.5 py-1 text-xs text-center"
                    />
                  </td>
                  <td className="text-center px-3 py-2">
                    <input
                      type="number"
                      min={0}
                      placeholder="default"
                      value={rule.min_votes ?? ''}
                      onChange={(e) =>
                        update(g.id, { min_votes: e.target.value ? Number(e.target.value) : null })
                      }
                      className="w-20 bg-bg border border-border rounded px-1.5 py-1 text-xs text-center"
                    />
                  </td>
                  <td className="text-center px-3 py-2">
                    <input
                      type="checkbox"
                      checked={rule.auto_request_trending}
                      onChange={(e) => update(g.id, { auto_request_trending: e.target.checked })}
                      className="accent-accent"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-60 font-semibold text-sm"
        >
          {saveMutation.isPending ? 'Saving...' : 'Save changes'}
        </button>
        {saved && <span className="text-xs text-green-400">Saved ✓</span>}
      </div>
    </div>
  );
}
