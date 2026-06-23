import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { api, tmdbImg } from '../api';
import type { FilmographyItem, TmdbItem } from '../types';

export default function PersonModal({
  personId,
  onClose,
  onSelectItem,
}: {
  personId: number | null;
  onClose: () => void;
  onSelectItem: (item: TmdbItem) => void;
}) {
  const open = personId !== null;

  const { data: person, isLoading } = useQuery({
    queryKey: ['person', personId],
    queryFn: () => api.personDetails(personId!),
    enabled: open,
  });

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const photo = tmdbImg.profile(person?.profile_path);

  return createPortal(
    <div
      className="fixed inset-0 z-[200] bg-black/85 backdrop-blur-sm overflow-y-auto p-4 sm:p-8"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="relative max-w-5xl mx-auto bg-card rounded-2xl overflow-hidden shadow-2xl p-6 sm:p-8">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-black/60 hover:bg-black/80
                      text-white text-xl flex items-center justify-center"
          aria-label="Close"
        >
          ×
        </button>
        {isLoading || !person ? (
          <div className="text-muted text-center py-12">Loading…</div>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row gap-6">
              <div className="flex-shrink-0 w-40 sm:w-52 mx-auto sm:mx-0 aspect-[2/3] rounded-lg overflow-hidden bg-bg">
                {photo ? (
                  <img src={photo} alt={person.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-muted text-xs p-3">
                    No photo
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-2xl sm:text-3xl font-bold">{person.name}</h2>
                <div className="flex flex-wrap gap-2 mt-3 text-xs">
                  {person.known_for_department && <Badge>{person.known_for_department}</Badge>}
                  {person.birthday && <Badge>Born {person.birthday}</Badge>}
                  {person.place_of_birth && <Badge>{person.place_of_birth}</Badge>}
                </div>
                <p className="text-sm leading-relaxed mt-4 max-w-3xl line-clamp-[10]">
                  {person.biography || 'No biography available.'}
                </p>
              </div>
            </div>

            {person.filmography.length > 0 && (
              <div className="mt-7">
                <h3 className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-3">
                  Filmography ({person.filmography.length})
                </h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
                  {person.filmography.map((f: FilmographyItem) => (
                    <button
                      key={`${f.media_type}-${f.tmdb_id}`}
                      type="button"
                      onClick={() => onSelectItem(f)}
                      className="text-left"
                    >
                      <div className="aspect-[2/3] rounded-md overflow-hidden bg-bg border border-border
                                  hover:border-accent/50 transition relative">
                        {f.poster_path ? (
                          <img
                            src={tmdbImg.poster(f.poster_path) || undefined}
                            alt={f.title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="text-xs text-muted p-2 text-center">{f.title}</div>
                        )}
                        <div
                          className={`absolute top-1 right-1 px-1 py-0.5 rounded text-[9px] font-semibold uppercase ${
                            f.media_type === 'tv' ? 'bg-accent/90' : 'bg-black/70'
                          } text-white`}
                        >
                          {f.media_type === 'tv' ? 'TV' : 'Movie'}
                        </div>
                      </div>
                      <div className="text-[11px] mt-1 font-semibold leading-tight line-clamp-2">
                        {f.title}
                      </div>
                      <div className="text-[10px] text-muted flex items-center gap-1">
                        {f.year && <span>{f.year}</span>}
                        {f.character && <span className="truncate">as {f.character}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return <span className="bg-bg px-2 py-0.5 rounded text-xs">{children}</span>;
}
