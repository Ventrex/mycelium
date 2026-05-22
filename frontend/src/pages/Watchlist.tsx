import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { MediaType, TmdbItem } from '../types';
import PosterCard from '../components/PosterCard';
import DetailModal from '../components/DetailModal';

export default function Watchlist() {
  const [detail, setDetail] = useState<{ id: number; type: MediaType } | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ['watchlist'], queryFn: api.watchlist });

  if (isLoading) {
    return <div className="text-muted text-sm py-6">Loading...</div>;
  }

  if (!data?.items.length) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-3">&#9733;</div>
        <h2 className="text-lg font-semibold mb-1">Your watchlist is empty</h2>
        <p className="text-muted text-sm">Add items from the Discover page to track what you want to watch.</p>
      </div>
    );
  }

  const open = (item: TmdbItem) => setDetail({ id: item.tmdb_id, type: item.media_type });

  return (
    <div>
      <p className="text-muted text-sm mb-4">{data.items.length} items in your watchlist</p>
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 200px))' }}>
        {data.items.map((it) => (
          <PosterCard
            key={it.id}
            item={{
              tmdb_id: it.tmdb_id || 0,
              media_type: it.media_type,
              title: it.title,
              year: null,
              rating: 0,
              votes: 0,
              popularity: 0,
              overview: '',
              poster_path: it.poster_path,
              backdrop_path: null,
            }}
            onClick={open}
            status={it.library_status}
          />
        ))}
      </div>
      <DetailModal
        tmdbId={detail?.id ?? null}
        mediaType={detail?.type ?? null}
        onClose={() => setDetail(null)}
        onSelectItem={open}
      />
    </div>
  );
}
