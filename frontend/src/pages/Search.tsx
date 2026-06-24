import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { MediaType, TmdbItem } from '../types';
import PosterCard from '../components/PosterCard';
import PersonCard from '../components/PersonCard';
import DetailModal from '../components/DetailModal';
import PersonModal from '../components/PersonModal';
import LanguageSettingsModal from '../components/LanguageSettingsModal';

type TypeFilter = 'all' | MediaType | 'person';

export default function Search() {
  const [q, setQ] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [detail, setDetail] = useState<{ id: number; type: MediaType } | null>(null);
  const [personId, setPersonId] = useState<number | null>(null);
  const [showLanguageSettings, setShowLanguageSettings] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['search', q],
    queryFn: () => api.search(q).then((r) => r.results),
    enabled: q.trim().length > 0,
  });

  const { data: people, isLoading: peopleLoading } = useQuery({
    queryKey: ['search-person', q],
    queryFn: () => api.searchPerson(q).then((r) => r.results),
    enabled: q.trim().length > 0,
  });

  const showTitles = typeFilter !== 'person';
  const showPeople = typeFilter === 'all' || typeFilter === 'person';

  const filtered = (data || []).filter((i) =>
    typeFilter === 'all' || typeFilter === 'person' ? true : i.media_type === typeFilter,
  );
  const visiblePeople = showPeople ? people || [] : [];
  const totalCount = (showTitles ? filtered.length : 0) + visiblePeople.length;

  const open = (it: TmdbItem) => setDetail({ id: it.tmdb_id, type: it.media_type });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 max-w-xl">
        <input
          type="text"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search movies, series or actors..."
          className="flex-1 bg-bg border border-border rounded-lg px-4 py-3 text-sm
                     focus:outline-none focus:border-accent text-white placeholder-muted/60"
        />
        <button
          type="button"
          onClick={() => setShowLanguageSettings(true)}
          title="Language settings"
          className="shrink-0 px-3 py-3 rounded-lg border border-border hover:border-accent/50 text-sm"
        >
          🌐
        </button>
      </div>
      <div className="flex gap-2">
        {(['all', 'movie', 'tv', 'person'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTypeFilter(t)}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${
              typeFilter === t
                ? 'border-accent bg-accent/10 text-white'
                : 'border-border text-muted hover:text-white'
            }`}
          >
            {t === 'all' ? 'All' : t === 'movie' ? 'Movies' : t === 'tv' ? 'Series' : 'Actors'}
          </button>
        ))}
      </div>
      {q.trim() && (
        <p className="text-muted text-xs">{totalCount} results for &quot;{q}&quot;</p>
      )}
      {q.trim() ? (
        isLoading || peopleLoading ? (
          <div className="text-muted text-sm py-6">Loading...</div>
        ) : totalCount > 0 ? (
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 200px))' }}>
            {visiblePeople.map((p) => (
              <PersonCard key={`person-${p.tmdb_id}`} person={p} onClick={(pp) => setPersonId(pp.tmdb_id)} />
            ))}
            {showTitles &&
              filtered.map((it) => (
                <PosterCard
                  key={`${it.media_type}-${it.tmdb_id}`}
                  item={it}
                  onClick={open}
                  status={it.library_status}
                />
              ))}
          </div>
        ) : (
          <div className="text-muted text-sm py-6">No results</div>
        )
      ) : (
        <div className="text-muted text-sm py-8 text-center">
          Start typing to search across movies, series and actors.
        </div>
      )}
      <DetailModal
        tmdbId={detail?.id ?? null}
        mediaType={detail?.type ?? null}
        onClose={() => setDetail(null)}
        onSelectItem={open}
      />
      <PersonModal
        personId={personId}
        onClose={() => setPersonId(null)}
        onSelectItem={(it) => {
          setPersonId(null);
          open(it);
        }}
      />
      {showLanguageSettings && (
        <LanguageSettingsModal onClose={() => setShowLanguageSettings(false)} />
      )}
    </div>
  );
}
