import { useState } from 'react';
import AutoApprove from './AutoApprove';
import Blacklist from './Blacklist';
import Subtitles from './Subtitles';
import Logs from './Logs';

const TABS = [
  { id: 'overview', label: 'Overview & Maintenance', icon: '⚙️' },
  { id: 'auto-approve', label: 'Auto-Approve', icon: '🤖' },
  { id: 'blacklist', label: 'Blacklist', icon: '🚫' },
  { id: 'subtitles', label: 'Subtitles', icon: '💬' },
  { id: 'logs', label: 'Logs', icon: '📜' },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function Admin() {
  const [tab, setTab] = useState<TabId>('overview');

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap border-b border-border pb-3">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-4 py-1.5 rounded-lg text-sm border transition flex items-center gap-1.5 ${
              tab === t.id
                ? 'border-accent bg-accent/10 text-white'
                : 'border-border text-muted hover:text-white'
            }`}
          >
            <span aria-hidden="true">{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Overview/Maintenance/Users/Settings/Releases still live in the
          server-rendered dashboard - it's a lot of working functionality
          that doesn't need a React rewrite just to sit under this tab bar. */}
      {tab === 'overview' && (
        <iframe
          src="/admin?embed=1"
          className="w-full border-0"
          style={{ height: 'calc(100vh - 160px)' }}
          title="Overview & Maintenance"
        />
      )}
      {tab === 'auto-approve' && <AutoApprove />}
      {tab === 'blacklist' && <Blacklist />}
      {tab === 'subtitles' && <Subtitles />}
      {tab === 'logs' && <Logs />}
    </div>
  );
}
