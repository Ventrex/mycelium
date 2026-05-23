import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { usePlugins } from '../hooks/usePlugins';

export default function Settings() {
  const { isLoaded } = usePlugins();
  return (
    <div className="space-y-6">
      <div className="bg-card rounded-lg border border-border p-6">
        <h2 className="text-lg font-bold mb-2">Settings</h2>
        <p className="text-muted text-sm mb-4">
          Runtime settings are managed in the admin panel.
        </p>
        <a
          href="/admin#settings"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-sm font-semibold"
        >
          Open Settings
        </a>
      </div>
      {isLoaded('trakt') && <TraktCard />}
    </div>
  );
}

function TraktCard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['trakt-status'],
    queryFn: api.traktStatus,
  });

  const revokeMut = useMutation({
    mutationFn: api.traktRevoke,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trakt-status', 'session'] }),
  });

  const syncMut = useMutation({ mutationFn: api.traktSync });

  const [connecting, setConnecting] = useState(false);
  const [deviceInfo, setDeviceInfo] = useState<{
    user_code: string; verification_url: string; interval: number;
  } | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const startConnect = async () => {
    setConnectError(null);
    try {
      const info = await api.traktAuthStart();
      setDeviceInfo({ user_code: info.user_code, verification_url: info.verification_url, interval: info.interval });
      setConnecting(true);
    } catch (e: any) {
      setConnectError(e.message);
    }
  };

  useEffect(() => {
    if (!connecting || !deviceInfo) return;
    const interval = Math.max(deviceInfo.interval * 1000, 5000);
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.traktAuthPoll();
        if (r.status === 'connected') {
          clearInterval(pollRef.current);
          setConnecting(false);
          setDeviceInfo(null);
          qc.invalidateQueries({ queryKey: ['trakt-status', 'session'] });
        } else if (r.status === 'error' || r.status === 'expired') {
          clearInterval(pollRef.current);
          setConnecting(false);
          setDeviceInfo(null);
          setConnectError(r.error || `Auth ${r.status}`);
        }
      } catch {
        // network hiccup — keep polling
      }
    }, interval);
    return () => clearInterval(pollRef.current);
  }, [connecting, deviceInfo]);

  if (isLoading) return null;

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">🎬</span>
        <div>
          <h2 className="text-base font-bold leading-tight">Trakt</h2>
          <p className="text-muted text-xs">Watchlist sync &amp; watch history</p>
        </div>
      </div>

      {!data?.configured && (
        <div className="text-xs text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 rounded px-3 py-2 mb-4">
          TRAKT_CLIENT_ID not configured. Create a Trakt app at{' '}
          <a href="https://trakt.tv/oauth/applications" target="_blank" rel="noopener"
             className="underline">trakt.tv/oauth/applications</a>{' '}
          and add the client ID + secret in Admin → Connections settings.
        </div>
      )}

      {data?.connected ? (
        <div className="space-y-3">
          <p className="text-sm">
            Connected as <span className="font-semibold text-white">{data.username}</span>
          </p>
          {data.synced_at && (
            <p className="text-xs text-muted">Last synced: {data.synced_at}</p>
          )}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => syncMut.mutate()}
              disabled={syncMut.isPending}
              className="px-3 py-1.5 rounded bg-accent/20 text-accent text-xs font-medium hover:bg-accent/30 disabled:opacity-50"
            >
              {syncMut.isPending ? 'Syncing…' : '↻ Sync watchlist now'}
            </button>
            {syncMut.isSuccess && (
              <span className="text-xs text-ok self-center">
                ✓ {(syncMut.data as any).added} items added
              </span>
            )}
            <button
              onClick={() => revokeMut.mutate()}
              disabled={revokeMut.isPending}
              className="px-3 py-1.5 rounded bg-red-500/20 text-red-400 text-xs font-medium hover:bg-red-500/30 disabled:opacity-50"
            >
              Disconnect
            </button>
          </div>
        </div>
      ) : connecting && deviceInfo ? (
        <div className="space-y-3">
          <p className="text-sm text-muted">
            Go to{' '}
            <a href={deviceInfo.verification_url} target="_blank" rel="noopener"
               className="text-accent underline font-medium">
              {deviceInfo.verification_url}
            </a>{' '}
            and enter:
          </p>
          <div className="font-mono text-2xl font-bold tracking-widest text-white bg-zinc-800 px-4 py-3 rounded-lg inline-block">
            {deviceInfo.user_code}
          </div>
          <p className="text-xs text-muted animate-pulse">Waiting for confirmation…</p>
          <button
            onClick={() => { clearInterval(pollRef.current); setConnecting(false); setDeviceInfo(null); }}
            className="text-xs text-muted hover:text-white"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {connectError && (
            <p className="text-xs text-red-400">{connectError}</p>
          )}
          <button
            onClick={startConnect}
            disabled={!data?.configured}
            className="px-4 py-2 rounded bg-accent text-sm font-semibold hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Connect Trakt account
          </button>
        </div>
      )}
    </div>
  );
}
