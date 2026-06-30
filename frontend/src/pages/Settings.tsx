import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '../api';
import { usePlugins } from '../hooks/usePlugins';
import PluginSettingsCard from '../components/PluginSettingsCard';
import type { NotificationSettings } from '../types';

export default function Settings() {
  const { plugins } = usePlugins();
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });

  const visiblePlugins = plugins.filter(p => {
    const anyFieldEnabled = (p.user_fields || []).some(f => !!(session?.user as any)?.[f]);
    return anyFieldEnabled || !!p.settings_ui;
  });

  const isAdmin = (session?.user as any)?.role === 'admin';

  return (
    <div className="space-y-6">
      <ChangePasswordCard />
      <PreferencesCard />
      {isAdmin && <NotificationsCard />}

      {visiblePlugins.length > 0 && (
        <>
          <div>
            <h1 className="text-xl font-bold mb-1">Plugins</h1>
            <p className="text-muted text-sm">Enable features and connect accounts for your profile.</p>
          </div>
          {visiblePlugins.map(plugin => (
            <PluginCard key={plugin.name} plugin={plugin} session={session} />
          ))}
        </>
      )}
    </div>
  );
}

function PluginCard({ plugin, session }: {
  plugin: ReturnType<typeof usePlugins>['plugins'][number];
  session: any;
}) {
  const hasFields = plugin.user_fields?.length > 0;
  const hasUi = !!plugin.settings_ui;

  // User-field toggles: only show if the admin has already enabled at least one
  // field for this user. This keeps toggles admin-controlled  -  users can turn
  // off what they have access to, but cannot self-grant new access.
  const anyFieldEnabled = hasFields &&
    plugin.user_fields.some(f => !!(session?.user as any)?.[f]);

  if (!anyFieldEnabled && !hasUi) return null;

  return (
    <div className="bg-card rounded-lg border border-border p-6 space-y-4">
      <div>
        <h2 className="text-base font-bold leading-tight">{plugin.label}</h2>
        {plugin.description && (
          <p className="text-muted text-xs mt-0.5">{plugin.description}</p>
        )}
      </div>

      {anyFieldEnabled && <PluginUserFieldsSection plugin={plugin} />}
      {hasUi && <PluginSettingsCard plugin={plugin} embedded />}
    </div>
  );
}

function PluginUserFieldsSection({ plugin }: { plugin: ReturnType<typeof usePlugins>['plugins'][number] }) {
  const qc = useQueryClient();
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });
  const mutation = useMutation({
    mutationFn: (fields: Record<string, boolean>) => api.setPluginFields(fields),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session'] }),
  });

  return (
    <div className="flex flex-wrap gap-4">
      {plugin.user_fields.map(field => {
        const label = plugin.user_field_labels?.[field] || field;
        const value = !!(session?.user as any)?.[field];
        return (
          <label key={field} className="flex items-center gap-2 cursor-pointer select-none">
            <span className="text-sm text-muted">{label}</span>
            <button
              type="button"
              role="switch"
              aria-checked={value}
              onClick={() => mutation.mutate({ [field]: !value })}
              disabled={mutation.isPending}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${value ? 'bg-accent' : 'bg-zinc-600'}
                ${mutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform
                ${value ? 'translate-x-4' : 'translate-x-1'}`} />
            </button>
            <span className={`text-xs font-medium ${value ? 'text-accent' : 'text-muted'}`}>
              {value ? 'On' : 'Off'}
            </span>
          </label>
        );
      })}
    </div>
  );
}

function PreferencesCard() {
  const qc = useQueryClient();
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session });
  const clickJellyfin = !!(session?.user as any)?.library_click_jellyfin;
  const jellyfinUrl = session?.jellyfin_url;

  const mutation = useMutation({
    mutationFn: (prefs: Record<string, boolean>) => api.setPreferences(prefs),
    onError: () => {
      // Revert optimistic update on failure
      qc.invalidateQueries({ queryKey: ['session'] });
    },
  });

  const toggle = () => {
    const newVal = !clickJellyfin;
    // Optimistic update: immediately flip in the shared session cache so
    // Library.tsx (which reads the same cache) picks it up without a reload.
    qc.setQueryData(['session'], (old: any) =>
      old ? { ...old, user: { ...old.user, library_click_jellyfin: newVal } } : old,
    );
    mutation.mutate({ library_click_jellyfin: newVal });
  };

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h2 className="text-base font-bold mb-1">Preferences</h2>
      <p className="text-muted text-xs mb-4">Personalise how the app behaves for your account.</p>
      <div className="space-y-3">
        <label className="flex items-start gap-3 cursor-pointer select-none" onClick={toggle}>
          <div className="mt-0.5 flex-shrink-0">
            <div className={`w-10 h-5 rounded-full transition-colors flex items-center px-0.5
                ${clickJellyfin ? 'bg-accent' : 'bg-border'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white shadow transition-transform
                ${clickJellyfin ? 'translate-x-5' : 'translate-x-0'}`} />
            </div>
          </div>
          <div>
            <div className="text-sm font-medium">Open library items in Jellyfin</div>
            <div className="text-xs text-muted mt-0.5">
              Clicking a poster in the Library tab opens the item in Jellyfin web instead of showing the detail modal.
              {!jellyfinUrl && (
                <span className="text-yellow-400 ml-1">(Jellyfin URL not configured)</span>
              )}
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}


function NotificationsCard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['notification-settings'],
    queryFn: api.notificationSettingsGet,
  });
  const [form, setForm] = useState<NotificationSettings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.notificationSettingsSet(form as NotificationSettings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-settings'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (isLoading || !form) {
    return (
      <div className="bg-card rounded-lg border border-border p-6">
        <h2 className="text-base font-bold mb-1">Notifications</h2>
        <p className="text-muted text-xs">Loading…</p>
      </div>
    );
  }

  const field = (key: keyof NotificationSettings, label: string, placeholder: string) => (
    <div>
      <label className="block text-xs text-muted mb-1">{label}</label>
      <input
        type="url"
        value={(form[key] as string) || ''}
        placeholder={placeholder}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
      />
    </div>
  );

  const toggle = (key: 'notify_on_success' | 'notify_on_failure', label: string) => (
    <label className="flex items-center gap-3 cursor-pointer select-none"
      onClick={() => setForm({ ...form, [key]: !form[key] })}>
      <div className={`w-10 h-5 rounded-full transition-colors flex items-center px-0.5
          ${form[key] ? 'bg-accent' : 'bg-border'}`}>
        <div className={`w-4 h-4 rounded-full bg-white shadow transition-transform
          ${form[key] ? 'translate-x-5' : 'translate-x-0'}`} />
      </div>
      <span className="text-sm">{label}</span>
    </label>
  );

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h2 className="text-base font-bold mb-1">Notifications</h2>
      <p className="text-muted text-xs mb-4">
        Discord webhooks for new media. Movie and show webhooks fall back to the default when left empty.
      </p>
      <div className="space-y-3 max-w-xl">
        {field('discord_webhook_url', 'Default Discord webhook', 'https://discord.com/api/webhooks/…')}
        {field('discord_webhook_url_movies', 'Movies Discord webhook', 'Optional, falls back to default')}
        {field('discord_webhook_url_shows', 'Shows Discord webhook', 'Optional, falls back to default')}
        <div className="flex flex-wrap gap-6 pt-1">
          {toggle('notify_on_success', 'Notify on success')}
          {toggle('notify_on_failure', 'Notify on failure')}
        </div>
        <div className="flex items-center gap-3 pt-1">
          <button type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-60 font-semibold text-sm">
            {mutation.isPending ? 'Saving…' : 'Save'}
          </button>
          {saved && <span className="text-ok text-sm">Saved.</span>}
        </div>
      </div>
    </div>
  );
}


function ChangePasswordCard() {
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: () => api.changePassword(current, password),
    onSuccess: () => {
      setSuccess(true);
      setCurrent(''); setPassword(''); setConfirm('');
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: (e: any) => setError(e.message || 'Failed to change password'),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) { setError('At least 6 characters required'); return; }
    if (password !== confirm) { setError('Passwords do not match'); return; }
    mutation.mutate();
  };

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h2 className="text-base font-bold mb-4">Change password</h2>
      {success && <p className="text-ok text-sm mb-3">Password changed successfully.</p>}
      <form onSubmit={submit} className="space-y-3 max-w-sm">
        <div>
          <label className="block text-xs text-muted mb-1">Current password</label>
          <input type="password" value={current} onChange={e => setCurrent(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent" />
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">New password</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent" />
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">Confirm new password</label>
          <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent" />
        </div>
        {error && <p className="text-danger text-xs">{error}</p>}
        <button type="submit" disabled={mutation.isPending}
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-60 font-semibold text-sm">
          {mutation.isPending ? 'Saving...' : 'Change password'}
        </button>
      </form>
    </div>
  );
}
