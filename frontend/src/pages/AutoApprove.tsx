import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { AutoApproveRule, AutoApproveRules, Genre, MediaType } from '../types';

const EMPTY_RULE: AutoApproveRule = {
  enabled: false,
  year_from: null,
  year_to: null,
  auto_request_trending: false,
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
    </div>
  );
}

function RunNowButton() {
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const mutation = useMutation({
    mutationFn: api.autoApproveRunNow,
    onMutate: () => setStatus('running'),
    onSuccess: () => setStatus('done'),
    onError: () => setStatus('idle'),
  });
  return (
    <button
      type="button"
      onClick={() => mutation.mutate()}
      disabled={status === 'running'}
      className="px-3 py-1.5 rounded-lg border border-border hover:border-accent/50 text-sm disabled:opacity-60"
    >
      {status === 'running' ? 'Running...' : status === 'done' ? 'Started ✓' : '▶ Run now'}
    </button>
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
