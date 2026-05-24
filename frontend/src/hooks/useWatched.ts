/**
 * Returns the set of imdb_ids the current user has watched (via Trakt).
 * Empty set when Trakt is not connected or plugin not loaded.
 * Cached 5 minutes via react-query.
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export function useWatched(): Set<string> {
  const { data: session } = useQuery({ queryKey: ['session'], queryFn: api.session })
  const isConnected = !!(session?.user as any)?.trakt_connected

  const { data } = useQuery({
    queryKey: ['trakt-watched'],
    queryFn: api.traktWatched,
    enabled: isConnected,
    staleTime: 5 * 60 * 1000,
  })

  return useMemo(() => new Set(data?.imdb_ids ?? []), [data])
}
