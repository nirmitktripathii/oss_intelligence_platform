'use client';

import { useState, useCallback, useTransition } from 'react';
import { FilterState, Domain, Difficulty, ViewMode } from '@/types/issue';

const DEFAULT_FILTERS: FilterState = {
  domain: 'all',
  difficulty: 'all',
  techStack: [],
  hasBountyOnly: false,
  minBounty: 0,
  timeToSolve: 'all',
  search: '',
  sortBy: 'created_desc',
  page: 1,
  pageSize: 20,
  viewMode: 'grid',
};

export function useFilters() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [isPending, startTransition] = useTransition();

  const setDomain = useCallback((domain: Domain | 'all') => {
    setFilters((prev) => ({ ...prev, domain, page: 1 }));
  }, []);

  const setDifficulty = useCallback((difficulty: Difficulty | 'all') => {
    setFilters((prev) => ({ ...prev, difficulty, page: 1 }));
  }, []);

  const toggleTechStack = useCallback((tech: string) => {
    setFilters((prev) => {
      const exists = prev.techStack.includes(tech);
      const nextStack = exists
        ? prev.techStack.filter((t) => t !== tech)
        : [...prev.techStack, tech];
      return { ...prev, techStack: nextStack, page: 1 };
    });
  }, []);

  const setHasBountyOnly = useCallback((hasBountyOnly: boolean) => {
    setFilters((prev) => ({ ...prev, hasBountyOnly, page: 1 }));
  }, []);

  const setMinBounty = useCallback((minBounty: number) => {
    setFilters((prev) => ({ ...prev, minBounty, page: 1 }));
  }, []);

  const setTimeToSolve = useCallback((timeToSolve: FilterState['timeToSolve']) => {
    setFilters((prev) => ({ ...prev, timeToSolve, page: 1 }));
  }, []);

  const setSearch = useCallback((search: string) => {
    startTransition(() => {
      setFilters((prev) => ({ ...prev, search, page: 1 }));
    });
  }, []);

  const setSortBy = useCallback((sortBy: FilterState['sortBy']) => {
    setFilters((prev) => ({ ...prev, sortBy, page: 1 }));
  }, []);

  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  const setViewMode = useCallback((viewMode: ViewMode) => {
    setFilters((prev) => ({ ...prev, viewMode }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters((prev) => ({
      ...DEFAULT_FILTERS,
      viewMode: prev.viewMode, // preserve view preference
    }));
  }, []);

  const isFiltered =
    filters.domain !== 'all' ||
    filters.difficulty !== 'all' ||
    filters.techStack.length > 0 ||
    filters.hasBountyOnly ||
    filters.minBounty > 0 ||
    filters.timeToSolve !== 'all' ||
    filters.search !== '';

  return {
    filters,
    isPending,
    setDomain,
    setDifficulty,
    toggleTechStack,
    setHasBountyOnly,
    setMinBounty,
    setTimeToSolve,
    setSearch,
    setSortBy,
    setPage,
    setViewMode,
    resetFilters,
    isFiltered,
  };
}
