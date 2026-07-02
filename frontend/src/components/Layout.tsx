import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

const navItems = [
  { to: '/movies', label: 'Movies', icon: '🎬' },
  { to: '/shows', label: 'Shows', icon: '📺' },
  { to: '/library', label: 'Library', icon: '📚' },
  { to: '/watchlist', label: 'Watchlist', icon: '★' },
  { to: '/requests', label: 'My Requests', icon: '📋' },
];

const adminItems = [
  { to: '/admin', label: 'Admin', icon: '⚙️' },
];

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { data: session } = useQuery({
    queryKey: ['session'],
    queryFn: api.session,
    staleTime: 60_000,
  });

  const isAdmin = session?.user?.role === 'admin';

  // Netflix-style: once signed in but no profile picked yet, go choose one.
  useEffect(() => {
    if (session?.profiles_required) {
      navigate('/profiles');
    }
  }, [session?.profiles_required, navigate]);

  return (
    <div className="min-h-screen flex bg-bg text-white overflow-x-hidden">
      {/* Sidebar (desktop) + Drawer (mobile) */}
      <aside
        className={`
          fixed lg:sticky top-0 left-0 h-screen w-[min(14rem,85vw)] lg:w-56 max-w-full
          bg-card border-r border-border z-40 flex flex-col
          transition-transform duration-200
          ${drawerOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0
        `}
      >
        <div className="px-5 py-5 flex items-center gap-3 border-b border-border">
          <svg width="28" height="28" viewBox="0 0 40 40" aria-hidden="true">
            <g stroke="#22d3ee" strokeWidth="1.5" opacity="0.7">
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
          <span className="font-mono font-bold tracking-wide text-lg text-white truncate">
            myc<span className="text-accent-2">3</span>l<span className="text-accent-2">1</span>um
          </span>
          <button
            className="lg:hidden ml-auto -mr-2 p-2 rounded text-muted hover:text-white hover:bg-bg"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close menu"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          <SidebarSection title="" items={navItems} onClick={() => setDrawerOpen(false)} />
          {isAdmin && (
            <SidebarSection title="Manage" items={adminItems} onClick={() => setDrawerOpen(false)} />
          )}
        </nav>
        <div className="shrink-0 p-4 border-t border-border text-center text-[10px] text-muted opacity-50">
          v0.2.0-beta
        </div>
      </aside>
      {/* Drawer overlay */}
      {drawerOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-20 bg-bg/80 backdrop-blur border-b border-border">
          <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 lg:px-8 py-3">
            <button
              className="lg:hidden shrink-0 p-2 -ml-1 border border-border rounded-lg text-white hover:bg-card hover:border-accent/50 transition"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </button>
            <Breadcrumb path={location.pathname} />
            <div className="ml-auto flex items-center gap-1.5 sm:gap-2 shrink-0">
              <TopbarSearch />
              <TopbarIconLink to="/manual" label="Manual" icon="📖" />
              {session?.user && <RegionPicker region={session.user.region || 'NL'} />}
              <ProfileMenu username={session?.user?.username} profile={session?.selected_profile} />
            </div>
          </div>
        </header>
        <main className="flex-1 min-w-0 px-3 sm:px-4 lg:px-8 py-4 sm:py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function SidebarSection({
  title,
  items,
  onClick,
}: {
  title: string;
  items: { to: string; label: string; icon: string; exact?: boolean; external?: boolean }[];
  onClick: () => void;
}) {
  return (
    <div className="mb-2">
      {title && (
        <div className="px-5 pt-3 pb-1 text-[10px] uppercase tracking-wider text-muted font-semibold">
          {title}
        </div>
      )}
      {items.map((item) =>
        item.external ? (
          <a
            key={item.to}
            href={item.to}
            onClick={onClick}
            className="flex items-center gap-3 px-5 py-2 text-sm transition relative text-muted hover:text-white hover:bg-bg"
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </a>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            onClick={onClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2 text-sm transition relative
               ${isActive
                  ? 'text-white bg-accent/10 before:absolute before:left-0 before:top-0 before:bottom-0 before:w-0.5 before:bg-accent'
                  : 'text-muted hover:text-white hover:bg-bg'
                }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        )
      )}
    </div>
  );
}


function TopbarSearch() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = q.trim();
    navigate(term ? `/search?q=${encodeURIComponent(term)}` : '/search');
  };

  return (
    <form onSubmit={submit} className="relative" role="search">
      <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-sm text-muted" aria-hidden="true">
        🔍
      </span>
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search…"
        aria-label="Search"
        className="w-28 sm:w-44 md:w-56 rounded-lg border border-border bg-card pl-8 pr-2.5 py-1.5 text-sm
                   text-white placeholder-muted/60 focus:outline-none focus:border-accent/50 transition-[width]"
      />
    </form>
  );
}

function TopbarIconLink({ to, label, icon }: { to: string; label: string; icon: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-center w-9 h-9 rounded-lg border border-border hover:border-accent/50 hover:bg-card transition"
      title={label}
      aria-label={label}
    >
      <span aria-hidden="true">{icon}</span>
    </Link>
  );
}

function ProfileMenu({ username, profile }: { username?: string; profile?: { name: string; avatar?: string } | null }) {
  const [open, setOpen] = useState(false);

  if (!username) {
    return (
      <a
        href="/login"
        className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white hover:border-accent/50 transition"
      >
        Sign in
      </a>
    );
  }

  const label = profile?.name || username;
  const avatar = profile?.avatar || '👤';

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border hover:border-accent/50 hover:bg-card transition"
        aria-haspopup="menu"
        aria-expanded={open}
        title={label}
      >
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-xs">{avatar}</span>
        <span className="hidden md:inline max-w-28 truncate text-sm">{label}</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 w-44 overflow-hidden rounded-lg border border-border bg-card shadow-xl">
            <Link
              to="/profiles"
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm text-muted hover:bg-bg hover:text-white"
            >
              Switch profile
            </Link>
            <Link
              to="/settings"
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm text-muted hover:bg-bg hover:text-white"
            >
              Settings
            </Link>
            <a href="/logout" className="block px-3 py-2 text-sm text-muted hover:bg-bg hover:text-white">
              Log out
            </a>
          </div>
        </>
      )}
    </div>
  );
}

const REGIONS: { code: string; flag: string; name: string }[] = [
  { code: 'NL', flag: '\u{1F1F3}\u{1F1F1}', name: 'Netherlands' },
  { code: 'BE', flag: '\u{1F1E7}\u{1F1EA}', name: 'Belgium' },
  { code: 'ZA', flag: '\u{1F1FF}\u{1F1E6}', name: 'South Africa' },
  { code: 'US', flag: '\u{1F1FA}\u{1F1F8}', name: 'United States' },
  { code: 'GB', flag: '\u{1F1EC}\u{1F1E7}', name: 'United Kingdom' },
  { code: 'DE', flag: '\u{1F1E9}\u{1F1EA}', name: 'Germany' },
  { code: 'FR', flag: '\u{1F1EB}\u{1F1F7}', name: 'France' },
  { code: 'ES', flag: '\u{1F1EA}\u{1F1F8}', name: 'Spain' },
  { code: 'IT', flag: '\u{1F1EE}\u{1F1F9}', name: 'Italy' },
  { code: 'AU', flag: '\u{1F1E6}\u{1F1FA}', name: 'Australia' },
  { code: 'CA', flag: '\u{1F1E8}\u{1F1E6}', name: 'Canada' },
  { code: 'BR', flag: '\u{1F1E7}\u{1F1F7}', name: 'Brazil' },
  { code: 'IN', flag: '\u{1F1EE}\u{1F1F3}', name: 'India' },
  { code: 'JP', flag: '\u{1F1EF}\u{1F1F5}', name: 'Japan' },
  { code: 'KR', flag: '\u{1F1F0}\u{1F1F7}', name: 'South Korea' },
  { code: 'SE', flag: '\u{1F1F8}\u{1F1EA}', name: 'Sweden' },
  { code: 'NO', flag: '\u{1F1F3}\u{1F1F4}', name: 'Norway' },
  { code: 'DK', flag: '\u{1F1E9}\u{1F1F0}', name: 'Denmark' },
  { code: 'PT', flag: '\u{1F1F5}\u{1F1F9}', name: 'Portugal' },
  { code: 'PL', flag: '\u{1F1F5}\u{1F1F1}', name: 'Poland' },
];

function RegionPicker({ region }: { region: string }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (code: string) => api.setRegion(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session'] });
      queryClient.invalidateQueries({ queryKey: ['trending'] });
      queryClient.invalidateQueries({ queryKey: ['popular'] });
      queryClient.invalidateQueries({ queryKey: ['top-rated'] });
      queryClient.invalidateQueries({ queryKey: ['now-playing'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming'] });
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      queryClient.invalidateQueries({ queryKey: ['by-provider'] });
    },
  });

  const current = REGIONS.find((r) => r.code === region);
  const flag = current?.flag || region;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded border border-border hover:border-accent/50 text-sm transition"
        title={current?.name || region}
      >
        <span className="text-base">{flag}</span>
        <span className="text-xs text-muted">{region}</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 bg-card border border-border rounded-lg shadow-xl overflow-hidden w-48 max-h-64 overflow-y-auto">
            {REGIONS.map((r) => (
              <button
                key={r.code}
                type="button"
                onClick={() => {
                  mutation.mutate(r.code);
                  setOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition
                  ${r.code === region ? 'bg-accent/10 text-white' : 'text-muted hover:text-white hover:bg-bg'}`}
              >
                <span>{r.flag}</span>
                <span>{r.name}</span>
                <span className="ml-auto text-[10px] opacity-50">{r.code}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Breadcrumb({ path }: { path: string }) {
  const map: Record<string, string> = {
    '/shows': 'Shows',
    '/movies': 'Movies',
    '/library': 'Library',
    '/watchlist': 'Watchlist',
    '/search': 'Search',
    '/requests': 'My Requests',
    '/settings': 'Settings',
    '/admin': 'Admin',
    '/manual': 'Manual',
    '/login': 'Sign in',
  };
  const title = map[path] || 'Mycelium';
  return <h1 className="font-semibold text-base sm:text-lg truncate min-w-0">{title}</h1>;
}

