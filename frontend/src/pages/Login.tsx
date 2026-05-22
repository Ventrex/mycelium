import { useState } from 'react';

export default function Login() {
  const [error, setError] = useState<string | null>(null);
  const params = new URLSearchParams(window.location.search);
  const errFromQuery = params.get('error');
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="w-full max-w-sm bg-card rounded-2xl border border-border p-8 shadow-2xl">
        <div className="flex items-center justify-center gap-3 mb-6">
          <svg width="32" height="32" viewBox="0 0 40 40" aria-hidden="true">
            <g stroke="#22d3ee" strokeWidth="1.5" opacity="0.7" fill="none">
              <line x1="10" y1="20" x2="30" y2="10"/>
              <line x1="10" y1="20" x2="30" y2="30"/>
              <line x1="30" y1="10" x2="30" y2="30"/>
              <line x1="20" y1="5"  x2="10" y2="20"/>
              <line x1="20" y1="35" x2="10" y2="20"/>
            </g>
            <circle cx="10" cy="20" r="3.5" fill="#0d9488"/>
            <circle cx="30" cy="10" r="3"   fill="#22d3ee"/>
            <circle cx="30" cy="30" r="3"   fill="#22d3ee"/>
            <circle cx="20" cy="5"  r="2.2" fill="#5eead4"/>
            <circle cx="20" cy="35" r="2.2" fill="#5eead4"/>
          </svg>
          <span className="font-mono font-bold text-2xl tracking-wide text-white">
            myc<span className="text-[#22d3ee]">3</span>l<span className="text-[#22d3ee]">1</span>um
          </span>
        </div>
        <h1 className="text-lg font-semibold text-center mb-6">Sign in</h1>
        {(error || errFromQuery) && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded p-3 mb-4">
            {error || errFromQuery}
          </div>
        )}
        <form method="post" action="/login" className="space-y-3">
          <input type="hidden" name="next" value="/" />
          <input
            type="hidden"
            name="csrf_token"
            value={document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content || ''}
          />
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-muted mb-1 font-semibold">
              Username
            </label>
            <input
              type="text"
              name="username"
              required
              autoFocus
              className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-sm
                          focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-muted mb-1 font-semibold">
              Password
            </label>
            <input
              type="password"
              name="password"
              required
              className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-sm
                          focus:outline-none focus:border-accent"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-accent hover:bg-accent/90 py-2.5 rounded-lg font-semibold text-sm"
          >
            Sign in
          </button>
        </form>
        <div className="text-center mt-4">
          <a href="/login/oidc" className="text-xs text-muted hover:text-white">
            Sign in with SSO
          </a>
        </div>
      </div>
    </div>
  );
}
