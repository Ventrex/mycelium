import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { LogEntry, LogType } from '../types';

const TABS: { id: LogType; label: string }[] = [
  { id: 'server', label: 'Server' },
  { id: 'auto_approve', label: 'Auto-Approve' },
  { id: 'subtitles', label: 'Subtitles' },
];

const LEVELS = ['ERROR', 'WARNING', 'INFO', 'DEBUG'] as const;
type LevelFilter = 'ALL' | (typeof LEVELS)[number];

function levelClass(level: string): string {
  switch (level) {
    case 'ERROR':
    case 'CRITICAL':
      return 'text-red-400';
    case 'WARNING':
      return 'text-amber-400';
    case 'DEBUG':
      return 'text-muted';
    default:
      return 'text-cyan-300';
  }
}

function normalizedLevel(level: string): string {
  return level === 'CRITICAL' ? 'ERROR' : level;
}

export default function Logs() {
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });
  const [type, setType] = useState<LogType>('server');
  const [level, setLevel] = useState<LevelFilter>('ALL');

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['logs', type],
    queryFn: () => api.logs(type).then((r) => r.logs),
    enabled: (session?.user as any)?.role === 'admin',
    refetchInterval: 5000,
  });

  if (session && (session.user as any)?.role !== 'admin') {
    return <div className="text-center py-16 text-muted">Logs are only available to admins.</div>;
  }

  const logs: LogEntry[] = data || [];

  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: logs.length, ERROR: 0, WARNING: 0, INFO: 0, DEBUG: 0 };
    for (const l of logs) {
      const norm = normalizedLevel(l.level);
      if (norm in c) c[norm] += 1;
    }
    return c;
  }, [logs]);

  const filtered = level === 'ALL' ? logs : logs.filter((l) => normalizedLevel(l.level) === level);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold">Logs</h1>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="px-3 py-1.5 rounded-lg border border-border text-sm hover:border-accent/50 hover:bg-card transition disabled:opacity-60"
        >
          {isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => { setType(t.id); setLevel('ALL'); }}
            className={`px-4 py-1.5 rounded-lg text-sm border transition ${
              type === t.id
                ? 'border-accent bg-accent/10 text-white'
                : 'border-border text-muted hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {(['ALL', ...LEVELS] as LevelFilter[]).map((lv) => (
          <button
            key={lv}
            type="button"
            onClick={() => setLevel(lv)}
            className={`px-3 py-1 rounded text-xs border transition flex items-center gap-1.5 ${
              level === lv
                ? 'border-accent bg-accent/10 text-white'
                : 'border-border text-muted hover:text-white'
            }`}
          >
            <span className={lv === 'ALL' ? '' : levelClass(lv)}>{lv}</span>
            <span className="text-[10px] opacity-70">{counts[lv] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="bg-[#090d14] border border-border rounded-lg p-3 font-mono text-xs leading-relaxed max-h-[70vh] overflow-y-auto">
        {isLoading ? (
          <div className="text-muted">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="text-muted">No log lines match this filter.</div>
        ) : (
          filtered.map((l, i) => (
            <div key={i} className="whitespace-pre-wrap break-words py-0.5">
              <span className="text-muted">{l.time}</span>{' '}
              <span className={levelClass(l.level)}>{l.level}</span>{' '}
              <span className="text-muted">[{l.name}]</span>{' '}
              <span className="text-white">{l.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
