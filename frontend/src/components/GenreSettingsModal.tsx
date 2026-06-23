import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { Genre, MediaType } from '../types';

export default function GenreSettingsModal({
  mediaType,
  allGenres,
  onClose,
}: {
  mediaType: MediaType;
  allGenres: Genre[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: prefs } = useQuery({
    queryKey: ['discover-prefs', mediaType],
    queryFn: () => api.discoverPrefsGet(mediaType),
  });

  const [hidden, setHidden] = useState<number[]>([]);
  const [order, setOrder] = useState<number[]>([]);
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');
  const [genreYears, setGenreYears] = useState<Record<string, { from: number | null; to: number | null }>>({});

  useEffect(() => {
    if (!prefs) return;
    setHidden(prefs.hidden_genres || []);
    const baseOrder = prefs.genre_order && prefs.genre_order.length > 0
      ? prefs.genre_order
      : allGenres.map((g) => g.id);
    const known = new Set(baseOrder);
    const merged = [...baseOrder, ...allGenres.filter((g) => !known.has(g.id)).map((g) => g.id)];
    setOrder(merged);
    setYearFrom(prefs.year_from != null ? String(prefs.year_from) : '');
    setYearTo(prefs.year_to != null ? String(prefs.year_to) : '');
    setGenreYears(prefs.genre_years || {});
  }, [prefs, allGenres]);

  const orderedGenres = order
    .map((id) => allGenres.find((g) => g.id === id))
    .filter((g): g is Genre => !!g);

  const toggleHidden = (id: number) =>
    setHidden((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const move = (id: number, dir: -1 | 1) => {
    setOrder((prev) => {
      const idx = prev.indexOf(id);
      const swapWith = idx + dir;
      if (idx < 0 || swapWith < 0 || swapWith >= prev.length) return prev;
      const next = [...prev];
      [next[idx], next[swapWith]] = [next[swapWith], next[idx]];
      return next;
    });
  };

  const setGenreYear = (id: number, bound: 'from' | 'to', value: string) => {
    setGenreYears((prev) => {
      const current = prev[String(id)] || { from: null, to: null };
      return { ...prev, [String(id)]: { ...current, [bound]: value ? Number(value) : null } };
    });
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      api.discoverPrefsSet(mediaType, {
        hidden_genres: hidden,
        genre_order: order,
        year_from: yearFrom ? Number(yearFrom) : null,
        year_to: yearTo ? Number(yearTo) : null,
        genre_years: genreYears,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discover-genres', mediaType] });
      queryClient.invalidateQueries({ queryKey: ['by-genre', mediaType] });
      onClose();
    },
  });

  return createPortal(
    <div
      className="fixed inset-0 z-[200] bg-black/85 backdrop-blur-sm overflow-y-auto p-4 sm:p-8"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="relative max-w-2xl mx-auto bg-card rounded-2xl shadow-2xl p-6 sm:p-8">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/40 hover:bg-black/60
                      text-white text-xl flex items-center justify-center"
          aria-label="Close"
        >
          ×
        </button>
        <h2 className="text-xl font-bold mb-1">Genre settings</h2>
        <p className="text-sm text-muted mb-5">
          Hide genres you don&apos;t want, reorder the rest, and set a default year range.
          A genre without its own range falls back to this default per bound.
        </p>

        <div className="flex items-center gap-3 mb-5 bg-bg/60 border border-border rounded-lg p-3">
          <span className="text-xs text-muted whitespace-nowrap">Default year range</span>
          <input
            type="number"
            placeholder="From"
            value={yearFrom}
            onChange={(e) => setYearFrom(e.target.value)}
            className="w-24 bg-bg border border-border rounded px-2 py-1 text-sm"
          />
          <span className="text-muted">-</span>
          <input
            type="number"
            placeholder="To"
            value={yearTo}
            onChange={(e) => setYearTo(e.target.value)}
            className="w-24 bg-bg border border-border rounded px-2 py-1 text-sm"
          />
        </div>

        <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
          {orderedGenres.map((g, i) => {
            const gy = genreYears[String(g.id)] || { from: null, to: null };
            const isHidden = hidden.includes(g.id);
            return (
              <div
                key={g.id}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border border-border ${
                  isHidden ? 'opacity-50' : ''
                }`}
              >
                <div className="flex flex-col -my-1">
                  <button
                    type="button"
                    onClick={() => move(g.id, -1)}
                    disabled={i === 0}
                    className="text-muted hover:text-white disabled:opacity-30 text-xs leading-none"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    onClick={() => move(g.id, 1)}
                    disabled={i === orderedGenres.length - 1}
                    className="text-muted hover:text-white disabled:opacity-30 text-xs leading-none"
                  >
                    ▼
                  </button>
                </div>
                <label className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!isHidden}
                    onChange={() => toggleHidden(g.id)}
                    className="accent-accent"
                  />
                  <span className="text-sm truncate">{g.name}</span>
                </label>
                <input
                  type="number"
                  placeholder="From"
                  value={gy.from ?? ''}
                  onChange={(e) => setGenreYear(g.id, 'from', e.target.value)}
                  className="w-16 bg-bg border border-border rounded px-1.5 py-1 text-xs"
                />
                <input
                  type="number"
                  placeholder="To"
                  value={gy.to ?? ''}
                  onChange={(e) => setGenreYear(g.id, 'to', e.target.value)}
                  className="w-16 bg-bg border border-border rounded px-1.5 py-1 text-xs"
                />
              </div>
            );
          })}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-border text-sm">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-60 font-semibold text-sm"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
