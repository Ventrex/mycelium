import { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export default function LanguageSettingsModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: languages } = useQuery({
    queryKey: ['discover-languages'],
    queryFn: () => api.languages().then((r) => r.languages),
  });
  const { data: prefs } = useQuery({
    queryKey: ['language-prefs'],
    queryFn: () => api.languagePrefsGet(),
  });

  const [allowed, setAllowed] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!prefs) return;
    setAllowed(prefs.allowed || []);
    setExcluded(prefs.excluded || []);
  }, [prefs]);

  const filtered = useMemo(() => {
    const list = languages || [];
    if (!query.trim()) return list;
    const q = query.trim().toLowerCase();
    return list.filter(
      (l) => l.english_name.toLowerCase().includes(q) || l.name.toLowerCase().includes(q),
    );
  }, [languages, query]);

  const nameFor = (code: string) => languages?.find((l) => l.iso_639_1 === code)?.english_name || code;

  const allow = (code: string) => {
    setExcluded((prev) => prev.filter((c) => c !== code));
    setAllowed((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };
  const exclude = (code: string) => {
    setAllowed((prev) => prev.filter((c) => c !== code));
    setExcluded((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const saveMutation = useMutation({
    mutationFn: () => api.languagePrefsSet({ allowed, excluded }),
    onSuccess: () => {
      queryClient.invalidateQueries();
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
        <h2 className="text-xl font-bold mb-1">Language settings</h2>
        <p className="text-sm text-muted mb-5">
          Only show titles in specific original languages (allow list), or hide specific languages
          entirely (e.g. exclude Hindi to filter out Bollywood). Leave both empty to show everything.
        </p>

        {(allowed.length > 0 || excluded.length > 0) && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {allowed.map((code) => (
              <span
                key={`a-${code}`}
                className="text-xs px-2 py-1 rounded-full bg-green-600/20 border border-green-600/50 text-green-300 flex items-center gap-1"
              >
                {nameFor(code)}
                <button type="button" onClick={() => allow(code)} className="hover:text-white">
                  ×
                </button>
              </span>
            ))}
            {excluded.map((code) => (
              <span
                key={`e-${code}`}
                className="text-xs px-2 py-1 rounded-full bg-red-600/20 border border-red-600/50 text-red-300 flex items-center gap-1"
              >
                {nameFor(code)}
                <button type="button" onClick={() => exclude(code)} className="hover:text-white">
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search languages..."
          className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm mb-3
                      focus:outline-none focus:border-accent text-white placeholder-muted/60"
        />

        <div className="space-y-1 max-h-80 overflow-y-auto pr-1">
          {filtered.map((l) => {
            const isAllowed = allowed.includes(l.iso_639_1);
            const isExcluded = excluded.includes(l.iso_639_1);
            return (
              <div
                key={l.iso_639_1}
                className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg border border-border"
              >
                <span className="text-sm truncate">{l.english_name || l.name || l.iso_639_1}</span>
                <div className="flex gap-1.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => allow(l.iso_639_1)}
                    className={`text-xs px-2 py-1 rounded ${
                      isAllowed ? 'bg-green-600 text-white' : 'border border-border text-muted hover:text-white'
                    }`}
                  >
                    Allow
                  </button>
                  <button
                    type="button"
                    onClick={() => exclude(l.iso_639_1)}
                    className={`text-xs px-2 py-1 rounded ${
                      isExcluded ? 'bg-red-600 text-white' : 'border border-border text-muted hover:text-white'
                    }`}
                  >
                    Exclude
                  </button>
                </div>
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
