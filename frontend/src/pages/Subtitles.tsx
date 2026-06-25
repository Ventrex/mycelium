import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { SubtitleItem } from '../types';

type Tab = 'movies' | 'series';
type Filter = 'all' | 'missing';

export default function Subtitles() {
  const [tab, setTab] = useState<Tab>('movies');
  const [filter, setFilter] = useState<Filter>('all');
  const [langFilter, setLangFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['subtitles'],
    queryFn: api.subtitles,
  });

  const queryClient = useQueryClient();
  const searchAll = useMutation({
    mutationFn: api.subtitlesSearchAll,
    onSuccess: () => setMsg('Started in background — check the Admin logs for progress. Refresh in a minute to see results.'),
  });

  const items = data?.items || [];
  const wantedLanguages = data?.wanted_languages || [];

  const missingFor = (item: SubtitleItem) =>
    wantedLanguages.filter((l) => !item.languages.includes(l));

  const filtered = useMemo(() => {
    let list = items.filter((i) => i.media_type === (tab === 'movies' ? 'movie' : 'series'));
    if (filter === 'missing') list = list.filter((i) => missingFor(i).length > 0);
    if (langFilter !== 'all') {
      list = list.filter((i) => !i.languages.includes(langFilter));
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((i) => i.title.toLowerCase().includes(q));
    }
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, tab, filter, langFilter, search, wantedLanguages]);

  const movieCount = items.filter((i) => i.media_type === 'movie').length;
  const seriesCount = items.filter((i) => i.media_type === 'series').length;

  if (isLoading) return <div className="text-muted">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-2 border-b border-border">
          {([['movies', `Movies (${movieCount})`], ['series', `Series (${seriesCount})`]] as const).map(
            ([t, label]) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
                  tab === t ? 'border-accent text-white' : 'border-transparent text-muted hover:text-white'
                }`}
              >
                {label}
              </button>
            )
          )}
        </div>
        <button
          type="button"
          onClick={() => {
            if (confirm('Search subtitles for every item still missing a configured language? This runs in the background and may take a while for a large library.')) {
              searchAll.mutate();
            }
          }}
          disabled={searchAll.isPending}
          className="px-3 py-1.5 rounded-lg bg-accent text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
        >
          🔍 Search all missing
        </button>
      </div>

      {msg && (
        <div className="mb-4 px-3 py-2 rounded-lg bg-accent/10 border border-accent/30 text-sm text-white flex items-center justify-between">
          <span>{msg}</span>
          <button
            type="button"
            onClick={() => { setMsg(null); queryClient.invalidateQueries({ queryKey: ['subtitles'] }); }}
            className="text-muted hover:text-white ml-3"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          type="search"
          placeholder={`Search ${tab}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-card border border-border rounded-lg px-3 py-2 text-sm
                     placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <div className="flex gap-1">
          {([
            ['all', 'All'],
            ['missing', 'Missing any language'],
          ] as const).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => setFilter(v)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                filter === v ? 'border-accent bg-accent/10 text-white' : 'border-border text-muted hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {wantedLanguages.length > 0 && (
          <select
            value={langFilter}
            onChange={(e) => setLangFilter(e.target.value)}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
          >
            <option value="all">All languages</option>
            {wantedLanguages.map((l) => (
              <option key={l} value={l}>Missing {l.toUpperCase()}</option>
            ))}
          </select>
        )}
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted text-sm py-8 text-center">No items found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-card text-muted text-left">
                <th className="px-3 py-2 font-medium">Title</th>
                {tab === 'series' && <th className="px-3 py-2 font-medium">Episode</th>}
                <th className="px-3 py-2 font-medium">Subtitles</th>
                <th className="px-3 py-2 font-medium w-24">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <SubtitleRow key={item.strm} item={item} wantedLanguages={wantedLanguages} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SubtitleRow({ item, wantedLanguages }: { item: SubtitleItem; wantedLanguages: string[] }) {
  const queryClient = useQueryClient();
  const search = useMutation({
    mutationFn: () => api.subtitlesSearch(item.strm),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subtitles'] }),
  });

  const missing = wantedLanguages.filter((l) => !item.languages.includes(l));

  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2">
        {item.title}
        {item.year ? <span className="text-muted"> ({item.year})</span> : null}
      </td>
      {item.episode != null && (
        <td className="px-3 py-2 text-muted">
          S{String(item.season).padStart(2, '0')}E{String(item.episode).padStart(2, '0')}
        </td>
      )}
      <td className="px-3 py-2">
        <div className="flex gap-1 flex-wrap">
          {item.languages.map((l) => (
            <span key={l} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-ok/20 text-ok uppercase">
              {l}
            </span>
          ))}
          {missing.map((l) => (
            <span key={l} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-border text-muted uppercase">
              {l}
            </span>
          ))}
          {item.languages.length === 0 && missing.length === 0 && (
            <span className="text-muted text-xs">—</span>
          )}
        </div>
      </td>
      <td className="px-3 py-2">
        <button
          type="button"
          onClick={() => search.mutate()}
          disabled={search.isPending}
          className="px-2 py-1 rounded border border-border text-xs text-muted hover:text-white hover:border-accent/50 transition disabled:opacity-50"
        >
          {search.isPending ? '…' : search.isSuccess ? '✓' : '🔍 Search'}
        </button>
      </td>
    </tr>
  );
}
