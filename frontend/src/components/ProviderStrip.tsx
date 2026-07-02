import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, NL_PROVIDER_IDS, tmdbImg } from '../api';
import type { MediaType, TmdbItem } from '../types';
import PosterGrid from './PosterGrid';
import SectionHeader from './SectionHeader';

export default function ProviderStrip({
  mediaType,
  onPick,
  onItemClick,
}: {
  mediaType: MediaType;
  onPick?: (pid: number | null) => void;
  onItemClick: (item: TmdbItem) => void;
}) {
  const [activePid, setActivePid] = useState<number | null>(null);
  const { data: providers } = useQuery({
    queryKey: ['providers', mediaType],
    queryFn: () => api.providers(mediaType),
  });

  const wanted = Object.values(NL_PROVIDER_IDS);
  const visible = (providers?.providers || [])
    .filter((p) => wanted.includes(p.id as any))
    .sort((a, b) => wanted.indexOf(a.id as any) - wanted.indexOf(b.id as any));

  const activeName = visible.find((p) => p.id === activePid)?.name || '';

  return (
    <section>
      <div className="flex gap-2 overflow-x-auto scrollbar-hidden pb-2 -mx-1 px-1">
        <ProviderChip
          name="All"
          active={activePid === null}
          onClick={() => {
            setActivePid(null);
            onPick?.(null);
          }}
        />
        {visible.map((p) => (
          <ProviderChip
            key={p.id}
            name={p.name}
            logo={tmdbImg.logo(p.logo_path)}
            active={activePid === p.id}
            onClick={() => {
              setActivePid(p.id);
              onPick?.(p.id);
            }}
          />
        ))}
      </div>
      {activePid !== null && (
        <div className="space-y-8 mt-6">
          <ProviderRow
            title={`Trending on ${activeName}`}
            pid={activePid}
            type={mediaType}
            sortBy="popularity.desc"
            onItemClick={onItemClick}
          />
          <ProviderRow
            title={`Top rated on ${activeName}`}
            pid={activePid}
            type={mediaType}
            sortBy="vote_average.desc"
            onItemClick={onItemClick}
          />
        </div>
      )}
    </section>
  );
}

function ProviderRow({ title, pid, type, sortBy, onItemClick }: {
  title: string; pid: number; type: MediaType; sortBy: string; onItemClick: (item: TmdbItem) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['by-provider', pid, type, sortBy],
    queryFn: () => api.byProvider(type, pid, sortBy).then((r) => r.results),
  });
  const items = data || [];
  if (!isLoading && items.length === 0) return null;
  return (
    <section>
      <SectionHeader title={title} />
      <PosterGrid items={items} loading={isLoading} onItemClick={onItemClick} />
    </section>
  );
}

function ProviderChip({
  name,
  logo,
  active,
  onClick,
}: {
  name: string;
  logo?: string | null;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-shrink-0 flex items-center gap-2 px-3 py-2 rounded-full text-xs whitespace-nowrap
                   border transition ${
                     active
                       ? 'bg-accent text-white border-accent'
                       : 'bg-card text-white border-border hover:border-accent/50'
                   }`}
    >
      {logo && <img src={logo} alt="" className="w-5 h-5 rounded" />}
      <span>{name}</span>
    </button>
  );
}
