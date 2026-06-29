import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Profile } from '../types';

const AGE_OPTIONS: Profile['age_rating'][] = ['all', '6', '9', '12', '16', '18'];
const AVATARS = ['👤', '😀', '😎', '🦸', '🧙', '🐱', '🐶', '🦊'];

export default function ProfileSelect() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['profiles'], queryFn: api.profiles });
  const [manage, setManage] = useState(false);
  const [form, setForm] = useState({ name: '', avatar: '👤', age_rating: 'all' as Profile['age_rating'], kids_mode: false });
  const [editing, setEditing] = useState<Profile | null>(null);

  useEffect(() => {
    if (editing) {
      setForm({
        name: editing.name,
        avatar: editing.avatar || '👤',
        age_rating: editing.age_rating || 'all',
        kids_mode: !!editing.kids_mode,
      });
    }
  }, [editing]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['profiles'] });
    qc.invalidateQueries({ queryKey: ['session'] });
  };
  const selectMut = useMutation({
    mutationFn: (id: number) => api.profileSelect(id),
    onSuccess: () => {
      invalidate();
      navigate('/');
    },
  });
  const createMut = useMutation({
    mutationFn: () => api.profileCreate(form),
    onSuccess: () => {
      invalidate();
      setForm({ name: '', avatar: '👤', age_rating: 'all', kids_mode: false });
    },
  });
  const updateMut = useMutation({
    mutationFn: () => editing ? api.profileUpdate(editing.id, form) : Promise.reject(new Error('No profile selected')),
    onSuccess: () => {
      invalidate();
      setEditing(null);
      setForm({ name: '', avatar: '👤', age_rating: 'all', kids_mode: false });
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => api.profileDelete(id),
    onSuccess: () => invalidate(),
  });

  const profiles = data?.profiles || [];

  if (isLoading) {
    return <div className="min-h-screen bg-bg text-white flex items-center justify-center">Loading profiles...</div>;
  }

  return (
    <div className="min-h-screen bg-bg text-white flex items-center justify-center p-6">
      <div className="w-full max-w-4xl text-center space-y-8">
        <div>
          <h1 className="text-3xl md:text-5xl font-bold mb-2">Who is watching?</h1>
          <p className="text-muted">Choose a profile to continue.</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-5">
          {profiles.map((profile) => (
            <div key={profile.id} className="space-y-2">
              <button
                type="button"
                onClick={() => manage ? setEditing(profile) : selectMut.mutate(profile.id)}
                className="w-full aspect-square rounded-xl border border-border bg-card hover:border-accent hover:bg-accent/10 transition flex items-center justify-center text-5xl"
              >
                {profile.avatar || '👤'}
              </button>
              <div className="font-semibold truncate">{profile.name}</div>
              <div className="text-xs text-muted">{profile.age_rating === 'all' ? 'All ages' : `${profile.age_rating}+`}</div>
              {manage && (
                <button
                  type="button"
                  onClick={() => deleteMut.mutate(profile.id)}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setEditing(null)}
            className="aspect-square rounded-xl border border-dashed border-border bg-card/40 hover:border-accent hover:bg-accent/10 transition flex flex-col items-center justify-center gap-2"
          >
            <span className="text-4xl">＋</span>
            <span className="text-sm text-muted">Add profile</span>
          </button>
        </div>

        <div className="mx-auto max-w-md rounded-xl border border-border bg-card p-4 text-left space-y-3">
          <h2 className="font-bold">{editing ? 'Edit profile' : 'Add profile'}</h2>
          <input
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="Profile name"
            className="w-full bg-bg border border-border rounded px-3 py-2"
          />
          <div className="flex flex-wrap gap-2">
            {AVATARS.map((avatar) => (
              <button
                key={avatar}
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, avatar }))}
                className={`h-10 w-10 rounded border ${form.avatar === avatar ? 'border-accent bg-accent/10' : 'border-border'}`}
              >
                {avatar}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              <span className="block text-xs text-muted mb-1">Age rating</span>
              <select
                value={form.age_rating}
                onChange={(e) => setForm((prev) => ({ ...prev, age_rating: e.target.value as Profile['age_rating'] }))}
                className="w-full bg-bg border border-border rounded px-3 py-2"
              >
                {AGE_OPTIONS.map((age) => <option key={age} value={age}>{age === 'all' ? 'All' : `${age}+`}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm pt-6">
              <input
                type="checkbox"
                checked={form.kids_mode}
                onChange={(e) => setForm((prev) => ({ ...prev, kids_mode: e.target.checked }))}
                className="accent-accent"
              />
              Kids mode
            </label>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => editing ? updateMut.mutate() : createMut.mutate()}
              disabled={!form.name.trim() || createMut.isPending || updateMut.isPending}
              className="px-4 py-2 rounded bg-accent font-semibold disabled:opacity-60"
            >
              {editing ? 'Save profile' : 'Add profile'}
            </button>
            {editing && (
              <button type="button" onClick={() => setEditing(null)} className="px-4 py-2 rounded border border-border">
                Cancel
              </button>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setManage(!manage)}
          className="px-4 py-2 rounded border border-border text-muted hover:text-white"
        >
          {manage ? 'Done managing' : 'Manage profiles'}
        </button>
      </div>
    </div>
  );
}
